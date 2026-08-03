import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import keyboard
import requests
import win32api
from dotenv import load_dotenv

# When frozen by PyInstaller, __file__ points into a temp extraction dir, not
# where the .exe actually lives — use sys.executable's folder instead so the
# config/log files stay next to the installed .exe.
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent

load_dotenv(BASE_DIR / "client_config.env")

SERVER_URL = os.getenv("SERVER_URL", "").rstrip("/")
PASSWORD = os.getenv("PASSWORD") or os.getenv("AUTH_TOKEN", "")  # AUTH_TOKEN kept as a fallback for older configs
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "6"))
RETRY_DELAY_SECONDS = int(os.getenv("RETRY_DELAY_SECONDS", "15"))
IDLE_THRESHOLD_SECONDS = int(os.getenv("IDLE_THRESHOLD_SECONDS", "7200"))  # 2 hours
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "60"))

LOG_PATH = BASE_DIR / "checkin_client.log"

WINDOW_START_HOUR = 8
WINDOW_END_HOUR = 11


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


# --- Idle tracking ---
# Primary signal is keyboard-only, not mouse: a mouse can get bumped by
# someone else walking past a desk, but a key press is a much stronger
# signal that the laptop's actual owner is back. It's installed via a
# low-level keyboard hook (the `keyboard` package), which some corporate
# endpoint security software may flag or block — the same category of
# restriction that blocked Task Scheduler earlier. Rather than trying to
# detect that failure directly (a silently-filtered hook raises no error —
# it just never fires), a second signal runs alongside it at all times:
# Windows' own combined keyboard+mouse idle-time API. Whichever signal
# shows the most recent activity wins, so a blocked/filtered keyboard hook
# degrades to mouse+keyboard detection instead of failing outright.
_last_keyboard_time = None  # None until a real key press has been observed
_keyboard_lock = threading.Lock()


def _on_key_event(_event):
    global _last_keyboard_time
    with _keyboard_lock:
        _last_keyboard_time = time.monotonic()


def get_keyboard_idle_seconds() -> float:
    with _keyboard_lock:
        if _last_keyboard_time is None:
            return float("inf")
        return time.monotonic() - _last_keyboard_time


def get_input_idle_seconds() -> float:
    """Seconds since the last keyboard OR mouse input, per Windows' own
    system-wide idle-time API — the fallback signal."""
    last_input_tick = win32api.GetLastInputInfo()
    current_tick = win32api.GetTickCount()
    return (current_tick - last_input_tick) / 1000.0


def get_idle_seconds() -> float:
    """The freshest of the two signals — whichever detected activity most recently."""
    return min(get_keyboard_idle_seconds(), get_input_idle_seconds())


# Windows' last-input tick as of process launch. A fresh logon (including an
# unattended one — an overnight forced-update reboot with saved credentials,
# or a remote-support session unlocking the machine) starts this daemon with
# nobody necessarily at the desk yet, so we don't treat "just launched" as
# proof of presence: has_seen_activity_since_startup() only returns True once
# a real keypress or mouse move has happened after we started watching.
_startup_input_tick = win32api.GetLastInputInfo()


def has_seen_activity_since_startup() -> bool:
    with _keyboard_lock:
        if _last_keyboard_time is not None:
            return True
    return win32api.GetLastInputInfo() != _startup_input_tick


def in_checkin_window(now: datetime) -> bool:
    return WINDOW_START_HOUR <= now.hour < WINDOW_END_HOUR


def is_weekday(now: datetime) -> bool:
    return now.weekday() < 5  # Monday=0 ... Sunday=6; weekends are 5 and 6


def post_checkin(wake_time: datetime) -> bool:
    payload = {"wake_time": wake_time.isoformat()}
    headers = {"Authorization": f"Bearer {PASSWORD}"}

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
    if not is_weekday(now):
        log(f"Skipped — weekend (current day={now.strftime('%A')})")
        return last_checked_in_date
    if not in_checkin_window(now):
        log(f"Skipped — outside {WINDOW_START_HOUR:02d}:00-{WINDOW_END_HOUR:02d}:00 window (current hour={now.hour})")
        return last_checked_in_date
    if not SERVER_URL or not PASSWORD:
        log("Skipped — SERVER_URL or PASSWORD not configured in client_config.env")
        return last_checked_in_date

    if post_checkin(datetime.now(timezone.utc)):
        return now.date()
    return last_checked_in_date


def main():
    log("checkin_daemon started")
    last_checked_in_date = None

    try:
        keyboard.on_press(_on_key_event)
        log("Keyboard hook installed (primary idle signal is keyboard-only)")
    except Exception as e:
        log(f"Keyboard hook failed to install ({e}) — relying on the mouse+keyboard idle fallback only")

    # Startup check — covers a fresh logon after a full shutdown, where
    # there's no prior idle stretch to have detected a return from. Wait for
    # a real keypress/mouse move first rather than checking in the instant
    # the process launches, since logon can happen with nobody at the desk
    # yet (an unattended overnight reboot, or a remote-support session).
    while not has_seen_activity_since_startup():
        time.sleep(2)
    last_checked_in_date = maybe_checkin(datetime.now(), last_checked_in_date)

    was_idle_long = False
    while True:
        time.sleep(POLL_INTERVAL_SECONDS)
        idle_seconds = get_idle_seconds()

        if idle_seconds >= IDLE_THRESHOLD_SECONDS:
            was_idle_long = True
        elif was_idle_long and idle_seconds < POLL_INTERVAL_SECONDS:
            log(f"Detected return from idle after {IDLE_THRESHOLD_SECONDS}s+")
            was_idle_long = False
            last_checked_in_date = maybe_checkin(datetime.now(), last_checked_in_date)


if __name__ == "__main__":
    main()
