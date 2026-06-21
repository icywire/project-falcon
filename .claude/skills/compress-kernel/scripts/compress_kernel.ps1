[CmdletBinding()]
param(
    [string]$KernelsDir = "falcon_drivers\kernels",
    [string]$ToolsDir   = "tools"
)

$ErrorActionPreference = "Stop"

$sysFile = Join-Path $KernelsDir "amdkmdag.sys"
$xzExe   = Join-Path $ToolsDir "xz.exe"

if (-not (Test-Path $sysFile)) {
    Write-Host "[ERROR] amdkmdag.sys not found at: $sysFile"
    exit 1
}
if (-not (Test-Path $xzExe)) {
    Write-Host "[ERROR] xz.exe not found at: $xzExe"
    exit 1
}

$version = (Get-Item $sysFile).VersionInfo.FileVersion
if (-not $version) {
    Write-Host "[ERROR] Could not read file version from $sysFile"
    exit 1
}

$outName = "amdkmdag_$version.sys.xz"
$outPath = Join-Path $KernelsDir $outName

Write-Host "[INFO] Source:  $sysFile"
Write-Host "[INFO] Version: $version"
Write-Host "[INFO] Output:  $outPath"

if (Test-Path $outPath) {
    Remove-Item $outPath
}

Write-Host "[INFO] Compressing with xz LZMA2 -9e (this takes ~20 seconds)..."
$tempXz = "$sysFile.xz"
if (Test-Path $tempXz) { Remove-Item $tempXz }

& $xzExe -k -9 -e -T 0 $sysFile

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] xz failed with exit code $LASTEXITCODE"
    exit 1
}

Move-Item $tempXz $outPath -Force

$origMB = [math]::Round((Get-Item $sysFile).Length / 1MB, 2)
$compMB  = [math]::Round((Get-Item $outPath).Length / 1MB, 2)
$ratio   = [math]::Round((1 - (Get-Item $outPath).Length / (Get-Item $sysFile).Length) * 100, 1)

Write-Host "[OK] Compressed: $outName"
Write-Host "[OK] $origMB MB -> $compMB MB ($ratio% reduction)"
