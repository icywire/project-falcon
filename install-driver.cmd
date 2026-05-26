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
set "DSTPARENT=C:\AMD\AMD-Software-Installer\Packages\Drivers\Display"

:: Verify base driver is present

echo [1/4] Copying driver files...
copy /y "%SRC%\u0412654.inf" "%DST%\" >nul || goto :error
copy /y "%SRC%\u0412654.cat" "%DST%\" >nul || goto :error
echo       Done.

echo [2/4] Relocating component directories...
if exist "%DSTPARENT%\amdxe" (
    echo       Already relocated - skipping.
) else (
    move "%DST%\amdxe"         "%DSTPARENT%\amdxe"         || goto :error
    move "%DST%\amdwin"        "%DSTPARENT%\amdwin"        || goto :error
    move "%DST%\amdpcibridge"  "%DSTPARENT%\amdpcibridge"  || goto :error
    move "%DST%\amdocl"        "%DSTPARENT%\amdocl"        || goto :error
    move "%DST%\amdfendr"      "%DSTPARENT%\amdfendr"      || goto :error
    move "%DST%\amdfdans"      "%DSTPARENT%\amdfdans"      || goto :error
    echo       Done.
)

echo [3/4] Installing driver - please be patient, this may take a moment...
pnputil /add-driver "%DST%\u0412654.inf" /install || goto :error
pnputil /scan-devices
echo       Done.

echo [4/4] Installing WHQL Digital Signature Link...
pnputil /add-driver "%SRC%\whql\u0412654_whql.inf" /install || goto :error
pnputil /scan-devices
::pnputil /add-driver "%SRC%\whql2\u0380612_msft.inf" /install || goto :error
::pnputil /add-driver "%SRC%\whql3\u0410212_msft.inf" /install || goto :error
::pnputil /scan-devices
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
