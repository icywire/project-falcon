# AMD Driver Registry Keys — Notes

## PP_GfxOffControl

Controls GFXOFF — RLC firmware power-gates the entire GFX engine (shader arrays, clocks, voltage islands) at idle and restores it on demand.

- **Type:** `REG_DWORD`

| Value | Meaning |
|-------|---------|
| `0` | GFXOFF disabled |
| `1` | GFXOFF enabled |

| Driver | Value (Navi14) |
|--------|---------------|
| Falcon / Adrenalin 25.2.1 | not set (driver default = enabled) |
| Bootcamp 24.10.1 | `0` |
| RID 25.3.1 | `0` |
| Apple macpro / r6.4 | not set (key not present in older driver generation) |

**Power:** Significant idle power saving (~2–5 W on Navi14). No performance impact under load.
**Stability:** Can cause sleep/wake issues on some platforms.

---

## UseExecuteIndirectPacket

Controls whether the KMD uses a native hardware packet for D3D12 `ExecuteIndirect` calls, or falls back to a software-emulated path. `ExecuteIndirect` allows the GPU to generate its own draw/dispatch commands without CPU round-trips.

- **Type:** `REG_DWORD`

| Value | Meaning |
|-------|---------|
| `0` | Software-emulated path |
| `1` | Native GPU indirect packet |

| Driver | Value (Navi14) |
|--------|---------------|
| Falcon / Adrenalin 25.2.1 | `1` |
| Bootcamp 24.10.1 | `0` |
| RID 25.3.1 | `1` |
| Apple macpro / r6.4 | not set (key not present in older driver generation) |

**Performance:** Value `1` reduces CPU overhead in D3D12 GPU-driven rendering workloads. Impact is most visible in modern titles that use indirect draw heavily.

---

## EnableCrossFireAutoLink

Enables automatic detection and negotiation of a CrossFire link when a compatible second GPU is present on the PCIe bus.

- **Type:** `REG_DWORD`

| Value | Meaning |
|-------|---------|
| `0` | Auto-detection disabled |
| `1` | Auto-detection enabled |

| Driver | Value (Navi14) |
|--------|---------------|
| Falcon / Adrenalin 25.2.1 | `1` |
| Bootcamp 24.10.1 | `1` |
| RID 25.3.1 | `1` |
| Apple macpro / r6.4 | `1` |

**Performance:** No effect on single-GPU systems. On multi-GPU systems, enabling allows the driver to activate CrossFire without manual configuration.

---

## DisableFBCSupport

Controls Frame Buffer Compression (FBC) — an AMD display controller optimization that compresses framebuffer data to reduce memory bandwidth consumption at idle and during light workloads. On RDNA hardware, shaders can read and write compressed color data, and the display unit reads it without decompressing.

- **Type:** `REG_DWORD`

| Value | Meaning |
|-------|---------|
| `0` | FBC enabled (compression active) |
| `1` | FBC disabled |

| Driver | Value (Navi14) |
|--------|---------------|
| Falcon / Adrenalin 25.2.1 | not set (driver default = enabled) |
| Bootcamp 24.10.1 | `1` |
| RID 25.3.1 | `0` |
| Apple macpro / r6.4 | not set (key not present in older driver generation) |

**Power:** FBC reduces display-engine memory bandwidth, lowering idle power. Effect is modest on discrete GPUs but measurable.
**Performance:** No direct 3D rendering impact. Disabling may slightly increase memory bandwidth available to the GPU in edge cases but this is not a practical tuning lever.

---

## DisableFBCForFullScreenApp

Controls whether Frame Buffer Compression is disabled when a fullscreen application is active. On older hardware/drivers, FBC could cause visual artifacts in fullscreen apps, so it was disabled in that mode as a workaround. On RDNA/Navi hardware the driver considers FBC stable enough to leave active.

- **Type:** `REG_SZ`

| Value | Meaning |
|-------|---------|
| `"0"` | FBC stays enabled during fullscreen (no special-case override) |
| `"1"` | FBC disabled when a fullscreen app is running |

| Driver | Value (Navi14) |
|--------|---------------|
| Falcon / Adrenalin 25.2.1 | not set |
| Bootcamp 24.10.1 | not set (key only present in Polaris sections, set to `"1"`) |
| RID 25.3.1 | not set for Navi14 (Polaris sections set `"1"`) |
| Apple macpro / r6.4 | not set for Navi14 (r6.4 sets `"1"` for Polaris sections only) |

**Power/Performance:** Keeping FBC active during fullscreen (`0`) preserves the memory bandwidth savings. Disabling it (`1`) eliminates any risk of fullscreen compression artifacts at the cost of slightly higher display-engine bandwidth.

---

## DalPSRFeatureEnable

Controls Panel Self-Refresh (PSR) — an eDP power-saving feature where the GPU stops sending frame data to the panel when the image is static. The panel stores the last frame in its own local buffer and self-refreshes without GPU involvement.

> ⚠️ **Must be set to `0`.** Leaving PSR enabled causes **severe display stuttering**. Keep this key explicitly set to `0` in every device section.

- **Type:** `REG_DWORD`

| Value | Meaning |
|-------|---------|
| `0` | PSR disabled ✅ |
| `1` | PSR enabled — causes stuttering ❌ |

| Driver | Value |
|--------|-------|
| Falcon / Adrenalin 25.2.1 | `0` |
| Bootcamp 24.10.1 | `0` |
| RID 25.3.1 | `0` |
| Apple macpro / r6.4 | `0` |

**Power:** PSR would normally save ~10–15% panel power at idle, but the stutter regression makes it unusable.
**Stability:** Enabling PSR causes large, reproducible frame stutters on affected hardware. Always disable explicitly — do not rely on the driver default.

---

## KMD_BackingStoreMgrEnabled

Controls the KMD Backing Store Manager — a WDDM 3.1 feature (Windows 11 22H2+) that maintains a committed system-memory buffer holding GPU allocation contents when evicted from VRAM. Both UMD and KMD can access this shared backing store, enabling more efficient memory residency tracking and paging under VRAM pressure.

- **Type:** `REG_DWORD`

| Value | Meaning |
|-------|---------|
| `0` | Backing Store Manager disabled |
| `1` | Backing Store Manager enabled |

| Driver | Value (global) |
|--------|----------------|
| Falcon / Adrenalin 25.2.1 | `1` |
| Bootcamp 24.10.1 | not set |
| RID 25.3.1 | `0` |
| Apple macpro / r6.4 | not set |

**Performance:** When enabled, reduces overhead when GPU allocations are paged in/out under VRAM pressure. 

> **Note:** Exact behavior is inferred from the WDDM 3.1 framework; this key is not publicly documented by AMD.

---

## KMD_EnableDisplayableSupport

Controls whether the KMD advertises support for WDDM 3.0 displayable allocations — surfaces that can be directly scanned out by the display controller without an intermediate composition step. When enabled, unlocks hardware flip queues and optimized flip models (independent flip, direct flip) for lower-latency presentation.

- **Type:** `REG_DWORD`

| Value | Meaning |
|-------|---------|
| `0` | Displayable allocation support disabled |
| `1` | Displayable allocation support enabled |

| Driver | Value (Navi14) |
|--------|---------------|
| Falcon / Adrenalin 25.2.1 | `0` |
| Bootcamp 24.10.1 | `0` |
| RID 25.3.1 | not set (lines present but commented out) |
| Apple macpro / r6.4 | `0` |

**Performance:** Enabling (`1`) would allow hardware flip queues and direct scan-out, potentially reducing presentation latency. All surveyed drivers opt out, likely due to insufficient driver-level validation of the feature on Navi14 rather than a hardware limitation — RDNA1 has the hardware capability.

> **Note:** Exact behavior is inferred from the WDDM 3.0 framework; this key is not publicly documented by AMD.
