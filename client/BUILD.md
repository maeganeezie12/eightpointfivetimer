# (Optional) Building a standalone checkin_daemon.exe

Most laptops don't need this — `SETUP.md`'s default path is `git clone` + `pip install` + run `checkin_daemon.py` directly via `pythonw.exe`, since the team already has Python installed. Only build a standalone exe for a specific machine that doesn't have Python and where installing it isn't an option.

```
python -m venv build_venv
build_venv\Scripts\pip install -r requirements.txt pyinstaller
build_venv\Scripts\pyinstaller checkin_daemon.spec
```

The built exe is at `dist\checkin_daemon.exe`. Copy that plus `client_config.env.example` to `C:\WorkTimer\` on the target machine, fill in `client_config.env` per `SETUP.md`, then register its own Startup-folder shortcut manually (`install_startup.ps1` targets the `.py` path, not the exe):

```powershell
$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut("$([Environment]::GetFolderPath('Startup'))\WorkTimerCheckin.lnk")
$shortcut.TargetPath = "C:\WorkTimer\checkin_daemon.exe"
$shortcut.WorkingDirectory = "C:\WorkTimer"
$shortcut.Save()

Start-Process "C:\WorkTimer\checkin_daemon.exe"
```

`build\`, `dist\`, and `build_venv\` are all build output/tooling — gitignored, not part of the repo.
