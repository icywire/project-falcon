#!/usr/bin/env python3
"""
inf2cat.py  —  Generate a Windows driver Security Catalog (.cat) file.

Replicates Microsoft's Inf2Cat WDK tool without requiring the WDK.
Produces an *unsigned* .cat that can then be signed with signtool.

Usage:
    python inf2cat.py <driver_dir> --os 10_X64
    python inf2cat.py <driver_dir> --os 10_X64,10_X86
    python inf2cat.py <driver_dir> --os 10_X64 --out my_driver.cat

Requirements:
    Python 3.6+  —  no third-party dependencies.

Notes:
    - Files listed in [SourceDisksFiles] that cannot be found are skipped with
      a warning.  The .inf file itself is always included in the catalog.
    - SHA-256 is computed on the raw file bytes.  If any input file already
      carries an Authenticode signature the hash will differ from what Windows
      Inf2Cat produces (which strips the existing signature before hashing).
      For unsigned driver packages this is never an issue.
    - The generated .cat is a v2 catalog (SHA-256, OID 1.3.6.1.4.1.311.12.1.3),
      which is the current Inf2Cat default for Windows 10+.
"""

import argparse
import hashlib
import os
import re
import sys
import uuid
from datetime import datetime, timezone


# OSAttr value written into every catalog entry.
# Format is "2:<NT-version>" where "2:" is the catalog format version.
# All Windows 10/11 and Server 2016+ share NT 10.0, so the value is always
# "2:10.0" for any modern driver.  Older values would be "2:6.3" (Win 8.1),
# "2:6.2" (Win 8), "2:6.1" (Win 7), "2:5.1" (XP) — verified against real
# Inf2Cat output.
OS_ATTR = "2:10.0"


# ---------------------------------------------------------------------------
# DER encoding primitives
# ---------------------------------------------------------------------------

def _der_len(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    if n < 0x100:
        return bytes([0x81, n])
    if n < 0x10000:
        return bytes([0x82, n >> 8, n & 0xFF])
    if n < 0x1000000:
        return bytes([0x83, n >> 16, (n >> 8) & 0xFF, n & 0xFF])
    raise OverflowError(f"DER length {n} is too large (> 24-bit)")


def _tlv(tag: int, body: bytes) -> bytes:
    return bytes([tag]) + _der_len(len(body)) + body


def der_seq(*items: bytes) -> bytes:
    return _tlv(0x30, b"".join(items))


def der_set(*items: bytes) -> bytes:
    # DER SET: members sorted lexicographically by their encoding.
    return _tlv(0x31, b"".join(sorted(items)))


def der_int(value: int) -> bytes:
    if value == 0:
        return _tlv(0x02, b"\x00")
    length = (value.bit_length() + 8) // 8  # +8 ensures room for sign bit
    data = value.to_bytes(length, "big").lstrip(b"\x00") or b"\x00"
    if data[0] & 0x80:
        data = b"\x00" + data
    return _tlv(0x02, data)


def der_octet(data: bytes) -> bytes:
    return _tlv(0x04, data)


def der_null() -> bytes:
    return b"\x05\x00"


def der_oid(dotted: str) -> bytes:
    """Encode an OID from its dotted-decimal string form."""
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


def der_bmp(text: str) -> bytes:
    """BMP string (UTF-16 big-endian)."""
    return _tlv(0x1E, text.encode("utf-16-be"))


def der_utctime(dt: datetime) -> bytes:
    return _tlv(0x17, dt.strftime("%y%m%d%H%M%SZ").encode("ascii"))


def der_ctx(tag: int, *items: bytes) -> bytes:
    """Explicit context-specific constructed tag."""
    return bytes([0xA0 | tag]) + _der_len(sum(len(i) for i in items)) + b"".join(items)


def der_ctx_implicit(tag: int, body: bytes = b"") -> bytes:
    """Implicit context-specific primitive tag."""
    return bytes([0x80 | tag]) + _der_len(len(body)) + body


# ---------------------------------------------------------------------------
# OIDs used in driver catalog files
# ---------------------------------------------------------------------------

OID_PKCS7_SIGNED_DATA        = "1.2.840.113549.1.7.2"
OID_CTL                      = "1.3.6.1.4.1.311.10.1"
OID_CATALOG_LIST             = "1.3.6.1.4.1.311.12.1.1"
OID_CATALOG_LIST_MEMBER_V2   = "1.3.6.1.4.1.311.12.1.3"
OID_CAT_NAMEVALUE            = "1.3.6.1.4.1.311.12.2.1"
OID_CAT_MEMBERINFO_V2        = "1.3.6.1.4.1.311.12.2.3"
OID_SPC_INDIRECT_DATA        = "1.3.6.1.4.1.311.2.1.4"
OID_SPC_PE_IMAGE_DATA        = "1.3.6.1.4.1.311.2.1.15"
OID_SHA256                   = "2.16.840.1.101.3.4.2.1"


# ---------------------------------------------------------------------------
# Catalog structure builders
# ---------------------------------------------------------------------------

_NAME_VALUE_FLAGS = 0x10010001  # observed in real Inf2Cat output


def _utf16le_nul(s: str) -> bytes:
    """UTF-16 LE with a null terminator (2 zero bytes)."""
    return s.encode("utf-16-le") + b"\x00\x00"


def _build_namevalue(name: str, value: str) -> bytes:
    """One CatalogNameValue sequence: BMP name + INT flags + OCTET value."""
    return der_seq(
        der_bmp(name),
        der_int(_NAME_VALUE_FLAGS),
        der_octet(_utf16le_nul(value)),
    )


def _build_spc(file_hash: bytes) -> bytes:
    """
    SPC_INDIRECT_DATA attribute value (the SET wrapping SpcIndirectDataContent).

    Structure verified against a real AMD/Inf2Cat-generated .cat file:

      SET {
        SEQ {                             -- SpcIndirectDataContent
          SEQ {                           -- SpcAttributeTypeAndOptionalValue
            OID(SPC_PE_IMAGE_DATA)
            SEQ {                         -- SpcPeImageData
              BIT STRING 0xa0 (5 unused)  -- flags
              [0] { [2] { [0] empty } }   -- empty file link
            }
          }
          SEQ {                           -- DigestInfo
            SEQ { OID(sha256), NULL }
            OCTET STRING[32]              -- SHA-256 hash
          }
        }
      }
    """
    flags_bs = b"\x03\x02\x05\xa0"   # BIT STRING, 2 bytes, 5 unused bits, value 0xa0

    spc_link = der_ctx(0,
        der_ctx(2,
            der_ctx_implicit(0),
        )
    )
    spc_pe_image_data = der_seq(flags_bs, spc_link)

    spc_attr_type = der_seq(
        der_oid(OID_SPC_PE_IMAGE_DATA),
        spc_pe_image_data,
    )

    digest_info = der_seq(
        der_seq(der_oid(OID_SHA256), der_null()),
        der_octet(file_hash),
    )

    spc_indirect_data = der_seq(spc_attr_type, digest_info)
    return der_set(spc_indirect_data)          # SET { SpcIndirectDataContent }


def _build_entry(filename: str, file_hash: bytes, os_attr: str) -> bytes:
    """
    One CTL entry:
      SEQUENCE {
        OCTET STRING  -- SubjectIdentifier = SHA-256 of file
        SET {         -- Attributes (DER-sorted)
          MemberInfoV2 attribute
          OSAttr NameValue attribute
          File NameValue attribute
          SPC hash attribute
        }
      }
    """
    member_info_v2 = der_seq(
        der_oid(OID_CAT_MEMBERINFO_V2),
        der_set(der_ctx_implicit(0)),      # SET { [0] implicit empty }
    )

    os_attr_seq = der_seq(
        der_oid(OID_CAT_NAMEVALUE),
        der_set(_build_namevalue("OSAttr", os_attr)),
    )

    file_attr_seq = der_seq(
        der_oid(OID_CAT_NAMEVALUE),
        der_set(_build_namevalue("File", filename)),
    )

    spc_attr_seq = der_seq(
        der_oid(OID_SPC_INDIRECT_DATA),
        _build_spc(file_hash),
    )

    # der_set() sorts the members automatically (DER canonical order).
    attributes = der_set(member_info_v2, os_attr_seq, file_attr_seq, spc_attr_seq)

    return der_seq(
        der_octet(file_hash),
        attributes,
    )


def _build_ctl_body(entries_der: bytes, list_id: bytes, timestamp: datetime) -> bytes:
    """
    Inner CTL (Certificate Trust List) body — Microsoft's proprietary format:

      SEQUENCE {
        SEQUENCE { OID(CATALOG_LIST) }    -- SubjectUsage
        OCTET STRING[16]                  -- ListIdentifier (random GUID bytes)
        UTCTime                           -- ThisUpdate
        SEQUENCE {                        -- SubjectAlgorithm
          OID(CATALOG_LIST_MEMBER_V2)
          NULL
        }
        SEQUENCE { ... CTL entries ... }  -- CTLEntries
      }
    """
    return der_seq(
        der_seq(der_oid(OID_CATALOG_LIST)),
        der_octet(list_id),
        der_utctime(timestamp),
        der_seq(der_oid(OID_CATALOG_LIST_MEMBER_V2), der_null()),
        der_seq(entries_der),
    )


def _build_pkcs7(ctl_body: bytes) -> bytes:
    """
    Wrap the CTL body in a PKCS#7 SignedData envelope (unsigned — no signerInfos).

      SEQUENCE {                          -- outer ContentInfo
        OID(pkcs7-signedData)
        [0] {                             -- EXPLICIT content
          SEQUENCE {                      -- SignedData
            INT(1)                        -- version
            SET {}                        -- digestAlgorithms (empty — unsigned)
            SEQUENCE {                    -- inner ContentInfo
              OID(szOID_CTL)
              [0] { <ctl_body> }
            }
            SET {}                        -- signerInfos (empty — unsigned)
          }
        }
      }
    """
    inner_ci = der_seq(
        der_oid(OID_CTL),
        der_ctx(0, ctl_body),
    )

    signed_data = der_seq(
        der_int(1),
        der_set(),           # empty digestAlgorithms
        inner_ci,
        der_set(),           # empty signerInfos
    )

    return der_seq(
        der_oid(OID_PKCS7_SIGNED_DATA),
        der_ctx(0, signed_data),
    )


# ---------------------------------------------------------------------------
# INF parsing
# ---------------------------------------------------------------------------

def parse_inf(inf_path: str) -> tuple[str | None, list[str]]:
    """Return (catalog_filename, [source_file_names])."""
    with open(inf_path, encoding="utf-8-sig", errors="replace") as fh:
        content = fh.read()

    cat_match = re.search(r"^CatalogFile\s*=\s*(.+)", content,
                          re.MULTILINE | re.IGNORECASE)
    catalog_name = cat_match.group(1).strip() if cat_match else None

    source_files: list[str] = []
    seen: set[str] = set()
    for section in re.finditer(
        r"^\[SourceDisksFiles[^\]]*\](.*?)(?=^\[|\Z)",
        content, re.MULTILINE | re.DOTALL,
    ):
        for line in section.group(1).splitlines():
            line = line.strip()
            if not line or line.startswith(";"):
                continue
            m = re.match(r"^([^=;,\s]+)\s*=", line)
            if m:
                fname = m.group(1)
                key = fname.lower()
                if key not in seen:
                    seen.add(key)
                    source_files.append(fname)

    return catalog_name, source_files


def find_file(base_dir: str, filename: str) -> str | None:
    """Recursively find a file by name (case-insensitive) under base_dir."""
    target = filename.lower()
    for root, _dirs, files in os.walk(base_dir):
        for f in files:
            if f.lower() == target:
                return os.path.join(root, f)
    return None


def sha256_of(path: str) -> bytes:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.digest()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Generate a Windows driver .cat catalog file (no WDK required).",
        epilog=(
            "Sign the output with signtool:\n"
            '  signtool sign /fd SHA256 /f cert.pfx /p <pw> \\\n'
            '    /tr http://timestamp.digicert.com /td SHA256 <output.cat>'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("driver_dir", help="Directory containing the .inf file(s)")
    ap.add_argument("--out", default=None,
                    help="Output .cat filename  (default: taken from INF CatalogFile=)")
    args = ap.parse_args()
    driver_dir = os.path.abspath(args.driver_dir)

    # Collect .inf files
    inf_files = [f for f in os.listdir(driver_dir) if f.lower().endswith(".inf")]
    if not inf_files:
        print(f"[ERROR] No .inf files in {driver_dir}")
        sys.exit(1)

    # Parse all INFs
    catalog_name: str | None = None
    all_filenames: list[str] = []
    seen: set[str] = set()

    for inf_name in inf_files:
        inf_path = os.path.join(driver_dir, inf_name)
        cat, sources = parse_inf(inf_path)
        if cat and not catalog_name:
            catalog_name = cat
        # The INF file itself is always cataloged
        if inf_name.lower() not in seen:
            seen.add(inf_name.lower())
            all_filenames.append(inf_name)
        for fname in sources:
            if fname.lower() not in seen:
                seen.add(fname.lower())
                all_filenames.append(fname)

    if args.out:
        catalog_name = args.out
    if not catalog_name:
        catalog_name = "driver.cat"
        print(f"[WARN] No CatalogFile= in INF; using '{catalog_name}'")

    # Hash files
    print(f"[INFO] Hashing {len(all_filenames)} file(s) ...")
    entries: list[tuple[str, bytes]] = []
    missing: list[str] = []

    for fname in all_filenames:
        path = find_file(driver_dir, fname)
        if path is None:
            missing.append(fname)
            continue
        h = sha256_of(path)
        entries.append((fname, h))

    if missing:
        print(f"[WARN] {len(missing)} file(s) not found (skipped):")
        for f in missing:
            print(f"       {f}")

    if not entries:
        print("[ERROR] No files to catalog.")
        sys.exit(1)

    # Sort by SubjectIdentifier (SHA-256 hash) — matches real Inf2Cat order
    entries.sort(key=lambda x: x[1])

    # Build catalog
    entries_der = b"".join(_build_entry(fname, h, OS_ATTR) for fname, h in entries)
    list_id = uuid.uuid4().bytes
    timestamp = datetime.now(timezone.utc)

    ctl_body  = _build_ctl_body(entries_der, list_id, timestamp)
    cat_bytes = _build_pkcs7(ctl_body)

    # Write
    out_path = os.path.join(driver_dir, catalog_name)
    with open(out_path, "wb") as fh:
        fh.write(cat_bytes)

    print(f"[OK]   {out_path}")
    print(f"       {len(entries)} file(s) cataloged")
    print(f"       OSAttr = \"{OS_ATTR}\"")
    if missing:
        print(f"       {len(missing)} skipped (not found)")
    print()
    print("Next: sign with signtool (or use the sign-driver skill):")
    print(f'  signtool sign /fd SHA256 /f "cert.pfx" /p <pw> /tr http://timestamp.digicert.com /td SHA256 "{out_path}"')


if __name__ == "__main__":
    main()
