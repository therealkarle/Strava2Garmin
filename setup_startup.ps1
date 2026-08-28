param(
    [string]$Python = "py",
    [string]$ProjectDirectory = $PSScriptRoot
)

$principal = [Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    $elevationArguments = @(
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", "`"$PSCommandPath`"",
        "-Python", "`"$Python`"",
        "-ProjectDirectory", "`"$ProjectDirectory`""
    )

    try {
        Start-Process -FilePath (Get-Process -Id $PID).Path -Verb RunAs -ArgumentList $elevationArguments
    }
    catch {
        Write-Error "Administrator approval was not granted."
    }
    return
}

$taskName = "Strava2Garmin Sync"
$scriptPath = Join-Path $ProjectDirectory "startup_launcher.py"
$arguments = "`"$scriptPath`""
$action = New-ScheduledTaskAction -Execute $Python -Argument $arguments -WorkingDirectory $ProjectDirectory
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description "Syncs Strava names and descriptions to Garmin." -Force | Out-Null
Write-Host "Task '$taskName' configured; startup_launcher.py reads the delay from config.toml."
