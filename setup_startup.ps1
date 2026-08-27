param(
    [string]$Python = "py",
    [string]$ProjectDirectory = $PSScriptRoot
)

$configPath = Join-Path $ProjectDirectory "config.toml"
$taskName = "Strava2Garmin Sync"
$scriptPath = Join-Path $ProjectDirectory "sync.py"
$arguments = "`"$scriptPath`" --config `"$configPath`""
$action = New-ScheduledTaskAction -Execute $Python -Argument $arguments -WorkingDirectory $ProjectDirectory
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Description "Syncs Strava names and descriptions to Garmin." -Force | Out-Null
Write-Host "Task '$taskName' configured; the delay is read from config.toml."
