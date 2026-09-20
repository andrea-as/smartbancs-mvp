$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$docker = Get-Command docker -ErrorAction SilentlyContinue
$dockerDir = $null
if (-not $docker) {
  $candidates = @(
    "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
    "$env:LOCALAPPDATA\Programs\DockerDesktop\resources\bin\docker.exe"
  )
  foreach ($candidate in $candidates) {
    if (Test-Path -LiteralPath $candidate) {
      $docker = Get-Item -LiteralPath $candidate
      $dockerDir = Split-Path -Parent $candidate
      break
    }
  }
}
if (-not $docker) {
  throw "No se encontró docker.exe. Abra Docker Desktop o agregue su carpeta resources\bin al PATH."
}
$dockerPath = if ($docker.PSObject.Properties.Name -contains "FullName") { $docker.FullName } else { $docker.Source }
if ($dockerDir) {
  $env:Path = "$dockerDir;$env:Path"
}
& $dockerPath version
if ($LASTEXITCODE -ne 0) {
  throw "Docker Desktop está instalado, pero el motor no responde. Espere a que termine de iniciar."
}
& $dockerPath compose up --build -d
$healthy = $false
for ($attempt = 1; $attempt -le 12; $attempt++) {
  try {
    Invoke-RestMethod http://localhost:8000/health -TimeoutSec 5 | Out-Null
    $healthy = $true
    break
  } catch {
    Start-Sleep -Seconds 5
  }
}
if (-not $healthy) {
  throw "Los contenedores arrancaron, pero la API no respondió en 60 segundos."
}
Invoke-RestMethod http://localhost:8000/health
Write-Host "SmartBancs listo: http://localhost:8000/docs"
