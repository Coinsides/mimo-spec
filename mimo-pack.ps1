param(
  [string]$In,
  [string]$Out,
  [string]$Source = "file",
  [string]$Workspace = "",
  [string]$Split = "line_window:400",
  [string]$VaultId = "default"
)

$ErrorActionPreference = "Stop"

if (-not $In -or -not $Out) {
  Write-Host "Usage: mimo-pack.ps1 -In <dir> -Out <dir> [-Source file] [-Workspace ws_x] [-Split line_window:400] [-VaultId default]" -ForegroundColor Yellow
  exit 2
}

$cmd = @(
  "python", "-m", "mimo_spec.tools.mimo_pack",
  "--in", $In,
  "--out", $Out,
  "--source", $Source,
  "--split", $Split,
  "--vault-id", $VaultId
)

if ($Workspace) {
  $cmd += @("--workspace", $Workspace)
}

& $cmd
