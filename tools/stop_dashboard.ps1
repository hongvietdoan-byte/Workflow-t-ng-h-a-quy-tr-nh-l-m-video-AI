# Stops the dashboard started by Start-Dashboard.bat (frees the port).
$port = if ($env:DASHBOARD_PORT) { [int]$env:DASHBOARD_PORT } else { 8501 }
$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) { Write-Host "Dashboard khong chay tren cong $port."; exit 0 }
$conns | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Write-Host "Da tat dashboard (cong $port)."
