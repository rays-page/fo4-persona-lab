[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$Fallout4Path = "C:\Program Files (x86)\Steam\steamapps\common\Fallout 4",
    [switch]$EnablePlugin,
    [switch]$SkipSources,
    [switch]$NoBackup
)

$ErrorActionPreference = "Stop"

$repoGameDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pluginName = "F4RPPersonaLab.esp"
$pluginSource = Join-Path $repoGameDir $pluginName
$scriptsDir = Join-Path $repoGameDir "scripts"
$sourceDir = Join-Path $scriptsDir "Source\User"

if (!(Test-Path -LiteralPath $Fallout4Path -PathType Container)) {
    throw "Fallout 4 folder not found: $Fallout4Path"
}

$dataDir = Join-Path $Fallout4Path "Data"
if (!(Test-Path -LiteralPath $dataDir -PathType Container)) {
    throw "Fallout 4 Data folder not found: $dataDir"
}

function Backup-IfNeeded {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if ($NoBackup -or !(Test-Path -LiteralPath $Path)) {
        return
    }

    $stamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupPath = "$Path.f4rp-backup-$stamp"
    if ($PSCmdlet.ShouldProcess($Path, "Back up to $backupPath")) {
        Copy-Item -LiteralPath $Path -Destination $backupPath -Force
    }
}

function Copy-Artifact {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Source,
        [Parameter(Mandatory = $true)]
        [string]$Destination
    )

    if (!(Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "Missing source artifact: $Source"
    }

    $destinationDir = Split-Path -Parent $Destination
    if (!(Test-Path -LiteralPath $destinationDir -PathType Container)) {
        if ($PSCmdlet.ShouldProcess($destinationDir, "Create directory")) {
            New-Item -ItemType Directory -Path $destinationDir | Out-Null
        }
    }

    Backup-IfNeeded -Path $Destination
    if ($PSCmdlet.ShouldProcess($Destination, "Copy $Source")) {
        Copy-Item -LiteralPath $Source -Destination $Destination -Force
        Write-Host "Installed $Destination"
    }
}

function Ensure-Line {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string]$Line
    )

    $dir = Split-Path -Parent $Path
    if (!(Test-Path -LiteralPath $dir -PathType Container)) {
        if ($PSCmdlet.ShouldProcess($dir, "Create directory")) {
            New-Item -ItemType Directory -Path $dir | Out-Null
        }
    }

    if (!(Test-Path -LiteralPath $Path)) {
        if ($PSCmdlet.ShouldProcess($Path, "Create file")) {
            New-Item -ItemType File -Path $Path | Out-Null
        }
    }

    $existing = Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($existing -contains $Line) {
        Write-Host "Already enabled in $Path`: $Line"
        return
    }

    Backup-IfNeeded -Path $Path
    if ($PSCmdlet.ShouldProcess($Path, "Append $Line")) {
        Add-Content -LiteralPath $Path -Value $Line
        Write-Host "Added $Line to $Path"
    }
}

Copy-Artifact -Source $pluginSource -Destination (Join-Path $dataDir $pluginName)

Copy-Artifact `
    -Source (Join-Path $scriptsDir "F4RP_BridgeQuestScript.pex") `
    -Destination (Join-Path $dataDir "Scripts\F4RP_BridgeQuestScript.pex")

Copy-Artifact `
    -Source (Join-Path $scriptsDir "F4RP_NativeBridge.pex") `
    -Destination (Join-Path $dataDir "Scripts\F4RP_NativeBridge.pex")

if (!$SkipSources) {
    Copy-Artifact `
        -Source (Join-Path $sourceDir "F4RP_BridgeQuestScript.psc") `
        -Destination (Join-Path $dataDir "Scripts\Source\User\F4RP_BridgeQuestScript.psc")

    Copy-Artifact `
        -Source (Join-Path $sourceDir "F4RP_NativeBridge.psc") `
        -Destination (Join-Path $dataDir "Scripts\Source\User\F4RP_NativeBridge.psc")
}

if ($EnablePlugin) {
    $falloutLocal = Join-Path $env:LOCALAPPDATA "Fallout4"
    Ensure-Line -Path (Join-Path $falloutLocal "Plugins.txt") -Line "*$pluginName"
    Ensure-Line -Path (Join-Path $falloutLocal "loadorder.txt") -Line $pluginName
}

Write-Host "FO4 Persona Lab deploy complete."
