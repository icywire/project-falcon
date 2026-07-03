#!/usr/bin/env python3
"""
sign_cat.py — Sign a Windows .cat catalog file using a PFX certificate.

Replaces `signtool sign /fd SHA256` without requiring the WDK or Windows SDK.
Works with any unsigned .cat produced by inf2cat.py (or Microsoft's Inf2Cat).

Usage:
    python sign_cat.py catalog.cat --pfx cert.pfx --password pfx_pass
    python sign_cat.py catalog.cat --pfx cert.pfx --password pfx_pass --out signed.cat
    python sign_cat.py catalog.cat --pfx cert.pfx --password pfx_pass \
        --timestamp http://timestamp.digicert.com

Requirements:
    pip install cryptography    (tested with cryptography >= 38)

How it works
------------
A .cat file is a PKCS#7 SignedData structure wrapping a Microsoft CTL.
inf2cat.py produces it unsigned — empty digestAlgorithms and signerInfos.
This script fills in the three missing fields:

  1. digestAlgorithms  SET { AlgorithmIdentifier { SHA-256, NULL } }

  2. certificates      [0] IMPLICIT { leaf cert DER | chain cert DERs ... }

  3. signerInfos       SET {
       SignerInfo {
         version               INTEGER 1
         signerIdentifier      IssuerAndSerialNumber (from leaf cert)
         digestAlgorithm       SHA-256
         signedAttrs [0] IMPL  {
           content-type          OID 1.3.6.1.4.1.311.10.1  (szOID_CTL)
           message-digest        SHA-256 of the CTL body bytes
           signing-time          current UTC time
         }
         signatureAlgorithm    RSA (PKCS#1 v1.5)
         signature             RSA-SHA256 over DER-encoded signedAttrs
         unsignedAttrs [1] IMPL {              ← only if timestamped
           id-aa-signatureTimeStampToken       RFC 3161 TimeStampToken
         }
       }
     }

The message-digest covers the raw CTL body bytes — the content inside the
[0] EXPLICIT wrapper that follows the CTL OID in encapContentInfo.

References
----------
  RFC 5652  — Cryptographic Message Syntax (CMS)
    https://datatracker.ietf.org/doc/html/rfc5652
  RFC 3161  — Internet X.509 PKI Time-Stamp Protocol (TSP)
    https://datatracker.ietf.org/doc/html/rfc3161
  Microsoft Authenticode PE Specification (Authenticode_PE.docx)
    https://download.microsoft.com/download/9/c/5/9c5b2167-8017-4bae-9fde-d599bac8184a/Authenticode_PE.docx
"""

import argparse
import hashlib
import sys
import urllib.request
from datetime import datetime, timezone

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization.pkcs12 import load_pkcs12
except ImportError:
    print("[ERROR] Missing dependency: pip install cryptography")
    sys.exit(1)


# ---------------------------------------------------------------------------
# DER primitives  (same conventions as inf2cat.py)
# ---------------------------------------------------------------------------

def _der_len(n: int) -> bytes:
    if n < 0x80:        return bytes([n])
    if n < 0x100:       return bytes([0x81, n])
    if n < 0x10000:     return bytes([0x82, n >> 8, n & 0xFF])
    if n < 0x1000000:   return bytes([0x83, n >> 16, (n >> 8) & 0xFF, n & 0xFF])
    if n < 0x100000000: return bytes([0x84, n >> 24, (n >> 16) & 0xFF, (n >> 8) & 0xFF, n & 0xFF])
    raise OverflowError(f"DER length {n} exceeds 32-bit range")


def _tlv(tag: int, body: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(body)) + body


def der_seq(*items: bytes) -> bytes:
    return _tlv(0x30, b"".join(items))


def der_set(*items: bytes) -> bytes:
    """DER SET — members sorted lexicographically by their encoding."""
    return _tlv(0x31, b"".join(sorted(items)))


def der_int(value: int) -> bytes:
    if value == 0:
        return _tlv(0x02, b"\x00")
    n = (value.bit_length() + 7) // 8
    data = value.to_bytes(n, "big")
    if data[0] & 0x80:      # positive integer with high bit set — prepend 0x00
        data = b"\x00" + data
    return _tlv(0x02, data)


def der_octet(data: bytes) -> bytes:
    return _tlv(0x04, data)


def der_null() -> bytes:
    return b"\x05\x00"


def der_oid(dotted: str) -> bytes:
    parts = list(map(int, dotted.split(".")))
    body = bytes([40 * parts[0] + parts[1]])
    for v in parts[2:]:
        if v == 0:
            body += b"\x00"
        else:
            septets: list[int] = []
            while v:
                septets.append(v & 0x7F)
                v >>= 7
            septets.reverse()
            body += bytes(
                (s | 0x80) if i < len(septets) - 1 else s
                for i, s in enumerate(septets)
            )
    return _tlv(0x06, body)


def der_utctime(dt: datetime) -> bytes:
    return _tlv(0x17, dt.strftime("%y%m%d%H%M%SZ").encode("ascii"))


def der_ctx(tag: int, body: bytes) -> bytes:
    """Explicit context-specific constructed tag."""
    return bytes([0xA0 | tag]) + _der_len(len(body)) + body


def _rlen(data: bytes, pos: int) -> tuple[int, int]:
    """Read a DER length at pos; return (length, new_pos)."""
    if pos >= len(data):
        return 0, pos
    b = data[pos]; pos += 1
    if b < 0x80:
        return b, pos
    n = b & 0x7F
    return int.from_bytes(data[pos : pos + n], "big"), pos + n


# ---------------------------------------------------------------------------
# OIDs
# ---------------------------------------------------------------------------

OID_SIGNED_DATA    = "1.2.840.113549.1.7.2"
OID_CTL            = "1.3.6.1.4.1.311.10.1"   # szOID_CTL — catalog content type
OID_SHA256         = "2.16.840.1.101.3.4.2.1"
OID_RSA            = "1.2.840.113549.1.1.1"
OID_CONTENT_TYPE   = "1.2.840.113549.1.9.3"
OID_MESSAGE_DIGEST = "1.2.840.113549.1.9.4"
OID_SIGNING_TIME   = "1.2.840.113549.1.9.5"
OID_TIMESTAMP_TOK  = "1.3.6.1.4.1.311.3.3.1"       # szOID_RFC3161_counterSign (Microsoft Authenticode)

_CTL_OID_DER = der_oid(OID_CTL)


# ---------------------------------------------------------------------------
# Catalog parsing
# ---------------------------------------------------------------------------

def extract_ctl_content(cat_bytes: bytes) -> bytes:
    """Return the raw CTL body bytes from an unsigned .cat file.

    Locates the CTL OID (1.3.6.1.4.1.311.10.1) inside encapContentInfo and
    returns the content inside the following [0] EXPLICIT wrapper:

        encapContentInfo SEQUENCE {
            OID 1.3.6.1.4.1.311.10.1
            [0] { <CTL SEQUENCE bytes> }   ← returned here
        }

    These bytes are the input to the message-digest signed attribute.
    """
    idx = cat_bytes.find(_CTL_OID_DER)
    if idx == -1:
        raise ValueError("CTL OID (1.3.6.1.4.1.311.10.1) not found in catalog")
    p = idx + len(_CTL_OID_DER)
    if cat_bytes[p] != 0xA0:
        raise ValueError(f"Expected [0] EXPLICIT after CTL OID, got 0x{cat_bytes[p]:02x}")
    p += 1
    content_len, p = _rlen(cat_bytes, p)
    return cat_bytes[p : p + content_len]


# ---------------------------------------------------------------------------
# RFC 3161 timestamping
# ---------------------------------------------------------------------------

def get_rfc3161_token(signature_bytes: bytes, ts_url: str) -> bytes:
    """Request an RFC 3161 timestamp token; return the TimeStampToken DER bytes.

    Sends a TimeStampReq with certReq=TRUE so the response includes the TSA
    certificate, which signtool and Windows need to verify the timestamp.
    """
    # Build TimeStampReq
    msg_hash = hashlib.sha256(signature_bytes).digest()
    msg_imprint = der_seq(
        der_seq(der_oid(OID_SHA256), der_null()),
        der_octet(msg_hash),
    )
    ts_req = der_seq(
        der_int(1),
        msg_imprint,
        b"\x01\x01\xff",   # certReq BOOLEAN TRUE
    )

    req = urllib.request.Request(
        ts_url, data=ts_req,
        headers={"Content-Type": "application/timestamp-query"},
    )
    resp = urllib.request.urlopen(req, timeout=20).read()

    # Parse TimeStampResp ::= SEQUENCE { PKIStatusInfo, TimeStampToken OPTIONAL }
    p = 1                                   # skip outer SEQUENCE tag
    _, p = _rlen(resp, p)
    if resp[p] != 0x30:
        raise ValueError("TSP response missing PKIStatusInfo")
    p += 1
    status_len, p = _rlen(resp, p)
    status_end = p + status_len
    # Read PKIStatus INTEGER
    if resp[p] == 0x02:
        p += 1; int_len, p = _rlen(resp, p)
        status = int.from_bytes(resp[p : p + int_len], "big")
        if status not in (0, 1):            # 0=granted, 1=grantedWithMods
            raise RuntimeError(f"TSP server returned status={status}")
    p = status_end
    # TimeStampToken ::= ContentInfo (a PKCS#7 SEQUENCE)
    if p < len(resp) and resp[p] == 0x30:
        tok_start = p; p += 1
        tok_len, p = _rlen(resp, p)
        return resp[tok_start : p + tok_len]
    raise ValueError("TSP response contains no TimeStampToken")


# ---------------------------------------------------------------------------
# Signing
# ---------------------------------------------------------------------------

def sign_cat(cat_bytes: bytes, pfx_bytes: bytes, password: str,
             ts_url: str | None = None) -> bytes:
    """Sign an unsigned .cat file; return the signed bytes.

    Parameters
    ----------
    cat_bytes : bytes
        Unsigned .cat (from inf2cat.py or Microsoft Inf2Cat).
    pfx_bytes : bytes
        Raw PKCS#12 / PFX file content.
    password : str
        PFX password.
    ts_url : str | None
        RFC 3161 timestamp server URL.  Pass None to skip timestamping.
    """
    # --- Load PFX ---
    pw = password.encode() if isinstance(password, str) else password
    p12 = load_pkcs12(pfx_bytes, pw)
    private_key = p12.key
    leaf_cert   = p12.cert.certificate
    chain_certs = [c.certificate for c in (p12.additional_certs or [])]

    if not hasattr(private_key, "sign"):
        raise TypeError("PFX key does not support signing (expected RSA or EC private key)")

    # --- Digest the CTL body ---
    ctl_content    = extract_ctl_content(cat_bytes)
    content_digest = hashlib.sha256(ctl_content).digest()
    signing_time   = datetime.now(timezone.utc)

    # --- Build signedAttrs (DER SET — also used as-is for hashing) ---
    # Per RFC 5652 §5.4: the message-digest is computed over the content bytes;
    # the signature covers the DER encoding of signedAttrs as a SET (0x31 tag).
    signed_attrs = der_set(
        der_seq(der_oid(OID_CONTENT_TYPE),   der_set(der_oid(OID_CTL))),
        der_seq(der_oid(OID_MESSAGE_DIGEST), der_set(der_octet(content_digest))),
        der_seq(der_oid(OID_SIGNING_TIME),   der_set(der_utctime(signing_time))),
    )
    # In the SignerInfo structure, signedAttrs is tagged [0] IMPLICIT (0xA0).
    # Only the tag byte changes; length bytes and body are identical.
    signed_attrs_in_si = b"\xa0" + signed_attrs[1:]

    # --- RSA-SHA256 signature over signedAttrs (as SET) ---
    # The key type determines which padding/algorithm to use.
    from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
    from cryptography.hazmat.primitives.asymmetric.ec import EllipticCurvePrivateKey
    if isinstance(private_key, RSAPrivateKey):
        signature = private_key.sign(signed_attrs, padding.PKCS1v15(), hashes.SHA256())
        sig_alg   = der_seq(der_oid(OID_RSA), der_null())
    elif isinstance(private_key, EllipticCurvePrivateKey):
        from cryptography.hazmat.primitives.asymmetric import ec
        OID_ECDSA_SHA256 = "1.2.840.10045.4.3.2"
        signature = private_key.sign(signed_attrs, ec.ECDSA(hashes.SHA256()))
        sig_alg   = der_seq(der_oid(OID_ECDSA_SHA256))
    else:
        raise TypeError(f"Unsupported key type: {type(private_key).__name__}")

    # --- RFC 3161 timestamp (optional) ---
    unsigned_attrs_bytes = b""
    if ts_url:
        fallback = "http://timestamp.sectigo.com"
        for server in [ts_url] + ([fallback] if ts_url != fallback else []):
            try:
                token  = get_rfc3161_token(signature, server)
                ts_seq = der_seq(der_oid(OID_TIMESTAMP_TOK), der_set(token))
                # unsignedAttrs uses [1] IMPLICIT tag
                unsigned_attrs_bytes = b"\xa1" + _der_len(len(ts_seq)) + ts_seq
                print(f"[INFO] Timestamped via {server}")
                break
            except Exception as e:
                print(f"[WARN] Timestamp failed ({server}): {e}")
        else:
            print("[WARN] All timestamp servers failed — signing without timestamp")

    # --- Assemble SignerInfo ---
    issuer_der = leaf_cert.issuer.public_bytes()   # DER-encoded Name
    signer_info = der_seq(
        der_int(1),                                          # version
        der_seq(issuer_der, der_int(leaf_cert.serial_number)),  # issuerAndSerialNumber
        der_seq(der_oid(OID_SHA256), der_null()),           # digestAlgorithm
        signed_attrs_in_si,                                  # signedAttrs [0] IMPLICIT
        sig_alg,                                             # signatureAlgorithm
        der_octet(signature),                                # signature
        *([unsigned_attrs_bytes] if unsigned_attrs_bytes else []),
    )

    # --- certificates [0] IMPLICIT: leaf + chain ---
    certs_der = b"".join(
        c.public_bytes(serialization.Encoding.DER) for c in [leaf_cert] + chain_certs
    )
    certs_field = b"\xa0" + _der_len(len(certs_der)) + certs_der

    # --- Rebuild encapContentInfo with the original CTL bytes ---
    ctl_field = b"\xa0" + _der_len(len(ctl_content)) + ctl_content
    encap_ci  = der_seq(der_oid(OID_CTL), ctl_field)

    # --- Final SignedData → ContentInfo ---
    signed_data = der_seq(
        der_int(1),
        der_set(der_seq(der_oid(OID_SHA256), der_null())),  # digestAlgorithms
        encap_ci,
        certs_field,
        der_set(signer_info),                                # signerInfos
    )
    return der_seq(
        der_oid(OID_SIGNED_DATA),
        der_ctx(0, signed_data),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Sign a Windows .cat catalog file (no WDK/SDK required).",
        epilog="Example: python sign_cat.py driver.cat --pfx cert.pfx --password falcon",
    )
    ap.add_argument("cat",           help=".cat file to sign")
    ap.add_argument("--pfx",         required=True, help="PFX / PKCS#12 certificate file")
    ap.add_argument("--password",    default="",    help="PFX password (default: empty string)")
    ap.add_argument("--out",         default=None,  help="Output path (default: overwrite input)")
    ap.add_argument("--timestamp",   default="http://timestamp.digicert.com",
                    help="RFC 3161 timestamp server URL (pass '' to skip)")
    args = ap.parse_args()

    cat_bytes = open(args.cat,  "rb").read()
    pfx_bytes = open(args.pfx,  "rb").read()
    ts_url    = args.timestamp or None
    out_path  = args.out or args.cat

    print(f"[INFO] Signing {args.cat} ...")
    signed = sign_cat(cat_bytes, pfx_bytes, args.password, ts_url)

    with open(out_path, "wb") as fh:
        fh.write(signed)

    size_diff = len(signed) - len(cat_bytes)
    print(f"[OK]   {out_path}  ({len(signed):,} bytes, +{size_diff:,} from signature)")
    print()
    print("Verify with:")
    print(f'  signtool verify /pa /v "{out_path}"')


if __name__ == "__main__":
    main()
