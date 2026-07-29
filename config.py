import os

from dotenv import load_dotenv

load_dotenv()

TIMEZONE = os.getenv("TIMEZONE", "Asia/Singapore")
WORK_DURATION_HOURS = float(os.getenv("WORK_DURATION_HOURS", "8.5"))
DASHBOARD_DONE_MESSAGE = os.getenv("DASHBOARD_DONE_MESSAGE", "Shift complete — log off!")
PORT = int(os.getenv("PORT", "8000"))
