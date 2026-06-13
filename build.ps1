# Build Personal Journal as a standalone Windows executable using PyInstaller,
# then optionally package it with NSIS into a Setup executable.
#
# Usage:
#   .\build.ps1              – PyInstaller only
#   .\build.ps1 -Installer   – PyInstaller + NSIS installer
#
# Run from any location — the script always operates in its own directory.

param(
    [switch]$Installer,      # also build the NSIS installer after PyInstaller
    [switch]$InstallerOnly   # skip PyInstaller; run NSIS only
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AppName    = "personalJournal"
$AppDir     = Split-Path -Parent $MyInvocation.MyCommand.Path
$DistDir    = Join-Path $AppDir "dist"
$BuildDir   = Join-Path $AppDir "build"
$NsiScript  = Join-Path $AppDir "installer.nsi"

# Resolve UPX: UPX_DIR env var → D:\Programs\UPX (default) → upx in PATH → local tools\
$UpxDir = $null
if ($env:UPX_DIR) {
    $UpxDir = $env:UPX_DIR
} elseif (Test-Path "D:\Programs\UPX\upx.exe") {
    $UpxDir = "D:\Programs\UPX"
} else {
    $upxCmd = Get-Command upx -ErrorAction SilentlyContinue
    if ($upxCmd) {
        $UpxDir = Split-Path $upxCmd.Source
    } else {
        $localUpx = Join-Path $AppDir "tools\upx\upx-5.2.0-win64"
        if (Test-Path (Join-Path $localUpx "upx.exe")) { $UpxDir = $localUpx }
    }
}

Set-Location $AppDir

# ── Check prerequisites ──────────────────────────────────────────────────────

if (-not $InstallerOnly) {
    if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
        Write-Error "PyInstaller not found. Install it with: pip install pyinstaller"
        exit 1
    }

    if (-not $UpxDir) {
        Write-Error "UPX not found. Set the UPX_DIR environment variable, add upx to PATH, or place upx.exe under tools\upx\upx-5.2.0-win64\"
        exit 1
    }
    $UpxExe = Join-Path $UpxDir "upx.exe"
    Write-Host "UPX        : $UpxExe" -ForegroundColor Cyan
}

if ($Installer -or $InstallerOnly) {
    $MakeNsis = Get-Command makensis -ErrorAction SilentlyContinue
    if (-not $MakeNsis) {
        # Common NSIS install locations on Windows
        $Candidates = @(
            "C:\Program Files (x86)\NSIS\makensis.exe",
            "C:\Program Files\NSIS\makensis.exe"
        )
        foreach ($c in $Candidates) {
            if (Test-Path $c) { $MakeNsis = $c; break }
        }
        if (-not $MakeNsis) {
            Write-Error "makensis not found. Install NSIS from https://nsis.sourceforge.io/ or add it to PATH."
            exit 1
        }
    } else {
        $MakeNsis = $MakeNsis.Source
    }
    Write-Host "makensis   : $MakeNsis" -ForegroundColor Cyan
    if (-not (Test-Path $NsiScript)) {
        Write-Error "NSIS script not found: $NsiScript"
        exit 1
    }
}

if (-not $InstallerOnly) {

    # ── Clean previous build artefacts ──────────────────────────────────────────

    Write-Host "Cleaning previous build..." -ForegroundColor Cyan

    foreach ($dir in @($DistDir, $BuildDir)) {
        if (Test-Path $dir) {
            Remove-Item $dir -Recurse -Force
            Write-Host "  Removed: $dir"
        }
    }

    $specFile = Join-Path $AppDir "$AppName.spec"
    if (Test-Path $specFile) {
        Remove-Item $specFile -Force
        Write-Host "  Removed: $specFile"
    }

    # ── Run PyInstaller ──────────────────────────────────────────────────────────

    Write-Host "`nBuilding '$AppName'..." -ForegroundColor Cyan

    pyinstaller `
        --onedir `
        --windowed `
        --noconfirm `
        --distpath     $DistDir `
        --workpath     $BuildDir `
        --upx-dir      $UpxDir `
        --hidden-import wx.adv `
        --exclude-module tkinter `
        --exclude-module unittest `
        --exclude-module pydoc `
        --exclude-module doctest `
        --exclude-module difflib `
        --add-data     "locales;locales" `
        --add-data     "sounds;sounds" `
        --add-binary   "UniversalSpeech.dll;." `
        --add-binary   "nvdaControllerClient.dll;." `
        --add-binary   "ZDSRAPI.dll;." `
        --name "PersonalJournal" `
        --version-file         "version.txt" `
        main.py

    if ($LASTEXITCODE -ne 0) {
        Write-Error "PyInstaller failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }

}

if (-not $InstallerOnly) {

    # ── Report result ────────────────────────────────────────────────────────────

    $ExeName  = "PersonalJournal"
    $ExePath  = Join-Path (Join-Path $DistDir $ExeName) "$ExeName.exe"
    $DirPath  = Join-Path $DistDir $ExeName

    if (Test-Path $ExePath) {
        $ExeSize  = (Get-Item $ExePath).Length / 1MB
        $DirSize  = (Get-ChildItem $DirPath -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB
        Write-Host "`nBuild succeeded." -ForegroundColor Green
        Write-Host "  Executable : $ExePath"
        Write-Host ("  Exe size   : {0:N1} MB" -f $ExeSize)
        Write-Host ("  Total size : {0:N1} MB" -f $DirSize)
    } else {
        Write-Error "Build appeared to succeed but the exe was not found at: $ExePath"
        exit 1
    }

}

# ── NSIS installer ──────────────────────────────────────────────────────────

if ($Installer -or $InstallerOnly) {
    Write-Host "`nBuilding NSIS installer..." -ForegroundColor Cyan

    # Run makensis from src/ so relative paths in the .nsi resolve correctly
    Push-Location $AppDir
    try {
        & $MakeNsis $NsiScript
        if ($LASTEXITCODE -ne 0) {
            Write-Error "makensis failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
    } finally {
        Pop-Location
    }

    # Find the generated setup exe next to the .nsi
    $SetupExe = Get-ChildItem $AppDir -Filter "PersonalJournal-*-setup.exe" |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1

    if ($SetupExe) {
        $SetupSize = $SetupExe.Length / 1MB
        Write-Host "`nInstaller built." -ForegroundColor Green
        Write-Host "  Setup file : $($SetupExe.FullName)"
        Write-Host ("  Size       : {0:N1} MB" -f $SetupSize)
    } else {
        Write-Warning "NSIS reported success but no Setup exe was found in $RepoRoot"
    }
}
