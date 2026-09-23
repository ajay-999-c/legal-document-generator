# Per-user installation; run as the office user, without administrator elevation.
[CmdletBinding()]
param(
    [string]$SourceExe = (Join-Path $PSScriptRoot 'dist\Legal Document Generator.exe'),
    [string]$ConfigSeed = (Join-Path $PSScriptRoot 'config.example.yaml'),
    [string]$CredentialsFile
)
$ErrorActionPreference = 'Stop'
if ($env:OS -ne 'Windows_NT') { throw 'Run this installer on Windows.' }
$AppId = 'LegalDocumentGenerator'
$InstallDir = Join-Path $env:LOCALAPPDATA "Programs\$AppId"
$DataDir = Join-Path $env:APPDATA $AppId
$TargetExe = Join-Path $InstallDir 'Legal Document Generator.exe'
$ConfigPath = Join-Path $DataDir 'config.yaml'
$CredentialPath = Join-Path $DataDir 'credentials.json'

if (-not (Test-Path -LiteralPath $SourceExe -PathType Leaf)) { throw 'Source executable is missing. Build first or supply -SourceExe.' }
if (-not (Test-Path -LiteralPath $ConfigPath) -and -not (Test-Path -LiteralPath $ConfigSeed -PathType Leaf)) { throw 'Initial config seed is missing.' }
if ($CredentialsFile -and -not (Test-Path -LiteralPath $CredentialsFile -PathType Leaf)) { throw 'Supplied credentials file is missing.' }
$Running = Get-Process -Name 'Legal Document Generator' -ErrorAction SilentlyContinue
if ($Running) { throw 'Close Legal Document Generator before installing or upgrading.' }

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $DataDir 'logs') -Force | Out-Null
# Stage the executable before replacement; configuration and credentials are never
# copied from the build tree or overwritten by an upgrade.
$Stage = Join-Path $InstallDir 'Legal Document Generator.exe.new'
Copy-Item -LiteralPath $SourceExe -Destination $Stage -Force
try {
    if (Test-Path -LiteralPath $TargetExe) {
        [System.IO.File]::Replace($Stage, $TargetExe, $null)
    } else {
        [System.IO.File]::Move($Stage, $TargetExe)
    }
} finally {
    if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage }
}
if (-not (Test-Path -LiteralPath $ConfigPath)) {
    # overwrite=false also protects against concurrent provisioning.
    [System.IO.File]::Copy((Resolve-Path -LiteralPath $ConfigSeed).Path, $ConfigPath, $false)
    Write-Host "Created $ConfigPath - administrator setup is required."
} else {
    Write-Host "Preserved $ConfigPath"
}
if ($CredentialsFile) {
    if (-not (Test-Path -LiteralPath $CredentialPath)) {
        [System.IO.File]::Copy((Resolve-Path -LiteralPath $CredentialsFile).Path, $CredentialPath, $false)
        Write-Host 'Provisioned credentials.json separately.'
    } else {
        Write-Host 'Preserved existing credentials.json; supplied replacement was not copied.'
    }
} else {
    Write-Host "Provision credentials separately at $CredentialPath if absent."
}

$Shell = New-Object -ComObject WScript.Shell
$DesktopDir = [Environment]::GetFolderPath('DesktopDirectory')
$ProgramsDir = [Environment]::GetFolderPath('Programs')
foreach ($ShortcutDir in @($DesktopDir, $ProgramsDir)) {
    New-Item -ItemType Directory -Path $ShortcutDir -Force | Out-Null
    $Shortcut = $Shell.CreateShortcut((Join-Path $ShortcutDir 'Legal Document Generator.lnk'))
    $Shortcut.TargetPath = $TargetExe
    $Shortcut.WorkingDirectory = $InstallDir
    $Shortcut.Description = 'Generate legal documents from approved Google Sheets submissions'
    $Shortcut.IconLocation = "$TargetExe,0"
    $Shortcut.Save()
}
Write-Host "Installed: $TargetExe"
Write-Host "Runtime data: $DataDir"
Write-Host 'Desktop and Start-menu shortcuts created. Existing settings and credentials preserved.'
