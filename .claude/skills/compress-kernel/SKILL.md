---
name: compress-kernel
description: >
  Compresses amdkmdag.sys from the falcon_drivers/kernels directory using xz LZMA2
  at maximum compression. The output file is named with the file version read from
  the binary (e.g. amdkmdag_30.0.21030.1003.sys.xz) and placed alongside the source.
  Use this skill whenever the user wants to compress the kernel driver, compress amdkmdag.sys,
  or mentions "compress kernel", "compress driver", or "xz the sys file".
compatibility: "Windows only. Requires tools/xz.exe and tools/liblzma-5.dll (already present in project)."
---

# Compress Kernel Skill

Compresses `falcon_drivers\kernels\amdkmdag.sys` with **xz LZMA2 -9e** (maximum compression).
Output filename is derived from the file's embedded version string.

## Inputs

No required inputs. Optional overrides:
- **KernelsDir** — default: `falcon_drivers\kernels` (relative to project root)
- **ToolsDir** — default: `tools` (relative to project root)

## Step 1 — Run the helper script

Run from the project root directory:

```powershell
& "<skill-dir>\scripts\compress_kernel.ps1" `
    -KernelsDir "falcon_drivers\kernels" `
    -ToolsDir "tools"
```

Replace `<skill-dir>` with the absolute path of this skill's directory.

**Read the script** (`scripts/compress_kernel.ps1`) before running it.

## Step 2 — Interpret the output

The script prints lines prefixed with `[INFO]`, `[OK]`, or `[ERROR]`.

- On success it prints the output filename and compression stats (original MB → compressed MB, % reduction).
- On failure it explains what was missing or what failed.

Relay the compression result to the user: output filename, sizes, and ratio.

## Notes

- Compression takes roughly 15–25 seconds (LZMA2 at max settings).
- Output is placed in the same `kernels` directory as the source.
- If an output file with the same name already exists it is overwritten silently.
- `tools\liblzma-5.dll` must be present alongside `tools\xz.exe` — both are checked in to the repo.
