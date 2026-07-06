@echo off
setlocal
chcp 65001 >nul 2>&1

:: Self-elevate if not running as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

echo.
echo  Project Falcon - Windows SDK / WDK Installer
echo  ______________________________________________
echo.

echo [1/2] Installing Windows SDK (includes signtool.exe)...
winget install Microsoft.WindowsSDK.10.0.28000 || goto :error
echo       Done.

echo [2/2] Installing Windows WDK (includes Inf2Cat.exe)...
winget install Microsoft.WindowsWDK.10.0.28000 || goto :error
echo       Done.

echo.
echo  Default install locations (version/arch subfolder may vary):
echo    Inf2Cat.exe  -^> C:\Program Files (x86)\Windows Kits\10\bin\10.0.28000.0\x64\Inf2Cat.exe
echo    signtool.exe -^> C:\Program Files (x86)\Windows Kits\10\bin\10.0.28000.0\x64\signtool.exe
echo.
echo  Installation complete.
pause
exit /b 0

:error
echo.
echo ERROR: Script failed (step above returned a non-zero exit code).
pause
exit /b 1
