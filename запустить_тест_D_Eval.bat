@echo off
chcp 65001 >nul
title VINA Scanner - Финальный тест 100 бутылок (D:\Eval)
cd /d "%~dp0"

echo ======================================================================
echo           VINA Scanner: Финальная оценка точности (D:\Eval)
echo      Пайплайн: Qwen2-VL GPU + DINOv2-LoRA + SigLIP2 + Formula IF
echo ======================================================================
echo.
python test_vina_scanner.py --eval-root D:\Eval --mode http %*

echo.
pause
