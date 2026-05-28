<#
.SYNOPSIS
    Generates a .cat file from a .inf driver file and signs it with a PFX certificate.
.PARAMETER InfPath
    Path to the .inf file.
.PARAMETER PfxPath
    Path to the .pfx certificate file. Defaults to "Project Falcon.pfx" in the current directory.
.PARAMETER PfxPassword
    Password for the PFX file. Defaults to "falcon".
.PARAMETER TimestampUrl
    RFC 3161 timestamp server URL. Defaults to DigiCert's server.
#>
param(
    [Parameter(Mandatory)]
    [string]$InfPath,

    [string]$PfxPath = "Project Falcon.pfx",
    [string]$PfxPassword = "falcon",
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ── Helpers ──────────────────────────────────────────────────────────────────

function Find-Tool {
    param([string]$ExeName)

    # 1. Check PATH first
    $inPath = Get-Command $ExeName -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }

    # 2. Search Windows Kits directory
    $kitsRoot = "C:\Program Files (x86)\Windows Kits\10"
    if (Test-Path $kitsRoot) {
        $found = Get-ChildItem -Path $kitsRoot -Filter $ExeName -Recurse -ErrorAction SilentlyContinue |
                 Select-Object -First 1
        if ($found) { return $found.FullName }
    }

    return $null
}

function Write-Status {
    param([string]$Level, [string]$Message)
    Write-Host "[$Level] $Message"
}

# ── Resolve paths ─────────────────────────────────────────────────────────────

$InfPath  = Resolve-Path $InfPath  | Select-Object -ExpandProperty Path
$DriverDir = Split-Path $InfPath -Parent

if (-not [System.IO.Path]::IsPathRooted($PfxPath)) {
    # Resolve relative PFX path against current directory
    $PfxPath = Join-Path (Get-Location) $PfxPath
}

if (-not (Test-Path $InfPath)) {
    Write-Status "ERROR" "INF file not found: $InfPath"
    exit 1
}

if (-not (Test-Path $PfxPath)) {
    Write-Status "ERROR" "PFX certificate not found: $PfxPath"
    Write-Status "INFO"  "Expected at: $PfxPath"
    exit 1
}

# ── Find tools ────────────────────────────────────────────────────────────────

Write-Status "INFO" "Locating Inf2Cat..."
$inf2cat = Find-Tool "Inf2Cat.exe"
if (-not $inf2cat) {
    Write-Status "ERROR" "Inf2Cat.exe not found in PATH or under C:\Program Files (x86)\Windows Kits\10\"
    Write-Status "INFO"  "Install the Windows Driver Kit (WDK): https://learn.microsoft.com/windows-hardware/drivers/download-the-wdk"
    exit 1
}
Write-Status "OK" "Inf2Cat: $inf2cat"

Write-Status "INFO" "Locating SignTool..."
$signtool = Find-Tool "signtool.exe"
if (-not $signtool) {
    Write-Status "ERROR" "signtool.exe not found in PATH or under C:\Program Files (x86)\Windows Kits\10\"
    Write-Status "INFO"  "Install the Windows SDK or WDK."
    exit 1
}
Write-Status "OK" "SignTool: $signtool"

$osList = '10_X64'
Write-Status "INFO" "Using OS target: $osList"

# ── Run Inf2Cat ───────────────────────────────────────────────────────────────

Write-Status "INFO" "Running Inf2Cat on folder: $DriverDir"
Write-Status "INFO" "  /os:$osList"

$inf2catArgs = @("/driver:`"$DriverDir`"", "/os:$osList")
$result = & $inf2cat @inf2catArgs 2>&1
Write-Host $result

if ($LASTEXITCODE -ne 0) {
    Write-Status "ERROR" "Inf2Cat failed (exit code $LASTEXITCODE)"
    exit 1
}

# Find the generated .cat file
$catFile = Get-ChildItem -Path $DriverDir -Filter "*.cat" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $catFile) {
    Write-Status "ERROR" "Inf2Cat appeared to succeed but no .cat file was found in: $DriverDir"
    exit 1
}
Write-Status "OK" "Generated catalog: $($catFile.FullName)"

# ── Sign with SignTool ────────────────────────────────────────────────────────

Write-Status "INFO" "Signing $($catFile.Name) with certificate: $(Split-Path $PfxPath -Leaf)"

$signArgs = @(
    'sign',
    '/fd', 'SHA256',
    '/f', "`"$PfxPath`"",
    '/p', $PfxPassword,
    '/tr', $TimestampUrl,
    '/td', 'SHA256',
    "`"$($catFile.FullName)`""
)

$signResult = & $signtool @signArgs 2>&1
Write-Host $signResult

if ($LASTEXITCODE -ne 0) {
    # Retry with fallback timestamp server
    Write-Status "INFO" "Timestamp server failed; retrying with Sectigo fallback..."
    $signArgs[6] = 'http://timestamp.sectigo.com'
    $signResult2 = & $signtool @signArgs 2>&1
    Write-Host $signResult2

    if ($LASTEXITCODE -ne 0) {
        # Sign without timestamp as last resort
        Write-Status "INFO" "Both timestamp servers unreachable. Signing without timestamp..."
        $noTsArgs = @('sign', '/fd', 'SHA256', '/f', "`"$PfxPath`"", '/p', $PfxPassword, "`"$($catFile.FullName)`"")
        $signResult3 = & $signtool @noTsArgs 2>&1
        Write-Host $signResult3
        if ($LASTEXITCODE -ne 0) {
            Write-Status "ERROR" "SignTool failed (exit code $LASTEXITCODE)"
            exit 1
        }
        Write-Status "INFO" "WARNING: Signed without timestamp. The signature will expire with the certificate."
    }
}

Write-Status "OK" "Successfully signed: $($catFile.FullName)"
Write-Host ""
Write-Host "Output: $($catFile.FullName)"
