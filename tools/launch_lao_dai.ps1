# Lão Đại chỉ đọc. Không nạp dashboard.env, không truyền session/token qua CLI/env.
param([switch]$Demo, [ValidatePattern('^[A-Za-z0-9_-]{1,80}$')][string]$QaName='manual',
      [ValidateSet('idle','tickets','disconnected')][string]$DemoState='idle')
$ErrorActionPreference='Stop'
$petRoot=(Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw 'Cần Python Windows (py).' }
& py -c 'import tkinter, win32gui, win32cred, win32com.propsys.propsys'
if ($LASTEXITCODE -ne 0) { throw 'Thiếu tkinter hoặc pywin32; launcher không tự cài thư viện.' }
$petArgs=@('-m','tools.lao_dai.gui')
if ($Demo) { $petArgs+=@('--demo','--qa-name',$QaName,'--demo-state',$DemoState) }
Start-Process -FilePath 'py' -ArgumentList $petArgs -WorkingDirectory $petRoot -WindowStyle Hidden
