---
name: sign-driver
description: >
  Signs a Windows kernel driver by generating a .cat catalog file from a .inf file
  using Inf2Cat, then signing it with a PFX certificate using SignTool.
  Use this skill whenever the user wants to sign a driver, generate a .cat file from
  a .inf, sign a catalog file, or work with Windows driver signing. Also trigger for
  requests like "sign my driver", "create cat file", "sign inf", "driver certificate",
  or any mention of Inf2Cat or SignTool in a driver context. Default certificate is
  "Project Falcon.pfx" with password "falcon" unless the user specifies otherwise.
compatibility: "Windows only. Requires Inf2Cat.exe and signtool.exe (from Windows Driver Kit / Windows SDK). Runs via PowerShell."
---

# Driver Signing Skill

This skill generates a `.cat` catalog file from a `.inf` driver file using **Inf2Cat**, then
signs the `.cat` with a PFX certificate using **SignTool**.

## Inputs

Gather these before starting:
- **`.inf` file path** — required; the driver's INF file
- **PFX certificate path** — default: `"Project Falcon.pfx"` in the current directory
- **PFX password** — default: `falcon`
- **Timestamp server** — default: `http://timestamp.digicert.com`

If the user doesn't specify the certificate or password, use the defaults silently.

## Step 1 — Run the helper script

A bundled PowerShell script handles the entire workflow. Invoke it from the directory
containing the `.inf` file (or pass full paths). The script is at `scripts/sign_driver.ps1`
relative to this SKILL.md.

```powershell
& "<skill-dir>\scripts\sign_driver.ps1" `
    -InfPath "path\to\driver.inf" `
    -PfxPath "Project Falcon.pfx" `
    -PfxPassword "falcon"
```

Replace `<skill-dir>` with the absolute path of this skill's directory.

**Read the script** (`scripts/sign_driver.ps1`) before running it so you know the exact
parameters and can adapt them to whatever the user specified.

## Step 2 — Interpret the output

The script prints status lines prefixed with `[OK]`, `[INFO]`, or `[ERROR]`.

- On success it prints the full path of the signed `.cat` file.
- On failure it explains which step failed and why.

Relay this output to the user in plain language. If a tool is missing, tell the user
the exact path that was searched and suggest installing the Windows Driver Kit (WDK).

## Edge cases

- **OS list for Inf2Cat**: Always uses `/os:10_X64`.
- **Multiple .inf files in one folder**: Inf2Cat processes the whole driver folder, so all
  `.inf` files in the same directory are included automatically.
- **Timestamp server unreachable**: The script retries once with `http://timestamp.sectigo.com`
  as a fallback. If both fail, signing still succeeds but without a timestamp — warn the user.
- **Already-signed .cat**: Inf2Cat will overwrite it; SignTool will add a second signature
  counter-signature (dual-signing). Mention this if the user seems unaware.
