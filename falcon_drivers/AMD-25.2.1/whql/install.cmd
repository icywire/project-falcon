@echo off
:: Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo.
echo Installing WHQL Digital Signature Link...
echo.

pnputil /add-driver "%~dp0u0412654.inf" /install
pnputil /scan-devices

if %errorlevel% equ 0 (
    echo.
    echo Done.
) else (
    echo.
    echo Failed. Error code: %errorlevel%
)

echo.
pause
