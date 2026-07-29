# Coworker laptop setup

Per person, once you've provisioned them on the server (`provision.py add "Their Name"` — see the repo root), do this on their laptop. No Python or pip install needed — it's a standalone `.exe`.

This uses a Startup-folder shortcut rather than Windows Task Scheduler, since many company-managed laptops restrict standard users from registering scheduled tasks (`schtasks /create` fails with "Access is denied"). A Startup-folder shortcut lives entirely in the user's own profile and needs no special permissions.

## 1. Copy files

Create `C:\WorkTimer\` and copy in:
- `checkin_daemon.exe` (built from `checkin_daemon.py` — see `BUILD.md`)
- `client_config.env.example` — rename to `client_config.env` and fill in their `AUTH_TOKEN` (and `SERVER_URL` if different from the default)
- `install_startup.ps1`

## 2. Register it to start automatically

From a normal PowerShell prompt (no admin rights needed):

```powershell
cd C:\WorkTimer
.\install_startup.ps1
```

This creates a shortcut in `shell:startup` pointing at `checkin_daemon.exe`. It'll launch automatically at every logon from now on.

## 3. Start it now (don't wait for the next logon)

```powershell
Start-Process "C:\WorkTimer\checkin_daemon.exe"
```

It then runs continuously in the background: once at startup (covering a fresh logon after a full shutdown), and afterwards it polls every 60 seconds watching for a large gap in elapsed time, which is how it detects the laptop resumed from sleep. Either way, it only actually posts a checkin if the local time is between 08:00 and 11:00 and it hasn't already checked in that day — outside that window, or after the day's checkin is done, it just logs and does nothing.

## 4. Verify

- Check `C:\WorkTimer\checkin_client.log` for a line confirming success, or the reason it skipped.
- Check the dashboard at `http://192.119.82.215:8000/` for their name and a live countdown.

## To stop it

```powershell
Get-Process checkin_daemon | Stop-Process
Remove-Item "$([Environment]::GetFolderPath('Startup'))\WorkTimerCheckin.lnk"
```
