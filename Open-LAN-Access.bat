@echo off
rem Double-click once: asks for administrator rights, then opens the Dashboard port for the company network.
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -NoExit -File \"%~dp0tools\open_lan_firewall.ps1\"'"
