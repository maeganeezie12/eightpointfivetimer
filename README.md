# eightpointfivetimer

Multi-user work-timer check-in system. Each person's laptop automatically posts a check-in when it wakes from sleep (or on logon) between 08:00–11:00, and a shared web dashboard shows everyone's live countdown to the end of their shift.

## Layout

- Repo root — FastAPI + SQLite server (`main.py`, `db.py`, `config.py`, `provision.py`, `templates/dashboard.html`). See `DEPLOY.md` for deploying to a server via systemd.
- `client/` — the per-laptop check-in script (`checkin_client.py`), packaged into a standalone `.exe` (see `client/BUILD.md`) so coworkers don't need Python installed, plus a Windows Task Scheduler template (`WorkTimerCheckin.xml`) and setup instructions (`client/SETUP.md`).

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
