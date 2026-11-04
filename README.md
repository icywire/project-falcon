![banner](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/images/banner.png?raw=true)

## About

The goal of this project is to fill the gap and provide AMD driver updates dedicated for Macs!

Want to learn more and stay in touch? [<img src="images/discord.png" width="24" valign="middle"> Join our discord!](https://discord.gg/JrUCrVhFqz)

## Current state

All Polaris/Vega/Navi AMD GPUs from Macbooks/iMacs/MacPro are supported. This includes:

✅ Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series)  
✅ Radeon Pro 5600M  
✅ Radeon Pro Polaris (400/500 series) and Vega  

## Driver versions

❗Read [Installation](#installation) first before you ask what to download❗

#### For Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series):
1. [AMD 26.9.2](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-9-2.html) (original kernel)
2. [AMD 26.6.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-6-1.html) (25.2.1 kernel)
3. [AMD 25.2.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html) (original kernel)

#### For Radeon Pro 5600M  
1. [AMD 26.6.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-6-1.html) (22.6.1 kernel)
2. [AMD 25.2.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html) (22.6.1 kernel)

#### For Radeon Pro Polaris (400/500 series) and Vega  
1. [AMD 26.5.2](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-5-2-POLARIS-VEGA.html) (original kernel)

## Installation

1. Download this repository - click green "Code" button from top of this GitHub page, then "Download ZIP", and unzip it
2. Download the official AMD driver matching your GPU (see supported [Driver versions](#driver-versions) section above). Not sure which one? Run `install-driver.cmd` (step 5) first: it detects your GPU, recommends an option and prints its AMD download link, then press Q to quit
3. Uninstall your existing GPU driver using DDU or RAPR (see [Tools](#tools) section below)
4. Run official AMD driver installer you got in step 2. **Installation will fail** — that is expected — just close its window
5. Now from extracted Falcon package, right-click `install-driver.cmd` and "Run as admin". **In case of any issues**, start it manually:
   * click Option+R (or Win+R)
   * type `cmd` and hit Ctrl+Shift+Enter (to run as admin)
   * type `cd C:\Users\<your-username>\Downloads\project-falcon-master` and hit Enter
   * type `.\install-driver.cmd` and hit Enter
6. Script shows the GPU it detected and a menu. Each option says `[fits your GPU]` if its driver supports your GPU, and `[package ready]` if the AMD driver from step 4 is extracted (`[download needed]` if not). Pick the option on the `Recommended:` line. If you pick an option that doesn't fit your GPU, the script warns and asks before it continues
7. Patiently wait, sometime script hangs, just hit Enter after minute or so. If a step fails, the script prints an `ERROR` line and stops instead of saying `Done.`
8. At the end the script asks `Install AMD Software now? [Y/N]` - press Y to start the AMD Software installer (`ccc2_install.exe`). If you press N, it prints the `ccc2_install.exe` path to run later (it is in `C:\AMD\AMD-Software-Installer\Packages\Drivers\Display2\WT6A_INF\B...` or `...\Display\WT6A_INF\B...`, depending on the driver version)

## Overclocking/undervolting mobile cards

See [OVERCLOCKING.md](OVERCLOCKING.md)

## Other

### Tools

#### Uninstalling drivers

[Display Driver Uninstaller (DDU)](https://www.guru3d.com/download/display-driver-uninstaller-download/) - recommended tool for cleanly uninstalling GPU drivers  
[DriverStoreExplorer (RAPR)](https://github.com/lostindark/DriverStoreExplorer) - browse and remove driver packages from the Windows Driver Store

#### Tuning

[MPO-GPU-FIX](https://github.com/RedDot-3ND7355/MPO-GPU-FIX) - small tool that might help fix stutters and improve FPS  

#### Overclocking tools

[MorePowerTool_1.2.2 (MPT)](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/tools/MorePowerTool_1.2.2.exe) - needed for overclocking/undervolting to change clocks/voltages/limits 
[restart64-gpu](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/tools/restart64-gpu.exe) - simple tool for hot-reloading AMD cards after usign MPT or changing registry  

### Guides

VRM cooling mod for Macbooks - https://www.reddit.com/r/macbookpro/comments/gs6bal/2019_mbp_16_vrm_cooling_mod  
How to unlock Wattman settings using RadeonID with old 22.40 kernel - https://www.reddit.com/r/macgaming/comments/1c48skn/full_installation_guide_latest_2024_amd_2431

### Why "Falcon" ?
This names comes from BIOS dump of Radeon Pro 5500M, and also exists in driver registry (`PP_EnableLoadFalconSmcFirmware` and `PP_Falcon_QuickTransition_Enable` keys).
And it's cool, right? :sunglasses:
