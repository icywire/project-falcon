@echo off
setlocal
chcp 65001 >nul 2>&1

:: Self-elevate if not running as administrator.
:: The script path goes to PowerShell through an env var, so spaces or quotes in it (O'Brien) can't break the command.
net session >nul 2>&1
if %errorlevel% neq 0 (
    set "FALCON_SELF=%~f0"
    powershell -NoProfile -Command "$q = [char]34; Start-Process -FilePath cmd.exe -ArgumentList ('/c ' + $q + $q + $env:FALCON_SELF + $q + $q) -Verb RunAs"
    exit /b
)

:: Detect the AMD GPU by its PCI vendor ID (VEN_1002), not by name: after DDU, Windows calls it
:: "Microsoft Basic Display Adapter". GPUDEV = 4-digit device ID (e.g. 7340), GPUNAME = Windows' name.
set "GPUDEV="
set "GPUNAME="
for /f "tokens=1*" %%A in ('powershell -NoProfile -Command "foreach ($g in Get-CimInstance Win32_VideoController) { if ($g.PNPDeviceID -like 'PCI\VEN_1002&DEV_*') { $g.PNPDeviceID.Substring(17, 4) + ' ' + $g.Name; break } }"') do (
    set "GPUDEV=%%A"
    set "GPUNAME=%%B"
)

:Menu
cls
echo.
echo  Project Falcon - AMD Driver Installer
echo  ____________________________________
echo.
if defined GPUDEV echo  Detected GPU: %GPUNAME% (DEV_%GPUDEV%)
if not defined GPUDEV echo  WARNING: No AMD GPU found. Pick the option that matches your Mac's GPU yourself.
echo.
echo  Select driver to install:
echo.
set "REC="
set "FIRSTFIT="
for %%N in (1 2 3 4 5 6) do call :MenuLine %%N
echo.
if defined GPUDEV if not defined FIRSTFIT echo  WARNING: No option lists your GPU (DEV_%GPUDEV%).
if defined REC echo  Recommended: %REC%
if defined REC goto Choose
if not defined FIRSTFIT goto Choose
call :Pick %FIRSTFIT%
echo  Recommended: %FIRSTFIT% - but its AMD package is not extracted yet:
echo    1. Download the AMD driver from:
echo       %RELNOTES%
echo    2. Run the AMD installer (it will fail - that is expected), close it,
echo       then run this script again.

:Choose
echo.
choice /c 123456Q /n /m "  Choose [1, 2, 3, 4, 5, 6] or Q to quit: "
if errorlevel 7 exit /b 0
set "OPT=%errorlevel%"
call :Pick %OPT%
call :Status
echo.
echo  Selected: %LABEL%
echo.
if not defined GPUDEV goto Install
if defined FIT goto Install
echo  WARNING: Option %OPT% does not fit your GPU (DEV_%GPUDEV%).
if defined REC echo           Recommended for your GPU: option %REC%.
choice /c YN /n /m "  Continue anyway? [Y/N]: "
if errorlevel 2 goto Menu
goto Install

:: Print option %1 with its status, and track the recommendation (menu order = preference order).
:MenuLine
call :Pick %1
call :Status
echo    %1  %LABEL%
echo          %STATUS%
if defined FIT if defined READY if not defined REC set "REC=%1"
if defined FIT if not defined FIRSTFIT set "FIRSTFIT=%1"
exit /b

:: FIT = this option's INF lists the detected GPU. READY = the AMD package is extracted.
:Status
set "FIT="
set "READY="
if defined GPUDEV findstr /i /l /c:"VEN_1002&DEV_%GPUDEV%" "%SRC%\%INFBASE%.inf" >nul 2>&1 && set "FIT=1"
if defined NOTFORDEV if /i "%GPUDEV%"=="%NOTFORDEV%" set "FIT="
if exist "%DST%\%BASEFOLDER%" set "READY=1"
set "STATUS=[download needed]"
if defined READY set "STATUS=[package ready]"
if defined FIT set "STATUS=[fits your GPU] %STATUS%"
exit /b

:: Load the settings of menu option %1. Optional values are cleared first so none leak from another option.
:: NOTFORDEV: a GPU this option's INF lists but which needs another option. 7360 = Radeon Pro 5600M
:: (Navi12 + HBM2): the RDNA INFs list it, but it needs the 22.6.1 kernel of options 4 and 5.
:Pick
set "KERNELFILE="
set "KERNELVER="
set "DATFILE="
set "NOTFORDEV="
goto Opt%1

:Opt2
set "LABEL=AMD 26.6.1 for Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series) (25.2.1 kernel)"
set "SRC=%~dp0falcon_drivers\AMD-26.6.1"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display2\WT6A_INF"
set "BASEFOLDER=B026079"
set "INFBASE=u0201163"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-6-1.html"
set "KERNELFILE=amdkmdag_32.0.12033.5029.sys.xz"
set "KERNELVER=32.0.21043.12001"
set "NOTFORDEV=7360"
exit /b

:Opt3
set "LABEL=AMD 25.2.1 for Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series)"
set "SRC=%~dp0falcon_drivers\AMD-25.2.1"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF"
set "BASEFOLDER=B412641"
set "INFBASE=u0412654"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html"
set "KERNELFILE="
set "KERNELVER="
set "NOTFORDEV=7360"
exit /b

:Opt4
set "LABEL=AMD 26.6.1 for Radeon Pro 5600M (22.6.1 kernel)"
set "SRC=%~dp0falcon_drivers\AMD-26.6.1_5600M"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display2\WT6A_INF"
set "BASEFOLDER=B026079"
set "INFBASE=u0201163"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-6-1.html"
set "KERNELFILE=amdkmdag_30.0.21030.1003.sys.xz"
set "KERNELVER=32.0.21043.12001"
exit /b

:Opt5
set "LABEL=AMD 25.2.1 for Radeon Pro 5600M (22.6.1 kernel)"
set "SRC=%~dp0falcon_drivers\AMD-25.2.1_5600M"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF"
set "BASEFOLDER=B412641"
set "INFBASE=u0412654"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html"
set "KERNELFILE=amdkmdag_30.0.21030.1003.sys.xz"
set "KERNELVER=32.0.12033.5029"
exit /b

:Opt6
set "LABEL=AMD 26.5.2 for Radeon Pro Polaris (400/500 series) and Vega"
set "SRC=%~dp0falcon_drivers\AMD-26.5.2_polaris_vega"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF"
set "BASEFOLDER=B025980"
set "INFBASE=u0201039"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-5-2-POLARIS-VEGA.html"
set "KERNELFILE="
set "KERNELVER="
exit /b

:Opt1
set "LABEL=AMD 26.9.2 for Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series)"
set "SRC=%~dp0falcon_drivers\AMD-26.9.2"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display2\WT6A_INF"
set "BASEFOLDER=B026531"
set "INFBASE=u0204589"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-9-2.html"
set "KERNELFILE="
set "KERNELVER="
set "DATFILE=amdgcf_26.9.2.dat.xz"
set "NOTFORDEV=7360"
exit /b

:Install
set "CERT=%~dp0certificate"

:: Verify base driver is present
if not exist "%DST%\%BASEFOLDER%" (
    echo ERROR: Base driver not found.
    echo.
    echo   AMD Radeon Software must be downloaded and extracted first.
    echo   Download it from:
    echo   %RELNOTES%
    echo.
    goto :fail
)

echo [1/4] Copying driver files...
more "%SRC%\%INFBASE%.inf" > "%DST%\%INFBASE%.inf" || goto :error
copy /y "%SRC%\%INFBASE%.cat" "%DST%\" >nul || goto :error
echo       Done.

echo [2/4] Installing certificate...
certutil -f -addstore Root            "%CERT%\Project Falcon.cer" >nul 2>&1 || goto :error
certutil -f -addstore TrustedPublisher "%CERT%\Project Falcon.cer" >nul 2>&1 || goto :error
echo       Done.

echo [3/4] Extracting files...
if defined KERNELFILE (
    "%~dp0tools\xz.exe" -d -k -f "%~dp0falcon_drivers\kernels\%KERNELFILE%" -c > "%DST%\%BASEFOLDER%\amdkmdag.sys" || goto :error
)
if defined DATFILE (
    "%~dp0tools\xz.exe" -d -k -f "%~dp0falcon_drivers\kernels\%DATFILE%" -c > "%DST%\%BASEFOLDER%\amdgcf.dat" || goto :error
)

echo [4/4] Installing driver - this sometimes freezes, press Enter after a minute or so...
start /b /w pnputil /add-driver "%DST%\%INFBASE%.inf" /install
set "RC=%errorlevel%"
if not "%RC%"=="0" if not "%RC%"=="3010" if not "%RC%"=="259" (
    echo.
    echo ERROR: pnputil failed with exit code %RC%.
    goto :fail
)
echo       Done.
if "%RC%"=="3010" echo       Reboot required to finish the install.
if "%RC%"=="259" echo WARNING: Driver added, but no device was updated - already installed, or GPU ID not in this INF?

if defined KERNELVER (
    set "FOUND="
    for /f "delims=" %%K in ('reg query "HKLM\SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}" /s /d /e /f "Advanced Micro Devices, Inc." 2^>nul ^| findstr /r /c:"^HKEY.*\\[0-9][0-9][0-9][0-9]$"') do (
        set "FOUND=1"
        reg add "%%K" /v DriverVersion /d "%KERNELVER%" /t REG_SZ /f >nul 2>&1 && echo [+]   Set DriverVersion to %KERNELVER% in %%K || echo WARNING: Could not set DriverVersion in %%K
    )
    if not defined FOUND echo WARNING: No AMD display adapter key found, DriverVersion was not set.
)

echo.
if not exist "%DST%\%BASEFOLDER%\ccc2_install.exe" (
    echo  To install AMD Software, look for ccc2_install.exe in:
    echo    %DST%
    pause
    exit /b 0
)
choice /c YN /n /m "  Install AMD Software now? [Y/N]: "
if errorlevel 2 (
    echo  To install AMD Software later, run:
    echo    %DST%\%BASEFOLDER%\ccc2_install.exe
    pause
    exit /b 0
)
echo  Starting AMD Software installer...
start "" "%DST%\%BASEFOLDER%\ccc2_install.exe"
exit /b 0

:error
echo.
echo ERROR: Script failed (step above returned a non-zero exit code).
:fail
pause
exit /b 1
