@echo off
title TCBS Token Updater
echo --- TCBS Token Update Shortcut ---
echo.
cd /d "%~dp0"
"%~dp0venv\Scripts\python.exe" fetch_tcbs_token.py
echo.
echo Press any key to close this window...
pause >nul
