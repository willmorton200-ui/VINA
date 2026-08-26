@echo off
chcp 65001 > nul
cls
echo ==================================================================
echo   VINA Studio: Пакетная обработка всего датасета бутылок
echo ==================================================================
echo.
echo Запуск сквозной обработки всех изображений из test_dataset/butilki...
echo.

cd /d "%~dp0"

python run_pipeline.py --input_dir test_dataset/butilki --output_dir outputs/batch_all_bottles --save_intermediate True

echo.
echo ==================================================================
echo   Обработка завершена!
echo   Результаты сохранены в: D:\VINA\outputs\batch_all_bottles
echo ==================================================================
echo.

start "" "outputs\batch_all_bottles"
pause
