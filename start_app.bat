@echo off
setlocal
cd /d "%~dp0"

title VINA Studio - Cylindrical Dewarp and OCR

echo ======================================================================
echo           VINA Studio: Cylindrical Dewarp and OCR System
echo ======================================================================
echo.
echo [1/2] Starting FastAPI server on http://127.0.0.1:8000 ...
echo [2/2] Opening browser automatically...
echo.
echo To stop the server, press Ctrl+C or close this window.
echo ======================================================================
echo.

python app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to start server. Please check Python environment.
    pause
)
