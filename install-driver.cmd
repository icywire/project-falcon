@echo off
setlocal

:: Self-elevate if not running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

echo =====================================================
echo  Project Falcon - AMD Driver Installer
echo =====================================================
echo.
echo  Supported devices:
echo    All Macs with AMD Radeon RDNA1 / RDNA2 GPU (series 5xxx/6xxx)
echo.
echo  NOT (yet) supported:
echo    AMD Radeon Pro 5600M
echo    Polaris/Vega series
echo =====================================================
echo.

set "SRC=%~dp0falcon_drivers\AMD-25.2.1"
set "DST=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display\WT6A_INF"
set "CERT=%~dp0certificate"

:: Verify base driver is present
if not exist "%DST%\u0412654.inf" (
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

echo [3/3] Installing driver - please be patient, this will take a while...
pnputil /add-driver "%DST%\u0412654.inf" /install || goto :error
echo       Done.

echo.
echo Done.
goto :end

:error
echo.
echo ERROR: Script failed (step above returned a non-zero exit code).

:end
echo.
pause
