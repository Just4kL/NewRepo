@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

title Steam Playtime Viewer - Launcher

echo ============================================
echo    Steam Playtime Viewer - Запуск
echo ============================================
echo.

cd /d "%~dp0"

:: Выбор интерпретатора: сначала conda с зависимостями, иначе py
set "PYBIN=py"
if exist "C:\Users\Kenig\miniconda3\python.exe" set "PYBIN=C:\Users\Kenig\miniconda3\python.exe"

:: Проверка Python
%PYBIN% --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден.
    pause
    exit /b 1
)

:: Запуск с сохранением ошибок
echo Запуск приложения...
echo.

%PYBIN% -m main 2>&1 | findstr /C:"Traceback" >nul
if not errorlevel 1 (
    echo.
    echo [ОШИБКА] Обнаружена ошибка. Сохраняем traceback...

    :: Создаём папку logs если нет
    if not exist logs mkdir logs

    :: Сохраняем traceback
    set "LOGFILE=logs\error_%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%.log"
    %PYBIN% -m main 2> "!LOGFILE!"

    echo.
    echo Ошибка сохранена в: !LOGFILE!
    pause
    exit /b 1
)

echo.
echo Приложение успешно закрыто.
timeout /t 2 >nul
exit /b 0