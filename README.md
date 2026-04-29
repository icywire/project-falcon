![banner](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/images/banner.png?raw=true)

## About
The goal of this project is to fill the gap and provide AMD driver updates dedicated for Macs after [BootCampDrivers.com](https://www.bootcampdriver.com) died. **RDNA** cards are main focus, as AMD still release driver updates for them (even though RDNA3/RDNA4 is more important :disappointed:).

Wonder why "Falcon"?  
This name comes from BIOS dump ([see screenshot](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/images/bios_falcon.jpg)) of my Radeon Pro 5500M (MacbookPro 2019), and also from registry keys from Apple's drivers for AMD cards (namely `PP_EnableLoadFalconSmcFirmware` and `PP_Falcon_QuickTransition_Enable`).  
And it's cool, right? :sunglasses:

## Falcon Drivers

### AMD 25.2.1 / RDNA1 (most stable)

This driver is based on official [AMD 25.2.1](https://drivers.amd.com/drivers/amd-software-adrenalin-edition-25.2.1-win10-win11-feb2025-rdna.exe) driver — no binaries are modified.

#### Supported devices

* All RDNA1 (Navi10/Navi14) cards should work - Radeon Pro 5300/5500/5600/5700
* Possible to add support for RDNA2 cards (from MacPro)

#### Verified devices

* Radeon Pro 5500M 8GB / MacbookPro 2019

### AMD 26.3.1 + kernel from 25.2.1 (yet unreleased)

This driver is based on official AMD 26.3.1 driver, but use kernel from 25.2.1 (which is the last driver that works with Macbooks).  
TBA

## Installation
For now, drivers are not signed, and **must be installed with disabled drivers signature check** ([see guide](https://www.google.com/search?q=disable+driver+signature+enforcement+windows)). 

1. Uninstall old GPU driver
2. Download official base driver (links above)
3. Try to install it. Once it fails just close the installer window. Extracted driver will remain on C:\ drive
4. Download Falcon driver
5. Copy Falcon .inf file to C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF
6. Install driver manually from Device Manager by selecting folder listed in earlier point (pick bottom option twice, and then click on "From disk")
7. Just continue when system alert will pop up

## Overclocking/undervolting mobile cards
TL;DR — overclocking/undervolting for AMD mobile cards **can be unlocked!**  
TL;DR2 — and yes, you don't have to use very old kernel 22.40 from AMD 23.5.2 drivers! <sup>(1)</sup>

In Macbooks **power and thermal throttling** are common issues. Fortunately, with undervolting, you may reduce power consumption to avoid throttling and improve performance.

<sup>(1)</sup> This is the method known from RadeonID drivers, [see guide](https://www.reddit.com/r/macgaming/comments/1c48skn/full_installation_guide_latest_2024_amd_2431).

TBA

## Tools

[MorePowerTool_1.2.2](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/tools/MorePowerTool_1.2.2.exe) - needed for overclocking/undervolting  
[restart64-gpu](https://github.com/icywire/project-falcon/blob/6919eb6aa78e0e8c7027f12dd9600b844e705038/tools/restart64-gpu.exe) - simple tool for hot-reloading AMD cards after usign MPT or changing registry

## Guides

How to unlock Wattman settings using RadeonID with old 22.40 kernel - https://www.reddit.com/r/macgaming/comments/1c48skn/full_installation_guide_latest_2024_amd_2431
