@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Steam Playtime Viewer - Launcher

cd /d "%~dp0"

:: Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    powershell -ExecutionPolicy Bypass -File "%~dp0install_python.ps1"
    if errorlevel 1 exit /b 1
)

:: Запуск
py -m main || python -m main
pause