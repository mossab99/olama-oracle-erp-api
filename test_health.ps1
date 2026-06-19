$url = "http://localhost:5000/api/health"

Write-Host "Testing API health endpoint: $url"
Invoke-RestMethod -Uri $url -Method GET
