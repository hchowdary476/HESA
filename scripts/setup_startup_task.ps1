param()
#Requires -Version 5.1
<#
.SYNOPSIS
    JARVIS AutoStart — Zero-Touch Setup

.DESCRIPTION
    Registers JARVIS to auto-start silently at Windows logon using:
    1. HKCU Registry Run key (primary, works without admin)
    2. Task Scheduler (optional, if no conflicting admin task exists)

    Both methods use pythonw.exe — no CMD window, no console flash.
    The HKCU Run key requires ZERO admin rights.

.NOTES
    ONE-TIME ADMIN CLEANUP (only needed if you previously ran create_task.ps1
    or setup_startup_task.ps1 as Administrator):

    Run this in an elevated PowerShell:
        Unregister-ScheduledTask -TaskName "JARVIS Auto Start" -Confirm:$false
        Unregister-ScheduledTask -TaskName "JARVIS_AutoLaunch" -Confirm:$false

    After that, re-run this script normally and Task Scheduler will also be registered.
#>

$ErrorActionPreference = "Continue"

# Dynamic path resolution - no hardcoded user paths
$scriptDir   = $PSScriptRoot
$projectRoot = Split-Path $scriptDir -Parent
$pythonwExe  = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
$entryPoint  = Join-Path $projectRoot "jarvis.py"
$taskName    = "JARVIS_SilentBoot"
$regKeyName  = "JARVIS_SilentBoot"
$regPath     = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

Write-Host "================================================="
Write-Host "  JARVIS Zero-Touch AutoStart Setup"
Write-Host "================================================="
Write-Host "  Project root : $projectRoot"
Write-Host "  pythonw.exe  : $pythonwExe"
Write-Host "  Entry point  : $entryPoint"
Write-Host ""

# Pre-flight checks
if (-not (Test-Path $pythonwExe)) {
    Write-Error "pythonw.exe not found at: $pythonwExe - Recreate the virtual environment first."
    exit 1
}
if (-not (Test-Path $entryPoint)) {
    Write-Error "Entry point not found: $entryPoint"
    exit 1
}

# ── METHOD 1: HKCU Registry Run key (no admin needed, always works) ───────────
Write-Host "--- Method 1: Registry Run key (no admin required) ---"
$runValue = '"{0}" "{1}"' -f $pythonwExe, $entryPoint
try {
    Set-ItemProperty -Path $regPath -Name $regKeyName -Value $runValue -Type String -ErrorAction Stop
    Write-Host "[OK] Registry key set: HKCU\...\Run\$regKeyName"
    Write-Host "     Value: $runValue"
} catch {
    Write-Warning "Failed to set registry key: $($_.Exception.Message)"
}

Write-Host ""

# ── METHOD 2: Task Scheduler (provides retry-on-failure, 15s delay) ────────────
Write-Host "--- Method 2: Task Scheduler (enhanced reliability) ---"

# Remove old keys that don't conflict
$safeRemoveTasks = @("JARVIS_SilentBoot", "JARVIS_AutoStart")
foreach ($t in $safeRemoveTasks) {
    if (Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue) {
        try {
            Unregister-ScheduledTask -TaskName $t -Confirm:$false -ErrorAction Stop
            Write-Host "Removed old task: $t"
        } catch {
            Write-Warning "Could not remove '$t': $($_.Exception.Message)"
        }
    }
}

# Remove old registry Run keys from previous setups
foreach ($key in @("JARVIS", "JARVIS_AutoLaunch")) {
    if (Get-ItemProperty -Path $regPath -Name $key -ErrorAction SilentlyContinue) {
        try {
            Remove-ItemProperty -Path $regPath -Name $key -Force
            Write-Host "Removed old registry key: $key"
        } catch {}
    }
}

# Remove old Startup folder shortcut
$startupLnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\JARVIS.lnk"
if (Test-Path $startupLnk) {
    Remove-Item $startupLnk -Force -ErrorAction SilentlyContinue
    Write-Host "Removed startup folder shortcut"
}

# Build Task Scheduler task
$action = New-ScheduledTaskAction `
    -Execute          $pythonwExe `
    -Argument         ('"{0}"' -f $entryPoint) `
    -WorkingDirectory $projectRoot

$trigger = New-ScheduledTaskTrigger -AtLogOn
$trigger.Delay = "PT15S"

$principal = New-ScheduledTaskPrincipal `
    -UserId    $env:USERNAME `
    -LogonType Interactive `
    -RunLevel  Limited

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances  IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 0) `
    -RestartCount       3 `
    -RestartInterval    (New-TimeSpan -Minutes 2)

try {
    Register-ScheduledTask `
        -TaskName   $taskName `
        -Action     $action `
        -Trigger    $trigger `
        -Principal  $principal `
        -Settings   $settings `
        -Description "JARVIS AI - silent auto-start at logon (pythonw, no UAC, no CMD)" `
        -Force -ErrorAction Stop | Out-Null

    Write-Host "[OK] Task Scheduler task registered: $taskName"
    Write-Host "[OK] Trigger : At logon of $env:USERNAME (delay 15s)"
    Write-Host "[OK] Retry   : 3x every 2 minutes on failure"
    schtasks /query /tn $taskName /fo LIST 2>&1 | Where-Object { $_ -match "(TaskName|Status|Run As|Next Run)" }
} catch {
    Write-Warning "Task Scheduler registration failed: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "  *** IMPORTANT: If you see 'Access is denied', an old admin-elevated task"
    Write-Host "  *** is blocking registration. Run these commands in an ELEVATED PowerShell:"
    Write-Host ""
    Write-Host "      Unregister-ScheduledTask -TaskName 'JARVIS Auto Start' -Confirm:`$false"
    Write-Host "      Unregister-ScheduledTask -TaskName 'JARVIS_AutoLaunch'  -Confirm:`$false"
    Write-Host ""
    Write-Host "  Then re-run this script normally."
    Write-Host ""
    Write-Host "  [NOTE] The HKCU Registry Run key (Method 1) IS already active and will"
    Write-Host "         launch JARVIS silently at logon regardless."
}

Write-Host ""
Write-Host "================================================="
Write-Host "  Setup complete. Summary:"
Write-Host ""
$regVal = Get-ItemProperty -Path $regPath -Name $regKeyName -ErrorAction SilentlyContinue
if ($regVal) {
    Write-Host "  [ACTIVE] Registry Run key: $regKeyName"
} else {
    Write-Host "  [MISSING] Registry Run key not set!"
}
$taskExists = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($taskExists) {
    Write-Host "  [ACTIVE] Task Scheduler: $taskName"
} else {
    Write-Host "  [SKIPPED] Task Scheduler (see admin note above)"
}
Write-Host ""
Write-Host "  JARVIS will auto-start silently at your next logon."
Write-Host "================================================="
