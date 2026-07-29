# Registers checkin_daemon.py to auto-start at logon via the per-user Startup
# folder — no admin rights or Task Scheduler permissions needed. Run this from
# the client/ folder after `pip install -r requirements.txt`.

$pythonwCmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
if (-not $pythonwCmd) {
    Write-Error "pythonw.exe not found on PATH. Make sure Python is installed and added to PATH, then try again."
    exit 1
}
$pythonw = $pythonwCmd.Source
$scriptPath = "$PSScriptRoot\checkin_daemon.py"

$WshShell = New-Object -ComObject WScript.Shell
$startupFolder = [Environment]::GetFolderPath('Startup')
$shortcut = $WshShell.CreateShortcut("$startupFolder\WorkTimerCheckin.lnk")
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "`"$scriptPath`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Save()

Write-Host "Startup shortcut created: $startupFolder\WorkTimerCheckin.lnk"
Write-Host "It will run automatically at your next logon. To start it right now:"
Write-Host "  & `"$pythonw`" `"$scriptPath`""
