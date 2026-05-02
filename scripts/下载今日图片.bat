@echo off
chcp 65001 >nul
echo 正在下载今日候选图片...
cd /d "%~dp0.."
python scripts\download_images.py 2026-04-29
echo.
echo 完成！按任意键退出
pause >nul
