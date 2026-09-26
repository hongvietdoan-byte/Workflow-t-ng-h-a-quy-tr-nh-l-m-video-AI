# Starts the AI Development System web (if needed) and opens it in your browser: http://localhost:8502
# Double-click Start-DevSystem.bat. Separate from the production dashboard (port 8501); reads the repo, costs nothing unless you
# confirm an AI scoring run (Claude API, recorded in the dashboard's cost ledger data\manifest.sqlite, stage "devsys").
$ErrorActionPreference = "Stop"
function Show-Failure([string]$msg) {
    $logDir = Join-Path $PSScriptRoot "..\devsys\data"
    try { New-Item -ItemType Directory -Force -Path $logDir | Out-Null; Add-Content (Join-Path $logDir "launcher.log") "$(Get-Date -Format s) $msg" -Encoding UTF8 } catch {}
    try { Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show("Khong mo duoc AI Development System.`n`n$msg`n`nXem devsys\data\devsys.log", "AI Development System") } catch {}
}
trap { Show-Failure $_.Exception.Message; exit 1 }
$root = Split-Path -Parent $PSScriptRoot
$item = Get-Item $root
if ($item.LinkType -eq "Junction") { $root = @($item.Target)[0] }
Set-Location $root
[Environment]::CurrentDirectory = $root
$port = if ($env:DEVSYS_PORT) { [int]$env:DEVSYS_PORT } else { 8502 }
$url = "http://localhost:$port"

function Test-Port([int]$p) {
    $c = New-Object System.Net.Sockets.TcpClient
    try { $c.Connect("127.0.0.1", $p); return $true } catch { return $false } finally { $c.Close() }
}

if (Test-Port $port) { Start-Process $url; exit 0 }   # already running: just open the page

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Show-Failure "Chua cai Python (lenh 'py'). Cai Python 3 tu python.org roi mo lai."; exit 1
}
py -c "import streamlit" 2>$null
if ($LASTEXITCODE -ne 0) {
    py -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { Show-Failure "Cai thu vien that bai (py -m pip install -r requirements.txt)."; exit 1 }
}

# Same non-secret settings as the dashboard (model, cost cap...) so an AI scoring run uses the same Claude model and ledger.
$envFile = Join-Path $root "dashboard.env"
if (Test-Path $envFile) {
    foreach ($line in Get-Content $envFile -Encoding UTF8) {
        $t = $line.Trim()
        if ($t -eq "" -or $t.StartsWith("#") -or -not $t.Contains("=")) { continue }
        $k, $v = $t.Split("=", 2)
        [Environment]::SetEnvironmentVariable($k.Trim(), $v.Trim().Trim('"'), "Process")
    }
}
# The Claude key lives in the user's Windows environment (setx); only passed to this process, never printed or written.
if (-not [Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "Process")) {
    $saved = [Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
    if ($saved) { [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $saved, "Process") }
}

$dataDir = Join-Path $root "devsys\data"
New-Item -ItemType Directory -Force -Path $dataDir | Out-Null
$log = Join-Path $dataDir "devsys.log"
$errLog = Join-Path $dataDir "devsys_err.log"
Start-Process -WindowStyle Hidden -WorkingDirectory $root -FilePath "py" -RedirectStandardOutput $log -RedirectStandardError $errLog `
    -ArgumentList "-m", "streamlit", "run", "devsys/app.py", "--server.port", "$port", "--server.address", "127.0.0.1", "--server.headless", "true", "--browser.gatherUsageStats", "false"
for ($i = 0; $i -lt 40 -and -not (Test-Port $port); $i++) { Start-Sleep -Milliseconds 500 }
if (-not (Test-Port $port)) { Show-Failure "May chu chua len sau 20 giay (cong $port)."; exit 1 }
Start-Process $url
