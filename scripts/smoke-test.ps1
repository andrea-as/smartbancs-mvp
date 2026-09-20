$ErrorActionPreference = "Stop"
$transfer = @{
  source_account = "ACC-1001"
  destination_account = "ACC-1002"
  amount = 1
  currency = "USD"
} | ConvertTo-Json
$result = Invoke-RestMethod http://localhost:8000/api/v1/transfers -Method Post -ContentType "application/json" -Body $transfer
if ($result.status -ne "COMPLETED") { throw "Transferencia no completada" }
Invoke-RestMethod http://localhost:8000/synthetic/transfer
