# Coworker laptop setup

Per person, once you've provisioned them on the server (`python provision.py add "Their Name"` — see `work_timer_server/`), do this on their laptop:

## 1. Copy files

Create `C:\WorkTimer\` and copy in:
- `checkin_client.py`
- `requirements.txt`
- `client_config.env.example` — rename to `client_config.env` and fill in their `AUTH_TOKEN` (and `SERVER_URL` if different from the default)

## 2. Install dependencies

```
pip install -r C:\WorkTimer\requirements.txt
```

## 3. Register the scheduled task

From an elevated or normal PowerShell/cmd prompt (no admin rights needed for a per-user task):

```
schtasks /create /tn "WorkTimerCheckin" /xml "C:\WorkTimer\WorkTimerCheckin.xml"
```

This registers two triggers that both run `checkin_client.py`:
- **On an event** — fires when Windows logs a "resumed from sleep" event (System log, source `Microsoft-Windows-Power-Troubleshooter`, Event ID 1).
- **At log on** — covers a full shutdown overnight, where no wake event exists.

The script itself only actually posts a checkin if the local time is between 08:00 and 11:00 — outside that window it just logs "skipped" and exits, so it's safe for the task to fire more than once a day (e.g. sleep/wake during lunch).

## 4. Verify

- Check `C:\WorkTimer\checkin_client.log` after a wake/logon event for a line confirming success or the reason it skipped.
- Check the dashboard at `http://192.119.82.215:8000/` for their name and a live countdown.

## To remove

```
schtasks /delete /tn "WorkTimerCheckin" /f
```
