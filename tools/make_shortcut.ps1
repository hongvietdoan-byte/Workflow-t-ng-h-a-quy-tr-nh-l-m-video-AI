# Creates Desktop shortcuts: "AI Video Pipeline" (start) and "Tat AI Video Pipeline" (stop).
$root = Split-Path -Parent $PSScriptRoot
$desktop = [Environment]::GetFolderPath("Desktop")
$shell = New-Object -ComObject WScript.Shell
function New-Link($name, $target, $icon) {
    $lnk = $shell.CreateShortcut((Join-Path $desktop "$name.lnk"))
    $lnk.TargetPath = $target
    $lnk.WorkingDirectory = $root
    $lnk.IconLocation = $icon
    $lnk.WindowStyle = 7
    $lnk.Save()
    Write-Host "Da tao: $desktop\$name.lnk"
}
New-Link "AI Video Pipeline" (Join-Path $root "Start-Dashboard.bat") (Join-Path $PSScriptRoot "icon.ico")
New-Link "Tat AI Video Pipeline" (Join-Path $root "Stop-Dashboard.bat") "shell32.dll,131"
