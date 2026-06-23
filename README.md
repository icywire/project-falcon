![banner](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/images/banner.png?raw=true)

## About

The goal of this project is to fill the gap and provide AMD driver updates dedicated for Macs after [BootCampDrivers.com](https://www.bootcampdriver.com) died.  
**RDNA** cards are main focus, might be someday I'll add Polaris/Vega support as well.

## Current state

✅ RDNA1/RDNA2 (all Radeon 5xxx/6xxx cards from iMacs/MacPro/Macbooks) - supported  
✅ 5600M - support added, needs someone who can verify  
🚧 AMD 26.6.1 - in progress  
⏳ WHQL workaround - on hold  
⏳ Polaris/Vega - on TODO list  

## Community/issues/help

[Join discord](https://discord.gg/JrUCrVhFqz)

[Report issues](https://github.com/icywire/project-falcon/issues)

[Start discussion](https://github.com/icywire/project-falcon/discussions)

## Drivers

### AMD 25.2.1
Stable - based on official [AMD 25.2.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html) driver (no binaries modified)  
Tested hardware: 5500M, 5300M, W6900X  
Tested software: Forza Horizon 6, Witcher 3, Assassin's Creed Origins, DaVinci Resolve

### AMD 26.6.1
Work in progress...

## Installation

1. Uninstall the existing GPU driver manually or using DDU or RAPR (see Tools section below)
2. Download the official [AMD 25.2.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html) base driver and run the installer. Once it fails, close the window — the extracted files will remain on `C:\`
3. Download or clone this repository
4. Run `install-driver.cmd` — it will patch base driver and install it (sometime it hangs, just hit Enter after minute or so)
5. Done
6. If you wish, you may install AMD Software manually from `C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF\B412641\ccc2_install.exe`

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
