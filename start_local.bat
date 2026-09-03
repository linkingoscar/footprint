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
    start "Footprint Server" /b python -m backend.app
    echo Waiting for service to be ready...
    powershell -Command "for ($i=0; $i -lt 10; $i++) { try { $r = Invoke-WebRequest -Uri 'http://localhost:5000/api/health' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Server is ready! Opening Footprint (http://localhost:5000)...
        start http://localhost:5000
    ) else (
        echo [Error] Server health check timed out. The backend server failed to start!
        echo Please inspect your terminal or test startup manually by running:
        echo   python app.py
        echo.
        pause
        exit /b 1
    )
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
