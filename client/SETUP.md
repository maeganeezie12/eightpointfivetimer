# Coworker laptop setup

Per person, once you've provisioned them on the server (`provision.py add "Their Name"` — see the repo root), do this on their laptop. They need Python installed (already the case for this team) — everything else comes straight from git, no separate file transfer needed.

This uses a Startup-folder shortcut rather than Windows Task Scheduler, since many company-managed laptops restrict standard users from registering scheduled tasks (`schtasks /create` fails with "Access is denied"). A Startup-folder shortcut lives entirely in the user's own profile and needs no special permissions.

## 1. Get the code and install dependencies

```powershell
git clone https://github.com/maeganeezie12/eightpointfivetimer.git
cd eightpointfivetimer\client
pip install -r requirements.txt
```

## 2. Configure it

Copy `client_config.env.example` to `client_config.env` in the same `client\` folder, and fill in their `PASSWORD` (and `SERVER_URL` if different from the default).

## 3. Register it to start automatically

From a normal PowerShell prompt (no admin rights needed), from inside `client\`:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_startup.ps1
```

(Just running `.\install_startup.ps1` directly often fails with `running scripts is disabled on this system` — that's PowerShell's script-execution policy, commonly locked down on company-managed laptops. The `-ExecutionPolicy Bypass -File` form only bypasses it for this one run, no admin rights or permanent setting change needed.)

This creates a shortcut in `shell:startup` that runs `checkin_daemon.py` via `pythonw.exe` (no console window). It'll launch automatically at every logon from now on.

## 4. Start it now (don't wait for the next logon)

```powershell
Start-Process pythonw.exe -ArgumentList "checkin_daemon.py"
```

It then runs continuously in the background: once at startup (covering a fresh logon after a full shutdown), and afterwards it watches for the first sign of activity after being idle 2+ hours — that's the "just got back to your desk" signal, whether the laptop actually went into a real sleep state or just sat locked while staying powered on (many company-managed laptops do the latter, in which case a sleep-detection approach based on elapsed-time gaps never fires at all). Either way, it only actually posts a checkin if the local time is between 08:00 and 11:00 and it hasn't already checked in that day — outside that window, or after the day's checkin is done, it just logs and does nothing.

The activity signal is deliberately keyboard-first, not mouse — a mouse can get bumped by someone walking past a desk, a key press is a much stronger signal. It's installed via a low-level keyboard hook (the `keyboard` package), which only ever looks at *timing* of key presses, never which keys were pressed. Some corporate endpoint security software may flag or silently filter low-level keyboard hooks regardless of intent, the same way `schtasks` got blocked — so a second, independent signal (Windows' own combined mouse+keyboard idle-time API) always runs alongside it, and whichever detects activity first wins. If the keyboard hook is blocked, detection just quietly degrades to mouse+keyboard instead of failing outright. Check `checkin_client.log` at startup for a line confirming whether the keyboard hook installed.

## 5. Verify

- Check `checkin_client.log` (in the `client\` folder) for a line confirming success, or the reason it skipped.
- Check the dashboard at `http://192.119.82.215:8000/` for their name and a live countdown.

## To update later

```powershell
cd eightpointfivetimer\client
git pull
pip install -r requirements.txt
```
The running daemon needs a restart (stop it per below, then start it again) to pick up code changes — it doesn't reload itself.

## To stop it

```powershell
Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" |
  Where-Object { $_.CommandLine -like "*checkin_daemon.py*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Remove-Item "$([Environment]::GetFolderPath('Startup'))\WorkTimerCheckin.lnk"
```
(Filtering by command line, rather than just the process name, avoids accidentally killing an unrelated `pythonw.exe` process.)

## Building a standalone .exe instead

If a particular machine doesn't have Python, see `BUILD.md` for packaging `checkin_daemon.py` into a standalone `.exe` instead — same behavior, just a different distribution method for that one machine.
