@echo off
setlocal
cd /d "%~dp0"

title VINA - Cloudflare Tunnel Bridge

echo ======================================================================
echo           VINA: Cloudflare Tunnel Bridge to RTX 3090
echo ======================================================================
echo.
echo [1/2] Checking local backend (http://127.0.0.1:8080)...
echo Make sure "start_app.bat" or "python app.py" is running!
echo.
echo [2/2] Starting secure HTTPS tunnel...
echo.
echo ======================================================================
echo  Look for the HTTPS link below (e.g., https://xxxx.trycloudflare.com):
echo  Copy that URL and paste it in the web scanner (Settings icon).
echo ======================================================================
echo.

.\bin\cloudflared.exe tunnel --url http://127.0.0.1:8080

pause
