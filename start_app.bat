@echo off
setlocal
cd /d "%~dp0"

title VINA Studio - Cylindrical Dewarp and OCR (RTX 3090)

echo ======================================================================
echo           VINA Studio: Cylindrical Dewarp and Search System
echo ======================================================================
echo.

rem Check if port 8080 is already active
netstat -ano | findstr 127.0.0.1:8080 | findstr LISTENING >nul
if %ERRORLEVEL% EQU 0 (
    echo [INFO] VINA server is already active on http://127.0.0.1:8080
    echo Opening browser...
    start http://127.0.0.1:8080
    echo.
    pause
    exit /b 0
)

echo [1/2] Checking Python environment...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in PATH!
    pause
    exit /b 1
)

echo.
echo [2/2] Loading neural networks into RTX 3090 VRAM...
echo       YOLOv8-seg, SAM, PP-OCRv4, EasyOCR, SigLIP2, FAISS catalog
echo.
echo       Please wait 8-10 seconds.
echo       The browser (http://127.0.0.1:8080) will open AUTOMATICALLY
echo       as soon as the server is ready!
echo.
echo ======================================================================
echo To stop the server, press Ctrl+C or close this window.
echo ======================================================================
echo.

python -u app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Server terminated with error.
    pause
)
