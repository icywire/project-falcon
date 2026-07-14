@echo off
setlocal
chcp 65001 >nul 2>&1

:: Self-elevate if not running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

:Menu
cls
echo.
echo  Project Falcon - AMD Driver Installer
echo  ____________________________________
echo.
echo  Select driver to install:
echo.
echo    1  AMD 26.6.1 for Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series) (25.2.1 kernel)
echo    2  AMD 25.2.1 for Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series)
echo    3  AMD 25.2.1 for Radeon Pro 5600M (22.6.1 kernel)
echo    4  AMD 26.5.2 for Radeon Pro Polaris (400/500 series) and Vega
echo.
choice /c 1234Q /n /m "  Choose [1, 2, 3, 4] or Q to quit: "
if errorlevel 5 exit /b 0
if errorlevel 4 goto Select_26_5_2_PolarisVega
if errorlevel 3 goto Select_25_2_1_5600M
if errorlevel 2 goto Select_25_2_1_Navi
if errorlevel 1 goto Select_26_6_1_Navi

:Select_26_6_1_Navi
set "SRC=%~dp0falcon_drivers\AMD-26.6.1"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display2\WT6A_INF"
set "BASEFOLDER=B026079"
set "INFBASE=u0201163"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-6-1.html"
set "KERNELFILE=amdkmdag_32.0.12033.5029.sys.xz"
set "KERNELVER=32.0.21043.12001"
echo.
echo  Selected: AMD 26.6.1 for Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series) (25.2.1 kernel)
echo.
goto Install

:Select_25_2_1_Navi
set "SRC=%~dp0falcon_drivers\AMD-25.2.1"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF"
set "BASEFOLDER=B412641"
set "INFBASE=u0412654"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html"
set "KERNELFILE="
set "KERNELVER="
echo.
echo  Selected: AMD 25.2.1 for Radeon Pro RDNA1 (5000 series) and RDNA2 (6000 series)
echo.
goto Install

:Select_25_2_1_5600M
set "SRC=%~dp0falcon_drivers\AMD-25.2.1_5600M"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF"
set "BASEFOLDER=B412641"
set "INFBASE=u0412654"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html"
set "KERNELFILE=amdkmdag_30.0.21030.1003.sys.xz"
set "KERNELVER=32.0.12033.5029"
echo.
echo  Selected: AMD 25.2.1 for Radeon Pro 5600M (kernel 22.6.1 kernel)
echo.
goto Install

:Select_26_5_2_PolarisVega
set "SRC=%~dp0falcon_drivers\AMD-26.5.2_polaris_vega"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF"
set "BASEFOLDER=B025980"
set "INFBASE=u0201039"
set "RELNOTES=https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-26-5-2-POLARIS-VEGA.html"
set "KERNELFILE="
set "KERNELVER="
echo.
echo  Selected: AMD 26.5.2 for Radeon Pro Polaris (400/500 series) and Vega
echo.
goto Install

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
    goto :end
)

echo [1/3] Copying driver files...
more "%SRC%\%INFBASE%.inf" > "%DST%\%INFBASE%.inf" || goto :error
copy /y "%SRC%\%INFBASE%.cat" "%DST%\" >nul || goto :error
echo       Done.

echo [2/3] Installing certificate...
certutil -f -p "falcon" -importpfx My "%CERT%\Project Falcon.pfx" >nul 2>&1 || goto :error
certutil -f -addstore My              "%CERT%\Project Falcon.cer" >nul 2>&1 || goto :error
certutil -f -addstore Root            "%CERT%\Project Falcon.cer" >nul 2>&1 || goto :error
certutil -f -addstore TrustedPublisher "%CERT%\Project Falcon.cer" >nul 2>&1 || goto :error
echo       Done.

if defined KERNELFILE (
    echo [3/4] Extracting kernel...
    "%~dp0tools\xz.exe" -d -k -f "%~dp0falcon_drivers\kernels\%KERNELFILE%" -c > "%DST%\%BASEFOLDER%\amdkmdag.sys" || goto :error
    echo       Done.
    echo [4/4] Installing driver - this sometimes freezes, press Enter after a minute or so...
) else (
    echo [3/3] Installing driver - this sometimes freezes, press Enter after a minute or so...
)
start /b /w pnputil /add-driver "%DST%\%INFBASE%.inf" /install
echo       Done.

if defined KERNELVER (
    reg add "HKLM\SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000" /v DriverVersion /d "%KERNELVER%" /t REG_SZ /f >nul 2>&1
    echo [+]   Set DriverVersion to %KERNELVER%
)

:exit
pause
exit /b 0

:error
echo.
echo ERROR: Script failed (step above returned a non-zero exit code).
pause