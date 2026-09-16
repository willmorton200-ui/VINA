@echo off
setlocal
cd /d "%~dp0"

title VINA Studio - Cylindrical Dewarp and OCR (RSHB.Tsifra)

echo ======================================================================
echo           VINA Studio: Cylindrical Dewarp and Search System
echo ======================================================================
echo.
echo [1/2] Starting FastAPI server on http://127.0.0.1:8080 ...
echo [2/2] Opening browser automatically:
echo       - Main Studio:    http://127.0.0.1:8080/
echo       - Mobile Scanner: http://127.0.0.1:8080/scanner
echo       - Remote Access:  Run "start_tunnel.bat" to share with mobile phones
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
