# Opens the AI Video Pipeline dashboard like a desktop app (double-click Start-Dashboard.bat).
# - Reads optional non-secret settings from dashboard.env (copy dashboard.env.example).
# - API tokens (CLIPAI_TOKEN, DEEPIX_TOKEN) come from your Windows user environment; never store them here.
# - Starts Streamlit minimized and opens the dashboard in its own app-style window.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$port = if ($env:DASHBOARD_PORT) { [int]$env:DASHBOARD_PORT } else { 8501 }
$url = "http://localhost:$port"

function Test-Port([int]$p) {
    $c = New-Object System.Net.Sockets.TcpClient
    try { $c.Connect("127.0.0.1", $p); return $true } catch { return $false } finally { $c.Close() }
}

function Find-Browser {
    $candidates = @(
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
        "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
        "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe")
    return $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
}

function Open-Dashboard {
    $browser = Find-Browser
    if ($browser) { Start-Process -FilePath $browser -ArgumentList "--app=$url" } else { Start-Process $url }
}

if (Test-Port $port) { Open-Dashboard; exit 0 }   # already running: just open a window

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Chua cai Python (lenh 'py'). Cai Python 3 tu python.org roi mo lai." -ForegroundColor Red
    Read-Host "Nhan Enter de dong"; exit 1
}

py -c "import streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Lan dau chay: dang cai thu vien (requirements.txt)..." -ForegroundColor Yellow
    py -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Read-Host "Cai thu vien that bai. Nhan Enter de dong"; exit 1 }
}

$envFile = Join-Path $root "dashboard.env"
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile -Encoding UTF8) {
        $t = $line.Trim()
        if ($t -eq "" -or $t.StartsWith("#") -or -not $t.Contains("=")) { continue }
        $k, $v = $t.Split("=", 2)
        [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim().Trim('"'), "Process")
    }
}

if (-not $env:FFMPEG_PATH -and -not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    $found = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Filter ffmpeg.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) { $env:FFMPEG_PATH = $found.FullName }
}

foreach ($name in "CLIPAI_TOKEN", "DEEPIX_TOKEN") {
    if ($env:VIDEO_PROVIDER -eq "clipai" -or $env:IMAGE_PROVIDER -eq "deepix") {
        if (-not [Environment]::GetEnvironmentVariable($name)) { Write-Host "Canh bao: chua dat $name (xem TODO.md / docs)." -ForegroundColor Yellow }
    }
}

Start-Process -WindowStyle Minimized -FilePath "py" -ArgumentList "-m", "streamlit", "run", "dashboard/app.py", "--server.port", $port
for ($i = 0; $i -lt 40 -and -not (Test-Port $port); $i++) { Start-Sleep -Milliseconds 500 }
Open-Dashboard
