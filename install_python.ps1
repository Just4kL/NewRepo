# install_python.ps1
$ErrorActionPreference = "Stop"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "   Установка Python для Steam Playtime Viewer" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$pythonVersion = "3.12.4"
$installPath = "$env:LOCALAPPDATA\Programs\Python\Python312"
$installerUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-amd64.exe"
$installerPath = "$env:TEMP\python-installer.exe"

Write-Host "Python не найден в системе." -ForegroundColor Yellow
Write-Host ""
Write-Host "Предлагаем установить Python $pythonVersion" -ForegroundColor White
Write-Host "Путь установки: $installPath" -ForegroundColor Gray
Write-Host ""

$response = Read-Host "Установить Python? (Y/N)"

if ($response -eq "Y" -or $response -eq "y") {
    Write-Host ""
    Write-Host "Скачивание установщика..." -ForegroundColor Cyan
    
    try {
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -ErrorAction Stop
    } catch {
        Write-Host "Ошибка скачивания: $_" -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
    
    Write-Host "Установка Python..." -ForegroundColor Cyan
    
    Start-Process -FilePath $installerPath -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_test=0", "TargetDir=$installPath" -Wait
    
    if (Test-Path "$installPath\python.exe") {
        Write-Host "Python успешно установлен!" -ForegroundColor Green
        
        # Установка зависимостей
        Write-Host "Установка зависимостей..." -ForegroundColor Cyan
        & "$installPath\python.exe" -m pip install --upgrade pip
        & "$installPath\python.exe" -m pip install PyQt5 aiohttp qasync openpyxl
        
        Write-Host "Готово!" -ForegroundColor Green
    } else {
        Write-Host "Ошибка установки Python." -ForegroundColor Red
        Read-Host "Нажмите Enter для выхода"
        exit 1
    }
    
    # Очистка
    Remove-Item $installerPath -ErrorAction SilentlyContinue
} else {
    Write-Host "Установка отменена." -ForegroundColor Yellow
    Write-Host "Установите Python вручную с https://python.org" -ForegroundColor White
    Read-Host "Нажмите Enter для выхода"
    exit 1
}