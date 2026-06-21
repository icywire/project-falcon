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
echo    1  AMD 25.2.1 for Navi  (RDNA1/RDNA2, series 5xxx/6xxx)
echo    2  AMD 25.2.1 for Radeon Pro 5600M  (22.6.1 kernel)
echo.
choice /c 12Q /n /m "  Choose [1, 2] or Q to quit: "
if errorlevel 3 exit /b 0
if errorlevel 2 goto Select5600M
if errorlevel 1 goto SelectNavi

:SelectNavi
set "SRC=%~dp0falcon_drivers\AMD-25.2.1"
set "IS_5600M=0"
echo.
echo  Selected: AMD 25.2.1 for Navi
echo.
goto Install

:Select5600M
set "SRC=%~dp0falcon_drivers\AMD-25.2.1_5600M"
set "IS_5600M=1"
echo.
echo  Selected: AMD 25.2.1 for Radeon Pro 5600M
echo.
goto Install

:Install
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF"
set "CERT=%~dp0certificate"

:: Verify base driver is present
if not exist "%DST%\B412641" (
    echo ERROR: Base driver not found.
    echo.
    echo   AMD Radeon Software 25.2.1 must be downloaded and extracted first.
    echo   Download it from:
    echo   https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-25-2-1.html
    echo.
    goto :end
)

echo [1/3] Copying driver files...
more "%SRC%\u0412654.inf" > "%DST%\u0412654.inf" || goto :error
copy /y "%SRC%\u0412654.cat" "%DST%\" >nul || goto :error
echo       Done.

echo [2/3] Installing certificate...
certutil -f -p "falcon" -importpfx My "%CERT%\Project Falcon.pfx" >nul 2>&1 || goto :error
certutil -f -addstore My              "%CERT%\Project Falcon.cer" >nul 2>&1 || goto :error
certutil -f -addstore Root            "%CERT%\Project Falcon.cer" >nul 2>&1 || goto :error
certutil -f -addstore TrustedPublisher "%CERT%\Project Falcon.cer" >nul 2>&1 || goto :error
echo       Done.

if "%IS_5600M%"=="1" (
    echo [3/4] Extracting kernel...
    "%~dp0tools\xz.exe" -d -k -f "%~dp0falcon_drivers\kernels\amdkmdag_30.0.21030.1003.sys.xz" -c > "C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF\B412641\amdkmdag.sys" || goto :error
    echo       Done.
    echo [4/4] Installing driver - this sometimes freezes, press Enter after a minute or so...
) else (
    echo [3/3] Installing driver - this sometimes freezes, press Enter after a minute or so...
)
start /b /w pnputil /add-driver "%DST%\u0412654.inf" /install
echo       Done.

if "%IS_5600M%"=="1" (
    reg add "HKLM\SYSTEM\ControlSet001\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}\0000" /v DriverVersion /d "32.0.12033.5029" /t REG_SZ /f >nul 2>&1
    echo [+]   Set DriverVersion to 32.0.12033.5029
)

:exit
pause
exit /b 0

:error
echo.
echo ERROR: Script failed (step above returned a non-zero exit code).
pause