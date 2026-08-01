$ErrorActionPreference = "Stop"

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

$batPath = Join-Path $scriptDir "run_jarvis_startup.bat"
$taskName = "JARVIS_AutoLaunch"

try {
    # Remove existing task if present (ignore errors if not found)
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    # Action: run the bat via cmd so it gets a proper desktop session
    $Action = New-ScheduledTaskAction `
        -Execute "cmd.exe" `
        -Argument "/c `"$batPath`"" `
        -WorkingDirectory $scriptDir

    # Trigger: at logon, with 30-second delay for system to stabilize
    $Trigger = New-ScheduledTaskTrigger -AtLogOn
    $Trigger.Delay = "PT30S"

    # Principal: run as current user in interactive session (REQUIRED for GUI window)
    # RunLevel LeastPrivilege avoids the UAC elevation that blocks GUI display
    $Principal = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" `
        -LogonType Interactive `
        -RunLevel Limited

    # Settings: no duplicate instances, auto-restart on failure
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -ExecutionTimeLimit 0 `
        -MultipleInstances IgnoreNew `
        -RestartCount 2 `
        -RestartInterval (New-TimeSpan -Minutes 1)

    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Description "JARVIS GUI Auto-Launch at Logon (PySide6/QML)" `
        -Force

    Write-Host "SUCCESS: Task '$taskName' created/updated."
    Write-Host ""
    schtasks /query /tn $taskName /fo LIST

} catch {
    Write-Host "FAILED: $_"
    Write-Host ""
    Write-Host "Note: Run this script as Administrator if Task Scheduler access is denied."
    Write-Host "The Registry Run key (already set) is the fallback startup mechanism."
}
