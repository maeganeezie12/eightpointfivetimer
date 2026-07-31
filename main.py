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
from farewells import FAREWELLS
from jokes import DAD_JOKES

db.init_db()

app = FastAPI()
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

LOCAL_TZ = ZoneInfo(config.TIMEZONE)


class CheckinRequest(BaseModel):
    wake_time: datetime


class CheckinEditRequest(BaseModel):
    name: str
    wake_time: datetime


def _authenticate(authorization: str):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    password = authorization.removeprefix("Bearer ").strip()

    user = db.get_user_by_password(password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid password")
    return user


def _compute_checkin(user, wake_time: datetime):
    if wake_time.tzinfo is None:
        wake_time = wake_time.replace(tzinfo=ZoneInfo("UTC"))

    duration_hours = user["duration_hours"] or config.WORK_DURATION_HOURS
    target_time = wake_time + timedelta(hours=duration_hours)
    checkin_date = wake_time.astimezone(LOCAL_TZ).date().isoformat()
    return wake_time, target_time, checkin_date


@app.post("/checkin")
def checkin(body: CheckinRequest, authorization: str = Header(default="")):
    user = _authenticate(authorization)
    wake_time, target_time, checkin_date = _compute_checkin(user, body.wake_time)

    row, created = db.get_or_create_checkin(user["id"], wake_time, checkin_date, target_time)

    return {
        "status": "created" if created else "already_checked_in",
        "wake_time": row["wake_time"],
        "target_time": row["target_time"],
    }


@app.post("/checkin/edit")
def edit_checkin(body: CheckinEditRequest):
    user = db.get_user_by_name(body.name)
    if user is None:
        raise HTTPException(status_code=404, detail="No user with that name")

    wake_time, target_time, checkin_date = _compute_checkin(user, body.wake_time)
    db.upsert_checkin(user["id"], checkin_date, wake_time, target_time)

    return {
        "status": "updated",
        "wake_time": wake_time.isoformat(),
        "target_time": target_time.isoformat(),
    }


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    now_local = datetime.now(LOCAL_TZ)
    today = now_local.date().isoformat()
    rows = db.get_today_checkins_for_dashboard(today)
    joke_of_the_day = DAD_JOKES[now_local.timetuple().tm_yday % len(DAD_JOKES)]

    users = []
    for row in rows:
        if row["target_time"] is None:
            users.append({"name": row["name"], "color_index": row["id"] % 8, "wake_epoch": None, "target_epoch": None})
        else:
            wake_dt = datetime.fromisoformat(row["wake_time"])
            target_dt = datetime.fromisoformat(row["target_time"])
            users.append({
                "name": row["name"],
                "color_index": row["id"] % 8,
                "wake_epoch": int(wake_dt.timestamp()),
                "target_epoch": int(target_dt.timestamp()),
            })

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "users": users,
            "joke_of_the_day": joke_of_the_day,
            "farewells": FAREWELLS,
        },
    )


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request):
    all_names = [user["name"] for user in db.list_users()]
    return templates.TemplateResponse(
        "history.html",
        {"request": request, "all_names": all_names},
    )


@app.get("/api/history")
def api_history(authorization: str = Header(default="")):
    user = _authenticate(authorization)
    rows = db.get_checkin_history(user["id"])

    history = []
    for row in rows:
        wake_dt = datetime.fromisoformat(row["wake_time"]).astimezone(LOCAL_TZ)
        target_dt = datetime.fromisoformat(row["target_time"]).astimezone(LOCAL_TZ)
        history.append({
            "date": row["checkin_date"],
            "wake_time": wake_dt.isoformat(),
            "target_time": target_dt.isoformat(),
        })

    return {"name": user["name"], "history": history}


@app.get("/health")
def health():
    return {"status": "ok"}
