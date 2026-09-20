$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:TOTAL_REQUESTS = "10000"
$env:CONCURRENCY = "1000"
$env:TRANSFER_AMOUNT = "0.01"
python tests\load_test.py
