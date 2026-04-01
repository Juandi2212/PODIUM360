@echo off
:: ============================================================
:: VALIOR - Actualizacion Nocturna (ROI)
:: Corre diariamente a las 23:00 via Task Scheduler
:: ============================================================

set PROJECT_DIR=C:\Users\Juan\Desktop\CLAUDE DL
set PYTHON=C:\Users\Juan\AppData\Local\Python\bin\python.exe
set LOG_DIR=%PROJECT_DIR%\logs
set LOG_FILE=%LOG_DIR%\night_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%.log

:: Crear carpeta de logs si no existe
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Cambiar al directorio del proyecto
cd /d "%PROJECT_DIR%"

echo ============================================================ >> "%LOG_FILE%"
echo VALIOR Night Pipeline - %DATE% %TIME% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: Correr la actualizacion nocturna y guardar log
"%PYTHON%" master_night.py >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Actualizacion nocturna fallo con codigo %ERRORLEVEL% >> "%LOG_FILE%"
    echo FALLO - Ver logs\night_*.log para detalles
    exit /b %ERRORLEVEL%
)

echo [OK] Actualizacion nocturna completada exitosamente >> "%LOG_FILE%"
