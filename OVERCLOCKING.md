## Overclocking/undervolting

Even though AMD disabled tuning section for mobile cards in AMD Software (CCC), it actually is still possible to do that **even with new drivers**.

In MacbookPro 2019 Radeon Pro 5500M theoretically might run at 1450Mhz/850mV. The problem is due to power constraints/thermal throttling you most likely will never see this actually happens.  Undervolting gives several benefits:
- improve performance
- reduce power consumption and temperatures
- eliminate thermal & power throttling to some extent

### Finding stable values

To follow my method it is a good to know what are **stable** levels or MHz/mV for your card. For that, I'd recommend using RadeonID driver with old 22.40 kernel. Please follow this [guide](https://www.reddit.com/r/macgaming/comments/1c48skn/full_installation_guide_latest_2024_amd_2431/). Once you did that, you may find yourself stable settings in AMD Software. In my case my card runs well at **1400Mhz/800mV**, **1000Mhz/730mV** and **700MHz/700mV**. Later we will try to find that values in MPT.

### MorePowerTool tuning

Once you have installed newer drivers, you won't be able to tune your GPU in AMD Software. MorePowerTool will do the job.

![image](https://github.com/icywire/project-falcon/blob/79795a3cf0fe3446fbf585cb4bb7b0cf9c09470b/images/undervolting.jpg)
* Step 1 - select checkboxes
* Step 2 - set max GFX/SoC voltage — **GFX max voltage will determine max real GPU clock based on AVFS curve** 
* Step 3 - optionally, you may limit max GFX clock (min clocks won't make any difference)
* Step 4 - in case of my card, I had to lower Memory DPM 3 clock from 750 to 736 (with 750 it was unstable)
* Step 5 - here you define your curve

### Adjust AVFS (curve)

![curve](https://github.com/icywire/project-falcon/blob/808575958d3979160687ce8a6ecd9026f7612e40/images/curve.jpg)

GPU BIOS has function that determines GPU required voltage based on clock. When clock grows, required voltage grows as well. However in MPT we can define how fast this function grows by changing AVFS values. If you have Radeon 5500M, you probably may reuse values from screenshot (or treat that as starting point).

"Algorithm" how to find AVFS values is quite simple. Assuming you've found stable settings at 1400Mhz/800mV:
- set your max GFX voltage to 800mV
- adjust AVFS values to get 1400Mhz clock @ 800mV while playing some games
- you need to start with higher a/b/c values, and slowly decrease them — when a/b/c is decreased, you max clock will grow
- after changing AVFS curve, you may run ![restart64-gpu.exe](https://github.com/icywire/project-falcon/blob/808575958d3979160687ce8a6ecd9026f7612e40/tools/restart64-gpu.exe), so you can test new settings right away, without restarting Windows
- **if you decrease too much, you will have to revert/clear MPT settings in Safe Mode**
