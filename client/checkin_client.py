import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

# When frozen by PyInstaller, __file__ points into a temp extraction dir, not
# where the .exe actually lives — use sys.executable's folder instead so the
# config/log files stay next to the installed .exe.
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

load_dotenv(BASE_DIR / "client_config.env")

SERVER_URL = os.getenv("SERVER_URL", "").rstrip("/")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "6"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "15"))

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


def main() -> int:
    now = datetime.now()
    if not in_checkin_window(now):
        log(f"Skipped — outside {WINDOW_START_HOUR:02d}:00-{WINDOW_END_HOUR:02d}:00 window (current hour={now.hour})")
        return 0

    if not SERVER_URL or not AUTH_TOKEN:
        log("Skipped — SERVER_URL or AUTH_TOKEN not configured in client_config.env")
        return 1

    wake_time = datetime.now(timezone.utc)
    success = post_checkin(wake_time)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
