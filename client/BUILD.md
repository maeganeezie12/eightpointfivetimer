# Building checkin_daemon.exe

You only need to do this once (or whenever `checkin_daemon.py` changes) — the same `.exe` is copied to every coworker's laptop, only `client_config.env` differs per person.

```
python -m venv build_venv
build_venv\Scripts\pip install -r requirements.txt pyinstaller
build_venv\Scripts\pyinstaller checkin_daemon.spec
```

The built exe is at `dist\checkin_daemon.exe`. Copy that (plus `client_config.env.example` and `install_startup.ps1`) per `SETUP.md`.

`build\`, `dist\`, and `build_venv\` are all build output/tooling — gitignored, not part of the distributed app.
