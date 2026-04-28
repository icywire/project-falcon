# Project Falcon
This project aims to makes your Mac great again, by deliverying driver updates to AMD Radeon GPUs.

## Supported devices
Theoretically it will work with any Macs with - Radeon 5300/5500/5600/5700 (M and XT).

Verified devices:
Radeon 5500M 8GB / MacbookPro 2019

## Install process
For now drivers are not signed. That's why to install them, you need to disable drivers signature enforcement.

1. Download repo as .zip and extract
2. Run Windows with driver signature verification turned off
 - while holding Shift click Restart in system menu
 - Troubleshoot > Advanced options > Startup Settings > Restart
 - once system boots up - select "Disable driver signature enforcement"
3. Remove old driver
4. Install new driver from Device Manager
 - RMB > Update driver
 - pick bottom option
 - pick bottom option again
 - click "From disk" and point to driver directory

## Undervolting
TBA

## Tools
