---
name: deobfuscate-pci-id
description: Decodes AMD driver INF obfuscated registry key names (20-char uppercase hex strings starting with BD) back to PCI hardware IDs. Use this skill whenever the user pastes hex strings like BDFDED8CEFEF94EFFDFF and asks what they mean, wants to decode or deobfuscate AMD registry keys, asks "what PCI ID is this", or mentions "decode AMD registry key", "deobfuscate pci", or "decode pci key". Also trigger when the user pastes a list of such strings without explanation — they almost certainly want them decoded.
---

## Algorithm

AMD driver INF files use obfuscated 10-byte registry key names for device-specific `SoftwareDeviceSettings` entries. Each key encodes the full PCI hardware ID of the target device.

### Encoding layout (byte positions, 0-indexed)

| Pos | Value | Field |
|-----|-------|-------|
| 0 | `BD` | Magic prefix (fixed) |
| 1 | `~VEN_lo` | Low byte of Vendor ID, XOR'd with 0xFF |
| 2 | `~SSID_lo` | Low byte of Subsystem ID, XOR'd with 0xFF |
| 3 | `~DEV_hi` | High byte of Device ID, XOR'd with 0xFF |
| 4 | `~DEV_lo` | Low byte of Device ID, XOR'd with 0xFF |
| 5 | `~VEN_hi` | High byte of Vendor ID, XOR'd with 0xFF |
| 6 | `~SVID_lo` | Low byte of Subsystem Vendor ID, XOR'd with 0xFF |
| 7 | `~SVID_hi` | High byte of Subsystem Vendor ID, XOR'd with 0xFF |
| 8 | `~SSID_hi` | High byte of Subsystem ID, XOR'd with 0xFF |
| 9 | `~REV` | Revision byte, XOR'd with 0xFF |

### Decoding steps

1. Parse the 20-char hex string into 10 bytes
2. Verify byte 0 is `0xBD` (magic prefix)
3. XOR each remaining byte with `0xFF` to recover the original value
4. Reconstruct the fields:
   - `VEN` = (byte5 << 8) | byte1  (hi | lo)
   - `DEV` = (byte3 << 8) | byte4  (hi | lo)
   - `SVID` = (byte7 << 8) | byte6  (hi | lo)
   - `SSID` = (byte8 << 8) | byte2  (hi | lo)
   - `REV` = byte9
5. Format: `PCI\VEN_VVVV&DEV_DDDD&SUBSYS_SSSSXXXX&REV_RR`
   - `SUBSYS` = SSID (4 hex digits) + SVID (4 hex digits)

### Example

`BDFDED8CEFEF94EFFDFF` → bytes `BD FD ED 8C EF EF 94 EF FD FF`

- VEN = ~EF<<8 | ~FD = 10 02 → `1002` (AMD)
- DEV = ~8C<<8 | ~EF = 73 10 → `7310` (Navi10)
- SVID = ~EF<<8 | ~94 = 10 6B → `106B` (Apple)
- SSID = ~FD<<8 | ~ED = 02 12 → `0212`
- REV = ~FF = `00`

Result: `PCI\VEN_1002&DEV_7310&SUBSYS_0212106B&REV_00`

## Output format

When decoding one or more values, present results as a markdown table:

| Encoded Key | PCI Hardware ID | VEN | DEV | SSID | SVID | REV |
|---|---|---|---|---|---|---|
| `BDFDED8CEFEF94EFFDFF` | `PCI\VEN_1002&DEV_7310&SUBSYS_0212106B&REV_00` | 1002 | 7310 | 0212 | 106B | 00 |

Add a note after the table if any values fail the `BD` magic check (invalid / not AMD-encoded).

Do the decoding inline — no scripts needed, it's simple arithmetic.
