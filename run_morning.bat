@echo off
:: ============================================================
:: VALIOR - Pipeline Matutino
:: Corre diariamente a las 09:00 AM via Task Scheduler
:: ============================================================

set PROJECT_DIR=C:\Users\Juan\Desktop\CLAUDE DL
set PYTHON=C:\Users\Juan\AppData\Local\Python\bin\python.exe
set LOG_DIR=%PROJECT_DIR%\logs
set LOG_FILE=%LOG_DIR%\morning_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%.log

:: Crear carpeta de logs si no existe
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Cambiar al directorio del proyecto
cd /d "%PROJECT_DIR%"

echo ============================================================ >> "%LOG_FILE%"
echo VALIOR Morning Pipeline - %DATE% %TIME% >> "%LOG_FILE%"
echo ============================================================ >> "%LOG_FILE%"

:: Correr el pipeline matutino y guardar log
"%PYTHON%" master_morning.py >> "%LOG_FILE%" 2>&1

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Pipeline matutino fallo con codigo %ERRORLEVEL% >> "%LOG_FILE%"
    echo FALLO - Ver logs\morning_*.log para detalles
    exit /b %ERRORLEVEL%
)

echo [OK] Pipeline matutino completado exitosamente >> "%LOG_FILE%"
