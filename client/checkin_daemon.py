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
MIN_SUSTAINED_ACTIVITY_SECONDS = int(os.getenv("MIN_SUSTAINED_ACTIVITY_SECONDS", "180"))  # 3 minutes

LOG_PATH = BASE_DIR / "checkin_client.log"

WINDOW_START_HOUR = 8
WINDOW_END_HOUR = 11


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write(f"[{timestamp}] {message}\n")


# --- Idle tracking ---
# Two signals, combined by taking whichever is freshest: a keyboard-only hook
# (the `keyboard` package — some corporate endpoint security software may
# flag or silently filter this, the same category of restriction that
# blocked Task Scheduler earlier) and Windows' own combined keyboard+mouse
# idle-time API as a fallback in case the hook is blocked or filtered.
#
# A single instant of activity isn't trusted on its own — see
# MIN_SUSTAINED_ACTIVITY_SECONDS below — since a momentary blip (a bumped
# mouse, or an automated overnight/morning update process briefly touching
# the session — logging in with cached credentials, dismissing a dialog,
# a management agent interacting with the desktop) looks identical to real
# activity for a single poll. A real person sitting down keeps typing or
# moving the mouse for much longer than that.
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
    activity_streak_start = None  # monotonic time the current unbroken run of activity began
    while True:
        time.sleep(POLL_INTERVAL_SECONDS)
        keyboard_idle = get_keyboard_idle_seconds()
        input_idle = get_input_idle_seconds()
        idle_seconds = min(keyboard_idle, input_idle)

        if not was_idle_long:
            if idle_seconds >= IDLE_THRESHOLD_SECONDS:
                was_idle_long = True
            continue

        # Idle for 2+ hours at some point — now watching for a genuine,
        # sustained return rather than trusting the first sign of activity.
        if idle_seconds < POLL_INTERVAL_SECONDS:
            if activity_streak_start is None:
                activity_streak_start = time.monotonic()
                log(f"Activity detected after {IDLE_THRESHOLD_SECONDS}s+ idle — confirming it lasts {MIN_SUSTAINED_ACTIVITY_SECONDS}s before treating it as a real return")

            streak_duration = time.monotonic() - activity_streak_start
            if streak_duration >= MIN_SUSTAINED_ACTIVITY_SECONDS:
                source = "KEYBOARD" if keyboard_idle < MIN_SUSTAINED_ACTIVITY_SECONDS else "MOUSE"
                log(f"Confirmed sustained activity for {MIN_SUSTAINED_ACTIVITY_SECONDS}s+ (via {source}) — treating as a real return from idle")
                was_idle_long = False
                activity_streak_start = None
                last_checked_in_date = maybe_checkin(datetime.now(), last_checked_in_date)
        elif activity_streak_start is not None:
            # Activity stopped before it was confirmed sustained — a brief
            # blip, not a real return. was_idle_long stays True so a genuine
            # return right after doesn't need another full idle period.
            log("Activity stopped before being confirmed as sustained — ignoring as a likely false trigger (e.g. an automated update)")
            activity_streak_start = None


if __name__ == "__main__":
    main()
