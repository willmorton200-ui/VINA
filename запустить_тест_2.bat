@echo off
chcp 65001 >nul
title Тест VINA Scanner - Прогон 2 (25 сложных полевых фото)
cd /d "%~dp0"

echo ======================================================================
echo           VINA SCANNER: ПРОГОН 2 (25 сложных полевых фото)
echo ======================================================================
echo.

python test_vina_scanner.py --run 2 --mode http %*

echo.
pause
