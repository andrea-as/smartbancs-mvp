$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$docker = Get-Command docker -ErrorAction SilentlyContinue
$dockerDir = $null
if (-not $docker) {
  $candidate = "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
  if (Test-Path -LiteralPath $candidate) {
    $docker = Get-Item -LiteralPath $candidate
    $dockerDir = Split-Path -Parent $candidate
  }
}
if (-not $docker) {
  throw "No se encontró docker.exe."
}
$dockerPath = if ($docker.PSObject.Properties.Name -contains "FullName") { $docker.FullName } else { $docker.Source }
if ($dockerDir) {
  $env:Path = "$dockerDir;$env:Path"
}
& $dockerPath compose down
