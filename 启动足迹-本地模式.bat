@echo off
chcp 65001 >nul
title 足迹 Footprint · 本地启动器

echo ========================================================
echo         🧭 足迹 Footprint · 本地免安装桌面启动器
echo ========================================================
echo.
echo 正在检查本地环境...

where python >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] 检测到本地 Python 环境，正在启动服务引擎...
    start "Footprint Server" /b python -m backend.app
    echo 等待服务就绪...
    powershell -Command "for ($i=0; $i -lt 10; $i++) { try { $r = Invoke-WebRequest -Uri 'http://localhost:5000/api/health' -UseBasicParsing -TimeoutSec 1; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1" >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] 服务启动成功！正在打开足迹主页 (http://localhost:5000)...
        start http://localhost:5000
    ) else (
        echo [提示] 服务初始化较慢或遇阻，正在尝试打开足迹主页...
        start http://localhost:5000
    )
) else (
    echo [提示] 本地未安装 Python，将直接以【纯本地桌面离线应用】模式启动！
    echo 你的所有照片与足迹数据将 100% 安全保存在本机浏览器中。
    echo 正在打开足迹主页...
    start "" "%~dp0frontend\index.html"
)

echo.
echo ========================================================
echo      足迹已就绪！你可以随时在浏览器中记录旅行与美食。
echo ========================================================
timeout /t 5 >nul
exit
