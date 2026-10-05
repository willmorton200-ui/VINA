@echo off
chcp 65001 >nul
title VINA Scanner - Тест на папке D:\Eval
cd /d "%~dp0"

echo ======================================================================
echo           VINA Scanner: Оценка точности (D:\Eval)
echo ======================================================================
echo.
python test_vina_scanner.py --eval-root D:\Eval --mode http %*

echo.
pause
