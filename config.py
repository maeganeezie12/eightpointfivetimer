import os

from dotenv import load_dotenv

load_dotenv()

TIMEZONE = os.getenv("TIMEZONE", "Asia/Singapore")
WORK_DURATION_HOURS = float(os.getenv("WORK_DURATION_HOURS", "8.5"))
PORT = int(os.getenv("PORT", "8000"))
