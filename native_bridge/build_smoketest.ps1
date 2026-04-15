param(
    [string]$Compiler = "g++",
    [switch]$RunSmoke,
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"

$bridgeRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $bridgeRoot "..")
$buildDir = Join-Path $bridgeRoot "build"
$exePath = Join-Path $buildDir "f4rp_bridge_smoketest.exe"

New-Item -ItemType Directory -Force $buildDir | Out-Null

$compileArgs = @(
    "-std=c++20",
    "-O2",
    "-I", (Join-Path $bridgeRoot "include"),
    (Join-Path $bridgeRoot "src\\bridge_runtime.cpp"),
    (Join-Path $bridgeRoot "src\\smoketest_main.cpp"),
    "-o", $exePath,
    "-lwinhttp",
    "-lws2_32"
)

Write-Host "Compiling smoketest with $Compiler ..."
& $Compiler @compileArgs
if ($LASTEXITCODE -ne 0) {
    throw "Compilation failed with exit code $LASTEXITCODE"
}

Write-Host "Built: $exePath"

if (-not $RunSmoke) {
    exit 0
}

Write-Host "Starting local service for smoke test ..."
$serverProcess = Start-Process $PythonExe -ArgumentList "-m", "fo4_persona_lab.server" -WorkingDirectory $repoRoot -PassThru

try {
    Start-Sleep -Seconds 2
    & $exePath
    if ($LASTEXITCODE -ne 0) {
        throw "Smoke test failed with exit code $LASTEXITCODE"
    }
}
finally {
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force
    }
}

Write-Host "Smoke test passed."
