![banner](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/images/banner.png?raw=true)

## About

The goal of this project is to fill the gap and provide AMD driver updates dedicated for Macs!

Want to learn more and stay in touch? [<img src="images/discord.png" width="24" valign="middle"> Join our discord!](https://discord.gg/JrUCrVhFqz)

## Current state

All Polaris/Vega/Navi AMD GPUs from Macbooks/iMacs/MacPro are supported. This includes:

✅ Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series)  
✅ Radeon Pro 5600M  
✅ Radeon Pro Polaris (400/500 series) and Vega  

## Drivers

### For Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series) (except Radeon Pro 5600M)
Base driver - [AMD 26.6.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-6-1.html) (25.2.1 kernel)

Older base driver - [AMD 25.2.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html) - this should be most stable one

### For Radeon Pro 5600M exclusively
Base driver - [AMD 25.2.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html) (22.6.1 kernel)

### For Radeon Pro Polaris (400/500 series) and Vega
Base driver - [AMD 26.5.2](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-5-2-POLARIS-VEGA.html)

## Installation

1. Uninstall the existing GPU driver manually or using DDU or RAPR (see Tools section below)
2. Download base driver (see above) and run the installer. Once it fails, close the window — the extracted files will remain on `C:\`
3. Download or clone this repository - click green button "Code", then "Download ZIP"
4. Run `install-driver.cmd` as admin — it will patch base driver and install it (sometime it hangs, just hit Enter after minute or so)
5. Done
6. If you wish, you may install AMD Software manually from `C:\AMD\AMD-Software-Installer\Packages\Drivers\Display2\WT6A_INF\B412641\ccc2_install.exe` (use `Display2` if `Display` doesn't work)

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
