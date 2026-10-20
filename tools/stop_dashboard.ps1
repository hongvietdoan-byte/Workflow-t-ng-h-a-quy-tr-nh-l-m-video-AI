# Stops the dashboard started by Start-Dashboard.bat (frees the port).
#   powershell -File tools\stop_dashboard.ps1          -> cong DASHBOARD_PORT (mac dinh 8501), nhu cu
#   powershell -File tools\stop_dashboard.ps1 -All     -> MOI tien trinh "dashboard.serve" (moi cong: 8501, 8503, 8504...)
# V3.1 M1.7 (G55, 20/10): 2 Dashboard cu 8503/8504 chay code cu ca ngay vi lenh nay chi tat 8501.
param([switch]$All)
if ($All) {
    $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match 'dashboard\.serve|streamlit.+dashboard[\\/]app\.py' }
    if (-not $procs) { Write-Host "Khong co tien trinh dashboard.serve nao."; exit 0 }
    foreach ($p in $procs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "Da tat dashboard pid $($p.ProcessId): $($p.CommandLine)"
    }
    exit 0
}
$port = if ($env:DASHBOARD_PORT) { [int]$env:DASHBOARD_PORT } else { 8501 }
$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) { Write-Host "Dashboard khong chay tren cong $port."; exit 0 }
$conns | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Write-Host "Da tat dashboard (cong $port)."
