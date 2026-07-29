import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# When frozen by PyInstaller, __file__ points into a temp extraction dir, not
# where the .exe actually lives — use sys.executable's folder instead so the
# config/log files stay next to the installed .exe.
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

load_dotenv(BASE_DIR / "client_config.env")

SERVER_URL = os.getenv("SERVER_URL", "").rstrip("/")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "6"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "15"))
SLEEP_THRESHOLD_SECONDS = int(os.getenv("SLEEP_THRESHOLD_SECONDS", "7200"))  # 2 hours
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

LOG_PATH = BASE_DIR / "checkin_client.log"

WINDOW_START_HOUR = 8
WINDOW_END_HOUR = 11


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


def in_checkin_window(now: datetime) -> bool:
    return WINDOW_START_HOUR <= now.hour < WINDOW_END_HOUR


def post_checkin(wake_time: datetime) -> bool:
    payload = {"wake_time": wake_time.isoformat()}
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(f"{SERVER_URL}/checkin", json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                log(f"Checkin succeeded: {response.json()}")
                return True
            log(f"Checkin failed (attempt {attempt}/{MAX_RETRIES}): HTTP {response.status_code} {response.text}")
        except requests.exceptions.RequestException as e:
            log(f"Checkin failed (attempt {attempt}/{MAX_RETRIES}): {e}")

        if attempt < MAX_RETRIES:
            time.sleep(min(RETRY_DELAY_SECONDS * attempt, 60))

    return False


def maybe_checkin(now: datetime, last_checked_in_date) -> object:
    """Posts a checkin if inside the window and not already done today. Returns the (possibly updated) last_checked_in_date."""
    if last_checked_in_date == now.date():
        return last_checked_in_date
    if not in_checkin_window(now):
        log(f"Skipped — outside {WINDOW_START_HOUR:02d}:00-{WINDOW_END_HOUR:02d}:00 window (current hour={now.hour})")
        return last_checked_in_date
    if not SERVER_URL or not AUTH_TOKEN:
        log("Skipped — SERVER_URL or AUTH_TOKEN not configured in client_config.env")
        return last_checked_in_date

    if post_checkin(datetime.now(timezone.utc)):
        return now.date()
    return last_checked_in_date


def main():
    log("checkin_daemon started")
    last_checked_in_date = None

    # Startup check — covers a fresh logon after a full shutdown, where no
    # sleep/wake gap exists to detect.
    last_checked_in_date = maybe_checkin(datetime.now(), last_checked_in_date)

    last_monotonic = time.monotonic()
    while True:
        time.sleep(POLL_INTERVAL_SECONDS)
        current_monotonic = time.monotonic()
        elapsed = current_monotonic - last_monotonic

        if elapsed >= SLEEP_THRESHOLD_SECONDS:
            log(f"Detected wake from sleep (gap={elapsed:.0f}s)")
            last_checked_in_date = maybe_checkin(datetime.now(), last_checked_in_date)

        last_monotonic = current_monotonic


if __name__ == "__main__":
    main()
