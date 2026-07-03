#!/usr/bin/env python3
"""
inf2cat.py  —  Generate a Windows driver Security Catalog (.cat) file.

Replicates Microsoft's Inf2Cat WDK tool without requiring the WDK or any
Windows API.  Produces an *unsigned* .cat that can then be signed with signtool.

Usage:
    python inf2cat.py <driver_dir> --os 10_X64
    python inf2cat.py <driver_dir> --os 10_X64,10_X86
    python inf2cat.py <driver_dir> --os 10_X64 --out my_driver.cat

Requirements:
    Python 3.6+  —  no third-party dependencies.

Catalog format
--------------
The generated .cat is a v2 catalog (SHA-256, OID 1.3.6.1.4.1.311.12.1.3),
which is the current Inf2Cat default for Windows 10+.  It is a DER-encoded
PKCS#7 SignedData structure wrapping a Microsoft CTL (Certificate Trust List).

File hashing
------------
Each file listed in [SourceDisksFiles] (plus the .inf itself) gets a
SubjectIdentifier entry in the CTL.  The hash stored there depends on file type:

  PE files (.exe, .dll, .sys, …)
      Authenticode hash — SHA-256 over the file excluding:
        • the 4-byte checksum in the Optional Header
        • the 8-byte IMAGE_DIRECTORY_ENTRY_SECURITY data-directory entry
        • the certificate table (Authenticode signature blob, if any)
      References:
        https://download.microsoft.com/download/9/c/5/9c5b2167-8017-4bae-9fde-d599bac8184a/Authenticode_PE.docx
        https://github.com/LINBIT/generate-cat-file  (strip-pe-image.c)

  Signed Cabinet files (.cab with FLAG_RESERVE_PRESENT + embedded PKCS#7)
      The hash is read directly from the SpcIndirectDataContent.messageDigest
      field inside the appended PKCS#7 blob — equivalent to running
      CryptCATAdminCalcHashFromFileHandle2 on the file.

  Unsigned Cabinet files (.cab without a reserve/signature header)
      osslsigncode algorithm: SHA-256 over data[0:4] + data[8:] — the entire
      file except the 4-byte reserved1 field at offset 4.
      References:
        https://github.com/mtrojnar/osslsigncode  (cab.c — cab_digest_calc)
        https://github.com/Devolutions/psign      (crates/psign-sip-digest/src/cab_digest.rs)

  All other files
      Plain SHA-256 of the raw file bytes.

Dual entries (SHA-256 + SHA-1)
------------------------------
Inf2Cat generates TWO CTL entries for every file:

  1. Main entry (SubjectIdentifier = 32-byte SHA-256 hash):
       Attributes: MemberInfoV2 + OSAttr + File + SpcIndirectDataContent
     For files that are already signed (PE/CAB with embedded Authenticode),
     the SpcIndirectDataContent is copied verbatim from the file's own PKCS#7
     signature — which can be hundreds of KB (e.g. 747 KB for a dual-signed DLL).
     For unsigned files a minimal DigestInfo-only SpcIndirectDataContent is built.

  2. Supplementary entry (SubjectIdentifier = 20-byte SHA-1 hash):
       Attributes: MemberInfoV2 + OSAttr + File  (NO SpcIndirectDataContent)
     The SHA-1 hash algorithm follows the same logic as SHA-256 (Authenticode
     for PE/CAB, plain for everything else), using SHA-1 instead.
     For signed CABs the psign selective-field algorithm is used:
       SHA-1 over: magic[4] + header[8:34] + padding[56:60] + folders + data[..sigpos]
       References:
         https://github.com/Devolutions/psign (crates/psign-sip-digest/src/cab_digest.rs)

All entries (main + supplementary) are sorted together by their raw
SubjectIdentifier bytes — SHA-1 and SHA-256 entries are interleaved in the output.

SpcIndirectDataContent extraction
-----------------------------------
For pre-signed PE/CAB files, the SpcIndirectDataContent SEQUENCE is extracted
from the file's embedded WIN_CERTIFICATE PKCS7 and embedded verbatim.  The
PKCS7 may contain multiple SPC_INDIRECT_DATA_CONTENT OID occurrences; we pick
the LARGEST SEQUENCE found (which contains page hashes via SpcSerializedObject
when present).  For unsigned files a minimal DigestInfo-only SpcIDC is built.

Limitation: if a PE was re-signed after the reference catalog was generated
(same Authenticode hash, new signing chain), the embedded SpcIDC blobs will
differ byte-for-byte even though all SubjectIdentifiers remain identical.
Windows validates catalogs by SubjectIdentifier hash only, so this is correct
for all practical uses.

Notes
-----
- Files listed in [SourceDisksFiles] that cannot be found are skipped with a
  warning.  The .inf file itself is always included in the catalog.
- Files in [SignatureAttributes.PETrust] get a "PETrusted" attribute appended
  to their CTL entry (not yet implemented in this script).
"""

import argparse
import hashlib
import os
import re
import struct
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

def _der_read_len(data: bytes, pos: int) -> tuple[int, int]:
    """Read a DER length at pos; return (length, new_pos)."""
    if pos >= len(data):
        return 0, pos
    b = data[pos]; pos += 1
    if b < 0x80:
        return b, pos
    n = b & 0x7F
    if pos + n > len(data):
        return 0, pos + n
    return int.from_bytes(data[pos : pos + n], "big"), pos + n


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
OID_SPC_CAB_DATA             = "1.3.6.1.4.1.311.2.1.25"
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


def _build_spc(file_hash: bytes, is_pe: bool, spc_der: bytes | None = None) -> bytes:
    """
    SPC_INDIRECT_DATA attribute value (the SET wrapping SpcIndirectDataContent).

    When spc_der is provided (extracted from the file's own embedded signature),
    it is used verbatim as the SpcIndirectDataContent — this is what Inf2Cat does
    for already-signed files (can be 100s of KB for dual-signed DLLs).

    When spc_der is None, a minimal SpcIndirectDataContent is built from scratch:
      PE files use SPC_PE_IMAGE_DATA (.2.1.15):
        SEQ { OID(SPC_PE_IMAGE_DATA)  SEQ { BIT_STRING(a0,5unused)  [0]{[2]{[0]empty}} } }
      Non-PE files use SPC_CAB_DATA (.2.1.25):
        SEQ { OID(SPC_CAB_DATA)  [2]{[0]empty} }

    Both verified against a real Inf2Cat-generated .cat file.
    """
    if spc_der is not None:
        return der_set(spc_der)

    if is_pe:
        flags_bs = b"\x03\x02\x05\xa0"   # BIT STRING, 2 bytes, 5 unused bits, value 0xa0
        spc_link = der_ctx(0, der_ctx(2, der_ctx_implicit(0)))
        spc_content = der_seq(
            der_oid(OID_SPC_PE_IMAGE_DATA),
            der_seq(flags_bs, spc_link),
        )
    else:
        spc_link = der_ctx(2, der_ctx_implicit(0))   # [2] { [0] empty }
        spc_content = der_seq(
            der_oid(OID_SPC_CAB_DATA),
            spc_link,
        )

    digest_info = der_seq(
        der_seq(der_oid(OID_SHA256), der_null()),
        der_octet(file_hash),
    )

    spc_indirect_data = der_seq(spc_content, digest_info)
    return der_set(spc_indirect_data)


def _build_entry(filename: str, file_hash: bytes, os_attr: str, is_pe: bool,
                  spc_der: bytes | None = None) -> bytes:
    """
    One CTL entry (main, SHA-256):
      SEQUENCE {
        OCTET STRING  -- SubjectIdentifier = SHA-256 of file
        SET {         -- Attributes (DER-sorted)
          MemberInfoV2 attribute
          OSAttr NameValue attribute
          File NameValue attribute
          SPC hash attribute
        }
      }

    spc_der: pre-extracted SpcIndirectDataContent DER from the file's embedded
    Authenticode signature; when provided it is used verbatim (may be very large
    for pre-signed PE/CAB files).  Pass None to generate a minimal fallback.
    """
    member_info_v2 = der_seq(
        der_oid(OID_CAT_MEMBERINFO_V2),
        der_set(der_ctx_implicit(2)),      # SET { [2] implicit empty } — matches Inf2Cat
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
        _build_spc(file_hash, is_pe, spc_der),
    )

    # der_set() sorts the members automatically (DER canonical order).
    attributes = der_set(member_info_v2, os_attr_seq, file_attr_seq, spc_attr_seq)

    return der_seq(
        der_octet(file_hash),
        attributes,
    )


def _build_supplementary_entry(filename: str, sha1_hash: bytes, os_attr: str) -> bytes:
    """
    Supplementary SHA-1 CTL entry — one generated per file alongside the main SHA-256 entry.

    Structure is identical to the main entry but:
      - SubjectIdentifier is 20-byte SHA-1 (not 32-byte SHA-256)
      - No SPC_INDIRECT_DATA attribute

      SEQUENCE {
        OCTET STRING  -- SubjectIdentifier = SHA-1 Authenticode hash
        SET {
          MemberInfoV2 attribute
          OSAttr NameValue attribute
          File NameValue attribute
        }
      }
    """
    member_info_v2 = der_seq(
        der_oid(OID_CAT_MEMBERINFO_V2),
        der_set(der_ctx_implicit(2)),
    )
    os_attr_seq = der_seq(
        der_oid(OID_CAT_NAMEVALUE),
        der_set(_build_namevalue("OSAttr", os_attr)),
    )
    file_attr_seq = der_seq(
        der_oid(OID_CAT_NAMEVALUE),
        der_set(_build_namevalue("File", filename)),
    )
    attributes = der_set(member_info_v2, os_attr_seq, file_attr_seq)
    return der_seq(der_octet(sha1_hash), attributes)


def _build_ctl_body(entries_der: bytes, list_id: bytes, timestamp: datetime,
                    hwid_ext: bytes = b"") -> bytes:
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
        [0] EXPLICIT { SEQUENCE { ... } } -- Extensions: OS + HWID section (optional)
      }
    """
    return der_seq(
        der_seq(der_oid(OID_CATALOG_LIST)),
        der_octet(list_id),
        der_utctime(timestamp),
        der_seq(der_oid(OID_CATALOG_LIST_MEMBER_V2), der_null()),
        der_seq(entries_der),
        hwid_ext,   # b"" when no HWID section
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


def _build_ext_namevalue(name: str, value: str, flags: int = _NAME_VALUE_FLAGS) -> bytes:
    """
    NAMEVALUE entry for the catalog extension section.
    Identical to per-file NameValue but wrapped in OCTET STRING (04) instead of SET (31).
    Verified against real Inf2Cat output for HWID and OS entries.
    """
    body = der_seq(
        der_bmp(name),
        der_int(flags),
        der_octet(_utf16le_nul(value)),
    )
    return der_seq(der_oid(OID_CAT_NAMEVALUE), der_octet(body))


def _decorator_to_os_value(decorator: str) -> str | None:
    """
    Convert an INF OS decorator to the catalog OS value format.
    Examples: 'NTamd64.10.0' -> '_v100_X64',  'NTx86.6.3' -> '_v63_X86'
    """
    d = decorator.lower().strip()
    if not d.startswith("nt"):
        return None
    if "arm64" in d:
        arch = "ARM64"
    elif "ia64" in d:
        arch = "IA64"
    elif "amd64" in d:
        arch = "X64"
    else:
        arch = "X86"
    m = re.search(r"\.(\d+)\.(\d+)", d)
    if not m:
        return None
    version = m.group(1) + m.group(2)  # "10.0" -> "100", "6.3" -> "63"
    return "_v%s_%s" % (version, arch)


def _build_hwid_section(hwids: list[str], os_values: list[str]) -> bytes:
    """
    Catalog extension block appended after CTLEntries in the CTL body:

      [0] EXPLICIT {
        SEQUENCE {
          SEQUENCE { OID(CAT_NAMEVALUE) OCTET_STRING { SEQ{ BMP("OS") ... } } }  -- per OS
          SEQUENCE { OID(CAT_NAMEVALUE) OCTET_STRING { SEQ{ BMP("HWIDn") ... } } }
          ...
          SEQUENCE { OID(CAT_NAMEVALUE) OCTET_STRING { SEQ{ BMP("HWID0") ... } } }
        }
      }

    HWIDs are numbered n-1 down to 0 (highest first), matching real Inf2Cat output.
    OS values come from INF [Manufacturer] decorators (e.g. 'NTamd64.10.0' -> '_v100_X64').
    """
    entries: list[bytes] = []
    # PE=TRUSTED is always the first entry; flags differ (0x10001 not 0x10010001)
    entries.append(_build_ext_namevalue("PE", "TRUSTED", 0x10001))
    for os_val in os_values:
        entries.append(_build_ext_namevalue("OS", os_val))
    # HWID_number = INF_line_index + 1 (1-based).
    # Stored in descending order (highest number first), so iterate reversed.
    n = len(hwids)
    for i, hwid in enumerate(reversed(hwids)):
        entries.append(_build_ext_namevalue("HWID%d" % (n - i), hwid))
    return der_ctx(0, der_seq(b"".join(entries)))


# ---------------------------------------------------------------------------
# INF parsing
# ---------------------------------------------------------------------------

def parse_inf_hwids(inf_path: str) -> tuple[list[str], list[str]]:
    """
    Parse hardware IDs and OS values from an INF's [Manufacturer] / [Models] sections.
    Returns (hwids, os_values):
      hwids     -- lowercase PnP IDs like 'pci\\ven_1002&dev_7340', deduplicated, in order
      os_values -- catalog OS strings like '_v100_X64', derived from [Manufacturer] decorators
    """
    with open(inf_path, encoding="utf-8-sig", errors="replace") as fh:
        content = fh.read()

    hwids: list[str] = []
    seen_hwids: set[str] = set()
    os_values: list[str] = []
    seen_os: set[str] = set()

    mfg_match = re.search(
        r"^\[Manufacturer\](.*?)(?=^\[|\Z)",
        content, re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    if not mfg_match:
        return hwids, os_values

    model_section_names: list[str] = []
    for line in mfg_match.group(1).splitlines():
        line = re.sub(r";.*", "", line).strip()
        if not line or "=" not in line:
            continue
        rhs = line.split("=", 1)[1].strip()
        parts = [p.strip() for p in rhs.split(",")]
        base_section = parts[0]
        decorators = [d for d in parts[1:] if d]
        for d in decorators:
            ov = _decorator_to_os_value(d)
            if ov and ov not in seen_os:
                seen_os.add(ov)
                os_values.append(ov)
            model_section_names.append("%s.%s" % (base_section, d))
        model_section_names.append(base_section)

    for section_name in model_section_names:
        pattern = r"^\[%s\](.*?)(?=^\[|\Z)" % re.escape(section_name)
        sec_match = re.search(pattern, content, re.MULTILINE | re.DOTALL | re.IGNORECASE)
        if not sec_match:
            continue
        for line in sec_match.group(1).splitlines():
            line = re.sub(r";.*", "", line).strip()
            if not line or "=" not in line:
                continue
            rhs = line.split("=", 1)[1].strip()
            parts = [p.strip() for p in rhs.split(",")]
            # parts[0] = install section; parts[1:] = hardware IDs
            for hwid in parts[1:]:
                hwid = hwid.strip().lower()
                if hwid and hwid not in seen_hwids:
                    seen_hwids.add(hwid)
                    hwids.append(hwid)

    return hwids, os_values


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


def _pe_authenticode_hash(data: bytes) -> bytes | None:
    """
    Compute the Authenticode SHA-256 hash of PE file bytes, matching Inf2Cat behavior.

    The hash covers the entire file EXCEPT:
      - The 4-byte checksum field in the Optional Header
      - The 8-byte IMAGE_DIRECTORY_ENTRY_SECURITY entry in the Data Directory
      - The certificate table itself (the actual Authenticode signature blob)

    For unsigned PE files the certificate table is absent (RVA=0/Size=0), so only
    the checksum and the zeroed security directory entry are excluded.
    Returns None if the bytes are not a valid PE (caller falls back to raw SHA-256).
    """
    try:
        pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_off : pe_off + 4] != b"PE\x00\x00":
            return None
        opt_off = pe_off + 24                          # 4-byte sig + 20-byte COFF header
        magic   = struct.unpack_from("<H", data, opt_off)[0]
        if magic == 0x10B:                             # PE32
            cksum_off = opt_off + 64
            dirs_off  = opt_off + 96
        elif magic == 0x20B:                           # PE32+
            cksum_off = opt_off + 64
            dirs_off  = opt_off + 112
        else:
            return None
        secdir_off = dirs_off + 32                     # index 4 × 8 bytes per entry
        cert_rva   = struct.unpack_from("<I", data, secdir_off)[0]
        cert_size  = struct.unpack_from("<I", data, secdir_off + 4)[0]

        h = hashlib.sha256()
        h.update(data[:cksum_off])                         # before checksum
        h.update(data[cksum_off + 4 : secdir_off])         # after checksum → before secdir entry
        if cert_rva:
            h.update(data[secdir_off + 8 : cert_rva])      # after secdir entry → before cert blob
            h.update(data[cert_rva + cert_size :])         # after cert blob → EOF
        else:
            h.update(data[secdir_off + 8 :])               # after secdir entry → EOF (no cert)
        return h.digest()
    except Exception:
        return None


_FLAG_RESERVE_PRESENT = 0x0004


def _cab_authenticode_hash(data: bytes) -> bytes | None:
    """Return the Authenticode hash of a Cabinet (.cab) file.

    Signed CABs (FLAG_RESERVE_PRESENT set, sigpos/siglen non-zero):
        The hash is read directly from the SpcIndirectDataContent.messageDigest
        embedded in the appended PKCS7 blob.  This avoids re-implementing the
        full CAB hash algorithm for the common case.

    Unsigned CABs (no reserve header):
        Algorithm follows osslsigncode / Devolutions psign cab_digest.rs:
        SHA-256 over data[0:4] + data[8:] — the whole file except the 4-byte
        reserved1 field at offset 4.  This matches what Windows
        CryptCATAdminCalcHashFromFileHandle2 returns for unsigned CABs.

    Returns None for non-CAB data; caller falls back to raw SHA-256.
    """
    try:
        if data[:4] != b"MSCF":
            return None
        flags = struct.unpack_from("<H", data, 30)[0]

        if flags & _FLAG_RESERVE_PRESENT:
            # Signed CAB — read SpcIndirectDataContent hash from embedded PKCS7.
            # header_size is the 4-byte LE value at offset 36 (cbCFHeader[2] +
            # cbCFFolder[1] + cbCFData[1]); must equal 20 (0x14).
            header_size = struct.unpack_from("<I", data, 36)[0]
            if header_size != 20:
                return None
            if struct.unpack_from("<I", data, 40)[0] != 0x00100000:  # abReserve marker
                return None
            sigpos = struct.unpack_from("<I", data, 44)[0]
            siglen = struct.unpack_from("<I", data, 48)[0]
            if sigpos == 0 or siglen == 0:
                return None
            sig = data[sigpos : sigpos + siglen]
            if not sig or sig[0] != 0x30:
                return None
            # Locate the first DigestInfo(SHA-256, hash) in the PKCS7 blob.
            # Pattern: SHA-256 OID (11 bytes) + optional NULL (2 bytes) + OCTET STRING(32).
            sha256_oid = bytes.fromhex("0609608648016503040201")
            search = sig[:4096]
            pos = 0
            while True:
                pos = search.find(sha256_oid, pos)
                if pos == -1:
                    return None
                after = pos + 11
                if search[after : after + 2] == b"\x05\x00":
                    after += 2
                if after + 34 <= len(search) and search[after] == 0x04 and search[after + 1] == 0x20:
                    return search[after + 2 : after + 34]
                pos += 1
        else:
            # Unsigned CAB — hash everything except reserved1 (bytes 4–7).
            h = hashlib.sha256()
            h.update(data[0:4])
            h.update(data[8:])
            return h.digest()
    except Exception:
        return None


def sha256_of(path: str) -> bytes:
    """Return the catalog hash of a file, matching Inf2Cat behavior.

    - PE files        : Authenticode hash (excludes checksum, security dir
                        entry, and certificate table).
    - Signed CABs     : hash read from the embedded SpcIndirectDataContent
                        digest (equivalent to CryptCATAdminCalcHashFromFileHandle2).
    - Unsigned CABs   : SHA-256 over the file excluding the 4-byte reserved1
                        field (osslsigncode / psign algorithm).
    - Everything else : plain SHA-256.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:2] == b"MZ":
        h = _pe_authenticode_hash(data)
        if h is not None:
            return h
    if data[:4] == b"MSCF":
        h = _cab_authenticode_hash(data)
        if h is not None:
            return h
    return hashlib.sha256(data).digest()


def _pe_authenticode_hash_sha1(data: bytes) -> bytes | None:
    """SHA-1 Authenticode hash of PE bytes; same field exclusions as the SHA-256 version."""
    try:
        pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_off : pe_off + 4] != b"PE\x00\x00":
            return None
        opt_off = pe_off + 24
        magic   = struct.unpack_from("<H", data, opt_off)[0]
        if magic == 0x10B:
            cksum_off = opt_off + 64; dirs_off = opt_off + 96
        elif magic == 0x20B:
            cksum_off = opt_off + 64; dirs_off = opt_off + 112
        else:
            return None
        secdir_off = dirs_off + 32
        cert_rva   = struct.unpack_from("<I", data, secdir_off)[0]
        cert_size  = struct.unpack_from("<I", data, secdir_off + 4)[0]
        h = hashlib.sha1()
        h.update(data[:cksum_off])
        h.update(data[cksum_off + 4 : secdir_off])
        if cert_rva:
            h.update(data[secdir_off + 8 : cert_rva])
            h.update(data[cert_rva + cert_size :])
        else:
            h.update(data[secdir_off + 8 :])
        return h.digest()
    except Exception:
        return None


def _cab_authenticode_hash_sha1(data: bytes) -> bytes | None:
    """Return the SHA-1 Authenticode hash of a Cabinet file.

    Signed CABs: psign selective-field algorithm using SHA-1 —
        SHA-1 over: magic[0:4] + header_fields[8:34] + padding[56:60]
                    + CFFOLDER entries + cabinet data up to sigpos.
        Skips: reserved1[4:8], iCabinet area[34:56], and the signature itself.
        Reference: Devolutions/psign (crates/psign-sip-digest/src/cab_digest.rs)

    Unsigned CABs: SHA-1 over data[0:4] + data[8:] (same skip of reserved1).
    """
    try:
        if data[:4] != b"MSCF":
            return None
        flags    = struct.unpack_from("<H", data, 30)[0]
        nfolders = struct.unpack_from("<H", data, 26)[0]

        if flags & _FLAG_RESERVE_PRESENT:
            header_size = struct.unpack_from("<I", data, 36)[0]
            if header_size != 20:
                return None
            sigpos = struct.unpack_from("<I", data, 44)[0]
            if sigpos == 0:
                return None
            h = hashlib.sha1()
            h.update(data[0:4])      # MSCF magic
            h.update(data[8:34])     # header fields (cbCabinet..setID), skip reserved1[4:8]
            # skip [34:56] — iCabinet + reserve descriptor bytes (sigpos/siglen fields)
            h.update(data[56:60])    # trailing 4-byte reserve padding
            off = 60
            for _ in range(nfolders):
                h.update(data[off : off + 8])
                off += 8
            h.update(data[off : sigpos])
            return h.digest()
        else:
            h = hashlib.sha1()
            h.update(data[0:4])
            h.update(data[8:])
            return h.digest()
    except Exception:
        return None


def sha1_of(path: str) -> bytes:
    """Return the SHA-1 catalog hash of a file (supplementary-entry algorithm).

    Follows the same dispatch as sha256_of but using SHA-1:
      - PE files        : SHA-1 Authenticode hash.
      - Signed CABs     : psign selective-field SHA-1.
      - Unsigned CABs   : SHA-1 over data[0:4] + data[8:].
      - Everything else : plain SHA-1.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:2] == b"MZ":
        h = _pe_authenticode_hash_sha1(data)
        if h is not None:
            return h
    if data[:4] == b"MSCF":
        h = _cab_authenticode_hash_sha1(data)
        if h is not None:
            return h
    return hashlib.sha1(data).digest()


# ---------------------------------------------------------------------------
# SpcIndirectDataContent extraction (for pre-signed files)
# ---------------------------------------------------------------------------

# DER-encoded OID 1.3.6.1.4.1.311.2.1.4 (SpcIndirectDataContent)
_SPC_INDIRECT_DATA_OID_DER = bytes.fromhex("060a2b060104018237020104")


def _extract_spc_from_pkcs7(pkcs7: bytes) -> bytes | None:
    """Extract SpcIndirectDataContent SEQUENCE DER from a PKCS7 SignedData blob.

    Scans ALL occurrences of the SpcIndirectDataContent OID and returns the
    LARGEST matching SEQUENCE.  The PKCS7 may contain multiple copies — a small
    (~100 byte) version in the primary ContentInfo and a large version (possibly
    hundreds of KB) elsewhere that includes page hashes via SpcSerializedObject.
    Inf2Cat always embeds the largest one.
    """
    best: bytes | None = None
    pos = 0
    while True:
        idx = pkcs7.find(_SPC_INDIRECT_DATA_OID_DER, pos)
        if idx == -1:
            break
        try:
            p = idx + len(_SPC_INDIRECT_DATA_OID_DER)
            # ContentInfo value may be [0] EXPLICIT (0xa0) or bare SEQUENCE (0x30).
            if p < len(pkcs7) and pkcs7[p] == 0xA0:
                p += 1
                _, p = _der_read_len(pkcs7, p)
            if p < len(pkcs7) and pkcs7[p] == 0x30:
                seq_start = p; p += 1
                seq_len, p = _der_read_len(pkcs7, p)
                candidate = pkcs7[seq_start : p + seq_len]
                if best is None or len(candidate) > len(best):
                    best = candidate
        except Exception:
            pass
        pos = idx + 1
    return best


def _extract_pe_spc_indirect_data(data: bytes) -> bytes | None:
    """Extract SpcIndirectDataContent DER from a PE file's embedded WIN_CERTIFICATE."""
    try:
        pe_off = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe_off : pe_off + 4] != b"PE\x00\x00":
            return None
        opt_off = pe_off + 24
        magic   = struct.unpack_from("<H", data, opt_off)[0]
        if magic == 0x10B:
            dirs_off = opt_off + 96
        elif magic == 0x20B:
            dirs_off = opt_off + 112
        else:
            return None
        secdir_off = dirs_off + 32
        cert_rva   = struct.unpack_from("<I", data, secdir_off)[0]
        cert_size  = struct.unpack_from("<I", data, secdir_off + 4)[0]
        if not cert_rva or not cert_size:
            return None
        # WIN_CERTIFICATE: length(4) + revision(2) + certType(2) + data
        wc_len = struct.unpack_from("<I", data, cert_rva)[0]
        pkcs7 = data[cert_rva + 8 : cert_rva + wc_len]
        return _extract_spc_from_pkcs7(pkcs7)
    except Exception:
        return None


def _extract_cab_spc_indirect_data(data: bytes) -> bytes | None:
    """Extract SpcIndirectDataContent DER from a signed Cabinet file."""
    try:
        if data[:4] != b"MSCF":
            return None
        flags = struct.unpack_from("<H", data, 30)[0]
        if not (flags & _FLAG_RESERVE_PRESENT):
            return None
        header_size = struct.unpack_from("<I", data, 36)[0]
        if header_size != 20:
            return None
        sigpos = struct.unpack_from("<I", data, 44)[0]
        siglen = struct.unpack_from("<I", data, 48)[0]
        if not sigpos or not siglen:
            return None
        pkcs7 = data[sigpos : sigpos + siglen]
        return _extract_spc_from_pkcs7(pkcs7)
    except Exception:
        return None


def is_pe_file(path: str) -> bool:
    """Return True if the file starts with the MZ PE magic bytes."""
    try:
        with open(path, "rb") as fh:
            return fh.read(2) == b"MZ"
    except OSError:
        return False


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
    all_hwids: list[str] = []
    all_os_values: list[str] = []
    seen_hwids: set[str] = set()
    seen_os: set[str] = set()

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
        hwids, os_values = parse_inf_hwids(inf_path)
        for hwid in hwids:
            if hwid not in seen_hwids:
                seen_hwids.add(hwid)
                all_hwids.append(hwid)
        for ov in os_values:
            if ov not in seen_os:
                seen_os.add(ov)
                all_os_values.append(ov)

    if args.out:
        catalog_name = args.out
    if not catalog_name:
        catalog_name = "driver.cat"
        print(f"[WARN] No CatalogFile= in INF; using '{catalog_name}'")

    # Hash files (read once; compute SHA-256 + SHA-1 + extract SPC)
    print(f"[INFO] Hashing {len(all_filenames)} file(s) ...")
    entries: list[tuple[str, bytes, bytes, bool, bytes | None]] = []
    missing: list[str] = []

    for fname in all_filenames:
        path = find_file(driver_dir, fname)
        if path is None:
            missing.append(fname)
            continue
        with open(path, "rb") as fh:
            raw = fh.read()
        if raw[:2] == b"MZ":
            sha256  = _pe_authenticode_hash(raw) or hashlib.sha256(raw).digest()
            sha1    = _pe_authenticode_hash_sha1(raw) or hashlib.sha1(raw).digest()
            spc_der = _extract_pe_spc_indirect_data(raw)
            pe      = True
        elif raw[:4] == b"MSCF":
            sha256  = _cab_authenticode_hash(raw) or hashlib.sha256(raw).digest()
            sha1    = _cab_authenticode_hash_sha1(raw) or hashlib.sha1(raw).digest()
            spc_der = _extract_cab_spc_indirect_data(raw)
            pe      = False
        else:
            sha256  = hashlib.sha256(raw).digest()
            sha1    = hashlib.sha1(raw).digest()
            spc_der = None
            pe      = False
        entries.append((fname, sha256, sha1, pe, spc_der))

    if missing:
        print(f"[WARN] {len(missing)} file(s) not found (skipped):")
        for f in missing:
            print(f"       {f}")

    if not entries:
        print("[ERROR] No files to catalog.")
        sys.exit(1)

    pe_count  = sum(1 for *_, pe, _ in entries if pe)
    non_count = len(entries) - pe_count

    # Build dual entries (main SHA-256 + supplementary SHA-1) for every file,
    # then sort all entries together by SubjectIdentifier bytes.
    all_ctlentries: list[tuple[bytes, bytes]] = []
    for fname, sha256, sha1, pe, spc_der in entries:
        all_ctlentries.append((sha256, _build_entry(fname, sha256, OS_ATTR, pe, spc_der)))
        all_ctlentries.append((sha1,   _build_supplementary_entry(fname, sha1, OS_ATTR)))
    all_ctlentries.sort(key=lambda x: x[0])
    entries_der = b"".join(e for _, e in all_ctlentries)
    list_id = uuid.uuid4().bytes
    timestamp = datetime.now(timezone.utc)
    # Keep only OS extension values whose NT version matches our hardcoded OS_ATTR target.
    # OS_ATTR "2:10.0" -> NT version "100"; filter to e.g. ["_v100_X64"] only.
    target_ver = OS_ATTR.split(":", 1)[1].replace(".", "")  # "2:10.0" -> "100"
    matched_os = [v for v in all_os_values if v.startswith("_v%s_" % target_ver)]
    hwid_ext = _build_hwid_section(all_hwids, matched_os) if (all_hwids or matched_os) else b""

    ctl_body  = _build_ctl_body(entries_der, list_id, timestamp, hwid_ext)
    cat_bytes = _build_pkcs7(ctl_body)

    # Write — if --out is an absolute path use it directly, otherwise place in driver_dir
    if args.out and os.path.isabs(args.out):
        out_path = args.out
    else:
        out_path = os.path.join(driver_dir, catalog_name)
    with open(out_path, "wb") as fh:
        fh.write(cat_bytes)

    print(f"[OK]   {out_path}")
    print(f"       {len(entries)} file(s) cataloged  ({pe_count} PE, {non_count} non-PE)")
    print(f"       {len(all_ctlentries)} CTL entries  ({len(entries)} SHA-256 + {len(entries)} SHA-1)")
    print(f"       OSAttr = \"{OS_ATTR}\"")
    if all_hwids:
        os_str = ", ".join(matched_os) if matched_os else "(none)"
        print(f"       {len(all_hwids)} hardware ID(s) in HWID section  OS: {os_str}")
    if missing:
        print(f"       {len(missing)} skipped (not found)")
    print()
    print("Next: sign with signtool (or use the sign-driver skill):")
    print(f'  signtool sign /fd SHA256 /f "cert.pfx" /p <pw> /tr http://timestamp.digicert.com /td SHA256 "{out_path}"')


if __name__ == "__main__":
    main()
