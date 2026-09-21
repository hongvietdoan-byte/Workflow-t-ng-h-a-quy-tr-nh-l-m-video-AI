' Starts launch_dashboard.ps1 with no console window at all (a PowerShell shortcut flashes a black window; this does not).
Set fso = CreateObject("Scripting.FileSystemObject")
here = fso.GetParentFolderName(WScript.ScriptFullName)
cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & here & "\launch_dashboard.ps1"""
CreateObject("WScript.Shell").Run cmd, 0, False
