@echo off
chcp 65001 >nul
title Тест VINA Scanner - Прогон 1 (27 каталожных фото)
cd /d "%~dp0"

echo ======================================================================
echo           VINA SCANNER: ПРОГОН 1 (27 каталожных фото)
echo ======================================================================
echo.

python test_vina_scanner.py --run 1 --mode http %*

echo.
pause
