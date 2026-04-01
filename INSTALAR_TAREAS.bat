@echo off
:: Auto-elevacion a Administrador
NET SESSION >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Solicitando permisos de Administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

:: Ya somos admin - registrar las tareas
echo.
echo ============================================================
echo  VALIOR - Instalando tareas programadas
echo ============================================================
echo.

set PROJECT_DIR=C:\Users\Juan\Desktop\CLAUDE DL

powershell -ExecutionPolicy Bypass -Command ^
    "$projectDir = 'C:\Users\Juan\Desktop\CLAUDE DL';" ^
    "$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Hours 2) -RestartCount 2 -RestartInterval (New-TimeSpan -Minutes 15) -StartWhenAvailable -RunOnlyIfNetworkAvailable;" ^
    "$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -RunLevel Highest;" ^
    "$a1 = New-ScheduledTaskAction -Execute \"$projectDir\run_morning.bat\" -WorkingDirectory $projectDir;" ^
    "$t1 = New-ScheduledTaskTrigger -Daily -At '09:00AM';" ^
    "Register-ScheduledTask -TaskName 'Valior Morning Pipeline' -Action $a1 -Trigger $t1 -Settings $settings -Principal $principal -Force;" ^
    "$a2 = New-ScheduledTaskAction -Execute \"$projectDir\run_night.bat\" -WorkingDirectory $projectDir;" ^
    "$t2 = New-ScheduledTaskTrigger -Daily -At '11:00PM';" ^
    "Register-ScheduledTask -TaskName 'Valior Night Pipeline' -Action $a2 -Trigger $t2 -Settings $settings -Principal $principal -Force;" ^
    "Write-Host '[OK] Tareas instaladas correctamente'"

echo.
echo ============================================================
echo  Tareas registradas:
echo   - Valior Morning Pipeline  ->  09:00 AM diario
echo   - Valior Night Pipeline    ->  23:00 diario
echo.
echo  Ambas corren como SYSTEM.
echo  Funcionan con pantalla bloqueada y sin sesion abierta.
echo ============================================================
echo.
pause
