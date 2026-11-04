# Project Falcon – Design

## Idea

Up-to-date AMD Windows drivers for the AMD GPUs in Macs (Boot Camp): Polaris/Vega, RDNA1/2 and the Radeon Pro 5600M.
Falcon doesn't ship AMD's binaries. The user downloads the official AMD package. Falcon adds a modified INF with the Mac
PCI IDs and a catalog signed with the Project Falcon certificate, plus an older kernel (`amdkmdag.sys`) where the new
one dropped support. `install-driver.cmd` puts all of this in place with one menu choice.

## Open questions

- **Root CA trust.** The cert's private key is public in this repo, and the cert is added to the Root and TrustedPublisher
  stores. That means anyone can sign code that every Falcon user's PC trusts. Should the installer remove it from Root
  after `pnputil` finishes? Would that break driver updates or reinstalls? This needs testing and the upstream dev's input.
- Upstream (icywire/project-falcon) has issues turned off. Changes go to upstream as PRs from the ztancrell fork.

## Decided

- 2026-11-04: Users' PCs get only the public `.cer`, never the `.pfx` private key. The private key is only needed for
  signing, which happens on the maintainer's machine.
- 2026-11-04: The installer stays a readable batch script; it won't be rewritten in Rust (or as any other compiled .exe).
  Run time is all `pnputil` and `xz`. An unsigned admin .exe would get blocked by SmartScreen and antivirus. Users
  should be able to read what they run as admin, and a script is easy for upstream to accept. If batch ever gets too
  limiting, the next step is PowerShell.
- 2026-11-04: Focus is user-friendliness: the installer detects the GPU and the extracted AMD package and recommends the
  menu option to pick.
