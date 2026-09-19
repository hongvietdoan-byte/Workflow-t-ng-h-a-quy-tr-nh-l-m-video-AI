@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\stop_dashboard.ps1"
timeout /t 2 >nul
