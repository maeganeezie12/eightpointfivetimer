# Registers checkin_daemon.exe to auto-start at logon via the per-user Startup
# folder — no admin rights or Task Scheduler permissions needed. Run this from
# the same folder as checkin_daemon.exe.

$WshShell = New-Object -ComObject WScript.Shell
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcut = $WshShell.CreateShortcut("$startupFolder\WorkTimerCheckin.lnk")
$shortcut.TargetPath = "$PSScriptRoot\checkin_daemon.exe"
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Save()

Write-Host "Startup shortcut created: $startupFolder\WorkTimerCheckin.lnk"
Write-Host "It will run automatically at your next logon. To start it right now:"
Write-Host "  Start-Process `"$PSScriptRoot\checkin_daemon.exe`""
