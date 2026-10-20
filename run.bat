@echo off
REM Run from source without building. Asks for Administrator itself.
setlocal
cd /d "%~dp0"
python main.py
if errorlevel 1 pause
