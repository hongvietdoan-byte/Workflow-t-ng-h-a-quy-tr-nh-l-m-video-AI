# Opens the AI Video Pipeline dashboard like a desktop app (double-click Start-Dashboard.bat).
# - Reads optional non-secret settings from dashboard.env (copy dashboard.env.example).
# - API tokens (CLIPAI_TOKEN, DEEPIX_TOKEN) come from your Windows user environment; never store them here.
# - Starts Streamlit minimized and opens the dashboard in its own app-style window.
$ErrorActionPreference = "Stop"
# The shortcut runs this window-less: a failure is written to data\launcher.log and shown in a message box.
function Show-Failure([string]$msg) {
    $logDir = Join-Path $PSScriptRoot "..\data"
    try { New-Item -ItemType Directory -Force -Path $logDir | Out-Null; Add-Content (Join-Path $logDir "launcher.log") "$(Get-Date -Format s) $msg" -Encoding UTF8 } catch {}
    try { Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show("Khong mo duoc Dashboard.`n`n$msg`n`nXem data\dashboard.log va data\launcher.log", "AI Video Pipeline") } catch {}
}
trap { Show-Failure $_.Exception.Message; exit 1 }
$root = Split-Path -Parent $PSScriptRoot
$asciiRoot = $root   # path as launched (ASCII junction): safe inside a file:// URL
# Started through the ASCII junction made by make_shortcut.ps1? Python (Store build) misreads a junction as
# working directory, so switch to the real folder.
$item = Get-Item $root
if ($item.LinkType -eq "Junction") { $root = @($item.Target)[0] }
Set-Location $root
[Environment]::CurrentDirectory = $root
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

function Open-Dashboard([string]$target = $url) {
    # Default: a tab in your normal web browser. DASHBOARD_APP_WINDOW=1 (in dashboard.env) = separate app-style window.
    $browser = if ($env:DASHBOARD_APP_WINDOW -eq "1") { Find-Browser } else { $null }
    if ($browser) { Start-Process -FilePath $browser -ArgumentList "--app=$target" } else { Start-Process $target }
}

if (Test-Port $port) { Open-Dashboard; exit 0 }   # already running: just open a window

# Not running yet: show a loading window with the logo at once; it switches to the dashboard when the server answers.
$loadingFile = Join-Path $asciiRoot "tools\loading.html"
$showedLoading = $false
if (Test-Path $loadingFile) { Open-Dashboard ("file:///" + $loadingFile.Replace('\', '/') + "?port=$port"); $showedLoading = $true }

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Show-Failure "Chua cai Python (lenh 'py'). Cai Python 3 tu python.org roi mo lai."; exit 1
}

py -c "import streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Lan dau chay: dang cai thu vien (requirements.txt)..." -ForegroundColor Yellow
    py -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Show-Failure "Cai thu vien that bai (py -m pip install -r requirements.txt)."; exit 1 }
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

New-Item -ItemType Directory -Force -Path (Join-Path $root "data") | Out-Null
$log = Join-Path $root "data\dashboard.log"
# Headless: Streamlit must not open its own tab or ask for an e-mail on first run (that prompt would block the server).
# Local only by default (the dashboard spends credits and has no login): DASHBOARD_LAN=1 opens it to your network.
$address = if ($env:DASHBOARD_LAN -eq "1") { "0.0.0.0" } else { "127.0.0.1" }
$errLog = Join-Path $root "data\dashboard_err.log"
Start-Process -WindowStyle Hidden -WorkingDirectory $root -FilePath "py" -RedirectStandardOutput $log -RedirectStandardError $errLog `
    -ArgumentList "-m", "streamlit", "run", "dashboard/app.py", "--server.port", "$port", "--server.address", $address, "--server.headless", "true", "--browser.gatherUsageStats", "false"
for ($i = 0; $i -lt 40 -and -not (Test-Port $port); $i++) { Start-Sleep -Milliseconds 500 }
if (-not (Test-Port $port)) { Show-Failure "May chu chua len sau 20 giay (cong $port)."; exit 1 }
if (-not $showedLoading) { Open-Dashboard }
