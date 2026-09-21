# Creates ONE Desktop shortcut, "AI Video Pipeline" (starts the dashboard, or just opens it when already running).
# Windows shortcuts made through WScript.Shell cannot store non-ASCII characters (this repo's folder
# name has Vietnamese letters), so the shortcuts point through an ASCII folder junction:
#   %LOCALAPPDATA%\AIVideoPipeline  ->  <this repo>
# Re-run this script after moving the repo folder.
$root = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$link = Join-Path $env:LOCALAPPDATA "AIVideoPipeline"
if (Test-Path $link) { cmd /c rmdir "`"$link`"" | Out-Null }
cmd /c mklink /J "`"$link`"" "`"$root`"" | Out-Null
if (-not (Test-Path (Join-Path $link "dashboard\app.py"))) { Write-Host "Khong tao duoc junction $link" -ForegroundColor Red; exit 1 }

$shell = New-Object -ComObject WScript.Shell
$ps = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
function New-Link($name, $script, $icon) {
    $file = Join-Path $desktop "$name.lnk"
    $lnk = $shell.CreateShortcut($file)
    $lnk.TargetPath = $ps
    $lnk.Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$(Join-Path $link $script)`""
    $lnk.WorkingDirectory = $link
    $lnk.IconLocation = $icon
    $lnk.Save()
    Write-Host "Da tao: $file"
}
$icon = Join-Path $link "tools\logo_g.ico"   # one logo for both shortcuts
New-Link "AI Video Pipeline" "tools\launch_dashboard.ps1" $icon
# One shortcut only. Stopping is done from the dashboard itself (button "Tat Dashboard"), or Stop-Dashboard.bat.
$old = Join-Path $desktop "Tat AI Video Pipeline.lnk"
if (Test-Path $old) { Remove-Item $old -Force; Write-Host "Da xoa shortcut cu: $old" }
