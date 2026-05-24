@echo off
setlocal

:: ============================================================
::  Project Falcon - Certificate Installer
::  Installs Root CA and Intermediate CA into Windows stores
:: ============================================================

:: Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] This script must be run as Administrator.
    echo         Right-click and select "Run as administrator".
    pause
    exit /b 1
)

set CERT_DIR=%~dp0

echo.
echo  Project Falcon - Certificate Installer
echo  =======================================
echo.

:: Install Root CA into Trusted Root Certification Authorities
echo [1/2] Installing Root CA...
certutil -addstore -f "Root" "%CERT_DIR%root-ca.cer"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Root CA.
    goto :fail
)
echo [OK] Root CA installed successfully.
echo.

:: Install Intermediate CA into Intermediate Certification Authorities
echo [2/2] Installing Intermediate CA...
certutil -addstore -f "CA" "%CERT_DIR%intermediate.cer"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Intermediate CA.
    goto :fail
)
echo [OK] Intermediate CA installed successfully.
echo.

echo  =======================================
echo  Installation complete.
echo  You can now sign and install drivers.
echo  =======================================
echo.
pause
exit /b 0

:fail
echo.
echo  Installation failed. Check errors above.
echo.
pause
exit /b 1
