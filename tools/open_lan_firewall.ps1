# Opens the Dashboard port (8501) in Windows Firewall so other computers on the company network can use it.
# Needs Administrator ONCE: the rule is permanent (it survives restarts). Run through Open-LAN-Access.bat (asks for admin itself).
# Scope: Domain + Private networks only, and only from private address ranges (10.x, 172.16-31.x, 192.168.x): not from the internet.
$ErrorActionPreference = "Stop"
$port = if ($env:DASHBOARD_PORT) { [int]$env:DASHBOARD_PORT } else { 8501 }
$name = "AI Video Pipeline Dashboard (LAN)"
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Can chay bang quyen Administrator (Run as administrator)." -ForegroundColor Red
    exit 1
}
Get-NetFirewallRule -DisplayName $name -ErrorAction SilentlyContinue | Remove-NetFirewallRule
New-NetFirewallRule -DisplayName $name -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port `
    -Profile Domain,Private -RemoteAddress "10.0.0.0/8","172.16.0.0/12","192.168.0.0/16" | Out-Null
$ips = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.254.*" }
Write-Host ""
Write-Host "Da mo cong $port cho mang noi bo. Gui link nay cho dong nghiep:" -ForegroundColor Green
foreach ($ip in $ips) { Write-Host ("  http://{0}:{1}" -f $ip.IPAddress, $port) }
Write-Host ("  http://{0}:{1}   (theo ten may)" -f $env:COMPUTERNAME, $port)
Write-Host ""
Write-Host "Luu y: may nay phai bat va Dashboard dang chay (Start-Dashboard.bat)."
