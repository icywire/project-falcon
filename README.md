![banner](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/images/banner.png?raw=true)

## About
The goal of this project is to fill the gap and provide AMD driver updates dedicated for Macs after [BootCampDrivers.com](https://www.bootcampdriver.com) died.  
**RDNA** cards are main focus, might be someday I'll add Polaris/Vega support as well.

## Falcon Drivers

### AMD 25.2.1 (most stable)

This driver is based on official [AMD 25.2.1](https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html) driver — no binaries are modified.  
All AMD Radeon 5xxx/6xxx cards (RDNA1/RDNA2) from Macs should work (except 5600M)

### AMD 26.5.1

(Work in progress)

### Installation
For now, drivers are not signed, and **must be installed with disabled drivers signature check** ([see guide](https://www.google.com/search?q=disable+driver+signature+enforcement+windows)). 

1. Uninstall old GPU driver
2. Download official base driver (links above)
3. Try to install it. Once it fails just close the installer window. Extracted driver will remain on C:\ drive
4. Download Falcon driver
5. Copy Falcon .inf file to C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF
6. Install driver manually from Device Manager by selecting folder listed in earlier point (pick bottom option twice, and then click on "From disk")
7. Just continue when system alert will pop up

## Overclocking/undervolting mobile cards

See [OVERCLOCKING.md](OVERCLOCKING.md)

## Other

### Tools

[MorePowerTool_1.2.2](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/tools/MorePowerTool_1.2.2.exe) - needed for overclocking/undervolting  
[restart64-gpu](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/tools/restart64-gpu.exe) - simple tool for hot-reloading AMD cards after usign MPT or changing registry  
[MPO-GPU-FIX](https://github.com/RedDot-3ND7355/MPO-GPU-FIX) - small tool that might help fix stutters and improve FPS

### Guides

VRM cooling mod for Macbooks - https://www.reddit.com/r/macbookpro/comments/gs6bal/2019_mbp_16_vrm_cooling_mod  
How to unlock Wattman settings using RadeonID with old 22.40 kernel - https://www.reddit.com/r/macgaming/comments/1c48skn/full_installation_guide_latest_2024_amd_2431

### Why "Falcon" ?
This names comes from BIOS dump of Radeon Pro 5500M, and also exists in driver registry (`PP_EnableLoadFalconSmcFirmware` and `PP_Falcon_QuickTransition_Enable` keys).
And it's cool, right? :sunglasses:
