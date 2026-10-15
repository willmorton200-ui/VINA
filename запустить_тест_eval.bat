@echo off
chcp 65001 >nul
title Тест VINA Scanner - Контрольный пакет Eval (100 бутылок)
cd /d "%~dp0"

echo ======================================================================
echo           VINA SCANNER: КОНТРОЛЬНЫЙ ТЕСТ EVAL (100 бутылок)
echo ======================================================================
echo.

python test_vina_scanner.py --run eval --mode http %*

echo.
pause
