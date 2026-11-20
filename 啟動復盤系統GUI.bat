@echo off
chcp 65001 >nul
title In Falsus AI 復盤診斷系統 (本地版)
echo ========================================================
echo   In Falsus AI 復盤診斷系統 (本地桌面版)
echo   完全離線運作 | GPU 硬體加速 | 無需任何網路伺服器
echo ========================================================
echo 正在啟動 In Falsus 復盤系統桌面應用程式...
python run_gui.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [錯誤] 啟動失敗，請確認已安裝相依套件 (pip install pywebview)。
    pause
)
