# Coworker laptop setup

Per person, once you've provisioned them on the server (`provision.py add "Their Name"` — see the repo root), do this on their laptop. No Python or pip install needed — it's a standalone `.exe`.

## 1. Copy files

Create `C:\WorkTimer\` and copy in:
- `checkin_client.exe` (built from `checkin_client.py` — see `BUILD.md`)
- `client_config.env.example` — rename to `client_config.env` and fill in their `AUTH_TOKEN` (and `SERVER_URL` if different from the default)
- `WorkTimerCheckin.xml`

## 2. Register the scheduled task

From a normal PowerShell/cmd prompt (no admin rights needed for a per-user task):

```
schtasks /create /tn "WorkTimerCheckin" /xml "C:\WorkTimer\WorkTimerCheckin.xml"
```

This registers two triggers that both run `checkin_client.exe`:
- **On an event** — fires when Windows logs a "resumed from sleep" event (System log, source `Microsoft-Windows-Power-Troubleshooter`, Event ID 1).
- **At log on** — covers a full shutdown overnight, where no wake event exists.

The exe itself only actually posts a checkin if the local time is between 08:00 and 11:00 — outside that window it just logs "skipped" and exits, so it's safe for the task to fire more than once a day (e.g. sleep/wake during lunch).

## 3. Verify

- Check `C:\WorkTimer\checkin_client.log` after a wake/logon event for a line confirming success or the reason it skipped.
- Check the dashboard at `http://192.119.82.215:8000/` for their name and a live countdown.

## To remove

```
schtasks /delete /tn "WorkTimerCheckin" /f
```
