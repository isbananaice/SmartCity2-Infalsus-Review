@echo off
chcp 65001 >nul
title In Falsus AI 復盤診斷系統
echo ========================================================
echo   In Falsus AI 復盤診斷系統 - 啟動器
echo ========================================================
echo 正在啟動 In Falsus 復盤系統 GUI...
python run_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [提示] 若原生視窗未開啟，嘗試以瀏覽器模式啟動...
    python run_gui.py --browser
)
pause
