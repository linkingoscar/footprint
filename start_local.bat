@echo off
chcp 65001 >nul
title Footprint · Local Desktop Launcher

echo ========================================================
echo         🧭 Footprint · Standalone Desktop Launcher
echo ========================================================
echo.
echo Checking local environment...

where python >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] Python detected, starting backend server...
    start /b python app.py >nul 2>nul
    timeout /t 2 >nul
    echo Opening Footprint (http://localhost:5000)...
    start http://localhost:5000
) else (
    echo [Notice] Python not found. Launching in 100% Offline Local Desktop Mode!
    echo All photos and data will be safely stored in your local browser storage.
    echo Opening Footprint...
    start "" "%~dp0frontend\index.html"
)

echo.
echo ========================================================
echo      Footprint is ready! Enjoy logging your life.
echo ========================================================
timeout /t 5 >nul
exit
