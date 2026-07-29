from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from pydantic import BaseModel

import config
import db

db.init_db()

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

LOCAL_TZ = ZoneInfo(config.TIMEZONE)


class CheckinRequest(BaseModel):
    wake_time: datetime


@app.post("/checkin")
def checkin(body: CheckinRequest, authorization: str = Header(default="")):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ").strip()

    user = db.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    wake_time = body.wake_time
    if wake_time.tzinfo is None:
        wake_time = wake_time.replace(tzinfo=ZoneInfo("UTC"))

    duration_hours = user["duration_hours"] or config.WORK_DURATION_HOURS
    target_time = wake_time + timedelta(hours=duration_hours)
    checkin_date = wake_time.astimezone(LOCAL_TZ).date().isoformat()

    row, created = db.get_or_create_checkin(user["id"], wake_time, checkin_date, target_time)

    return {
        "status": "created" if created else "already_checked_in",
        "wake_time": row["wake_time"],
        "target_time": row["target_time"],
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    today = datetime.now(LOCAL_TZ).date().isoformat()
    rows = db.get_today_checkins_for_dashboard(today)

    users = []
    for row in rows:
        if row["target_time"] is None:
            users.append({"name": row["name"], "target_epoch": None})
        else:
            target_dt = datetime.fromisoformat(row["target_time"])
            users.append({"name": row["name"], "target_epoch": int(target_dt.timestamp())})

    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "users": users, "done_message": config.DASHBOARD_DONE_MESSAGE},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
