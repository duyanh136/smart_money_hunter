@echo off
pushd "%~dp0"
echo Starting TCBS Config Setup...
"%~dp0venv\Scripts\python.exe" setup_tcbs_config.py
echo.
pause
