@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

title VINA Studio - Cylindrical Dewarp and OCR (RTX 3090)

echo ======================================================================
echo           VINA Studio: Cylindrical Dewarp and Search System
echo ======================================================================
echo.
echo [1/2] Проверка окружения Python...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo [ОШИБКА] Python не найден в переменной PATH!
    pause
    exit /b 1
)
netstat -ano | findstr 127.0.0.1:8080 | findstr LISTENING >nul
if %ERRORLEVEL% EQU 0 (
    echo [ИНФО] Сервер VINA уже активен и слушает порт 8080!
    echo       Открываем интерфейс в браузере: http://127.0.0.1:8080
    start http://127.0.0.1:8080
    echo.
    pause
    exit /b 0
)

echo.
echo [2/2] Загрузка нейросетей в видеопамять RTX 3090...
echo       (YOLOv8-seg, SAM, PP-OCRv4, EasyOCR, SigLIP2, FAISS-каталог)
echo.
echo       Пожалуйста, подождите около 10-12 секунд.
echo       Браузер (http://127.0.0.1:8080) откроется АВТОМАТИЧЕСКИ,
echo       как только сервер будет полностью готов к работе!
echo.
echo ======================================================================
echo Для остановки сервера закройте это окно или нажмите Ctrl+C.
echo ======================================================================
echo.

python -u app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Ошибка выполнения сервера.
    pause
)

