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
    echo [OK] 检测到本地 Python 环境，正在启动云端服务引擎...
    start /b python app.py >nul 2>nul
    timeout /t 2 >nul
    echo 正在打开足迹主页 (http://localhost:5000)...
    start http://localhost:5000
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
