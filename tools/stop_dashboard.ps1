# Stops the dashboard started by Start-Dashboard.bat (frees the port).
#   powershell -File tools\stop_dashboard.ps1          -> cong DASHBOARD_PORT (mac dinh 8501), nhu cu
#   powershell -File tools\stop_dashboard.ps1 -All     -> MOI tien trinh "dashboard.serve" CUA REPO NAY (moi cong: 8501, 8503, 8504...)
#   powershell -File tools\stop_dashboard.ps1 -All -AnyRepo -> ke ca dashboard.serve cua ban cai khac tren may
# V3.1 M1.7 (G55, 20/10): 2 Dashboard cu 8503/8504 chay code cu ca ngay vi lenh nay chi tat 8501.
param([switch]$All, [switch]$AnyRepo)
if ($All) {
    # C-FIX-M16-17: chi dashboard cua CHINH repo nay - duong dan repo trong dong lenh, hoac pid trong so data\run\dashboard_*.json
    # (core/code_version.register); tien trinh khac chi duoc LIET KE (them -AnyRepo de tat ca). Khong in CommandLine (co the mang token).
    $repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $runDir = if ($env:PIPELINE_DB) { Join-Path (Split-Path $env:PIPELINE_DB -Parent) 'run' } else { Join-Path $repo 'data\run' }
    $known = @()
    Get-ChildItem -Path $runDir -Filter 'dashboard_*.json' -ErrorAction SilentlyContinue | ForEach-Object {
        try { $known += [int]((Get-Content $_.FullName -Raw | ConvertFrom-Json).pid) } catch { }
    }
    $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -and $_.CommandLine -match 'dashboard\.serve|streamlit.+dashboard[\\/]app\.py' }
    if (-not $procs) { Write-Host "Khong co tien trinh dashboard.serve nao."; exit 0 }
    foreach ($p in $procs) {
        $port = if ($p.CommandLine -match 'server\.port[ =](\d+)') { $Matches[1] } else { '?' }
        $mine = $AnyRepo -or ($known -contains [int]$p.ProcessId) -or
                ($p.CommandLine.IndexOf($repo, [StringComparison]::OrdinalIgnoreCase) -ge 0)
        if ($mine) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Host "Da tat dashboard pid $($p.ProcessId) (cong $port)"
        } else {
            Write-Host "BO QUA dashboard pid $($p.ProcessId) (cong $port): khong chac thuoc $repo - them -AnyRepo de tat ca"
        }
    }
    exit 0
}
$port = if ($env:DASHBOARD_PORT) { [int]$env:DASHBOARD_PORT } else { 8501 }
$conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if (-not $conns) { Write-Host "Dashboard khong chay tren cong $port."; exit 0 }
$conns | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
Write-Host "Da tat dashboard (cong $port)."
