# VALIOR - Registro de tareas programadas (correr como Administrador)

$projectDir = "C:\Users\Juan\Desktop\CLAUDE DL"

# --- MORNING ---
$actionMorning = New-ScheduledTaskAction `
    -Execute "$projectDir\run_morning.bat" `
    -WorkingDirectory $projectDir

$triggerMorning = New-ScheduledTaskTrigger -Daily -At "09:00AM"

$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -RestartCount 2 `
    -RestartInterval (New-TimeSpan -Minutes 15) `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest

Register-ScheduledTask `
    -TaskName "Valior Morning Pipeline" `
    -Action $actionMorning `
    -Trigger $triggerMorning `
    -Settings $settings `
    -Principal $principal `
    -Force

Write-Host "[OK] Valior Morning Pipeline registrada -> 09:00 AM diario"

# --- NIGHT ---
$actionNight = New-ScheduledTaskAction `
    -Execute "$projectDir\run_night.bat" `
    -WorkingDirectory $projectDir

$triggerNight = New-ScheduledTaskTrigger -Daily -At "11:00PM"

Register-ScheduledTask `
    -TaskName "Valior Night Pipeline" `
    -Action $actionNight `
    -Trigger $triggerNight `
    -Settings $settings `
    -Principal $principal `
    -Force

Write-Host "[OK] Valior Night Pipeline registrada -> 23:00 diario"
Write-Host ""
Write-Host "Ambas tareas corren como SYSTEM - funcionan con pantalla bloqueada."
