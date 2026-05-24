param(
    [string]$Python = "python",
    [string]$Version = "0.2.5",
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$Dist = Join-Path $Root "dist"
$Build = Join-Path $Root "build"
$PortableDir = Join-Path $Dist "windows-portable"
$ExeName = "HUSTCampusAutologin.exe"
$CliExeName = "HUSTCampusAutologinCLI.exe"
$PortableZip = Join-Path $Dist "HUSTCampusAutologin-$Version-windows-portable.zip"
$Installer = Join-Path $Dist "HUSTCampusAutologinSetup-$Version.exe"
$NsisScript = Join-Path $Root "installer\windows\HUSTCampusAutologin.nsi"
$EntryPoint = Join-Path $Root "packaging\windows\entrypoint.py"
$GuiEntryPoint = Join-Path $Root "packaging\windows\gui_entrypoint.py"

New-Item -ItemType Directory -Force -Path $Dist | Out-Null
New-Item -ItemType Directory -Force -Path $Build | Out-Null

if (Test-Path $PortableDir) {
    Remove-Item -LiteralPath $PortableDir -Recurse -Force
}
if (Test-Path $PortableZip) {
    Remove-Item -LiteralPath $PortableZip -Force
}
if (Test-Path $Installer) {
    Remove-Item -LiteralPath $Installer -Force
}

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name "HUSTCampusAutologin" `
    --distpath $PortableDir `
    --workpath (Join-Path $Build "pyinstaller-gui") `
    --specpath (Join-Path $Build "pyinstaller-spec") `
    $GuiEntryPoint

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --console `
    --name "HUSTCampusAutologinCLI" `
    --distpath $PortableDir `
    --workpath (Join-Path $Build "pyinstaller-cli") `
    --specpath (Join-Path $Build "pyinstaller-spec") `
    $EntryPoint

Copy-Item -LiteralPath (Join-Path $Root "README.md") -Destination $PortableDir
Copy-Item -LiteralPath (Join-Path $Root "config.example.toml") -Destination $PortableDir
Copy-Item -LiteralPath (Join-Path $Root "LICENSE") -Destination $PortableDir
$PortableDocs = Join-Path $PortableDir "docs"
New-Item -ItemType Directory -Force -Path $PortableDocs | Out-Null
Copy-Item -LiteralPath (Join-Path $Root "docs\windows-source.md") -Destination $PortableDocs
Copy-Item -LiteralPath (Join-Path $Root "docs\windows-package.md") -Destination $PortableDocs
Copy-Item -LiteralPath (Join-Path $Root "docs\troubleshooting.md") -Destination $PortableDocs
Copy-Item -LiteralPath (Join-Path $Root "docs\linux-systemd.md") -Destination $PortableDocs

Compress-Archive -Path (Join-Path $PortableDir "*") -DestinationPath $PortableZip -Force

if (-not $SkipInstaller) {
    $Makensis = Get-Command makensis.exe -ErrorAction SilentlyContinue
    if (-not $Makensis) {
        $CandidatePaths = @(
            "${env:ProgramFiles(x86)}\NSIS\makensis.exe",
            "$env:ProgramFiles\NSIS\makensis.exe",
            "$env:LOCALAPPDATA\Programs\NSIS\makensis.exe"
        )
        foreach ($Candidate in $CandidatePaths) {
            if ($Candidate -and (Test-Path $Candidate)) {
                $Makensis = Get-Item $Candidate
                break
            }
        }
    }
    if (-not $Makensis) {
        throw "makensis.exe was not found. Install NSIS or rerun with -SkipInstaller."
    }

    $MakensisPath = if ($Makensis.Source) { $Makensis.Source } else { $Makensis.FullName }
    & $MakensisPath `
        "/DAPP_VERSION=$Version" `
        "/DSOURCE_EXE=$(Join-Path $PortableDir $ExeName)" `
        "/DSOURCE_CLI_EXE=$(Join-Path $PortableDir $CliExeName)" `
        "/DOUT_FILE=$Installer" `
        $NsisScript
}

Write-Host "Portable directory: $PortableDir"
Write-Host "Portable zip: $PortableZip"
if (-not $SkipInstaller) {
    Write-Host "Installer: $Installer"
}
