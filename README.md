# eightpointfivetimer

Multi-user work-timer check-in system. Each person's laptop automatically posts a check-in when it wakes from sleep (or on logon) between 08:00–11:00, and a shared web dashboard shows everyone's live countdown to the end of their shift.

## Layout

- Repo root — FastAPI + SQLite server (`main.py`, `db.py`, `config.py`, `provision.py`, `templates/dashboard.html`). See `DEPLOY.md` for deploying to a server via systemd.
- `client/` — a small background daemon (`checkin_daemon.py`) that coworkers `git clone` and run directly with Python. It auto-starts via a per-user Startup-folder shortcut (`install_startup.ps1`) rather than Windows Task Scheduler, since many company-managed laptops block standard users from registering scheduled tasks. See `client/SETUP.md` (and `client/BUILD.md` for the standalone-exe fallback on a machine without Python).

## Quick start (server)

```
python -m venv venv
venv/Scripts/pip install -r requirements.txt   # venv/bin/pip on Linux
cp .env.example .env
venv/Scripts/python provision.py add "Your Name"
venv/Scripts/python -m uvicorn main:app --port 8000
```

Then open `http://localhost:8000/`.

## Quick start (client)

See `client/SETUP.md`.
