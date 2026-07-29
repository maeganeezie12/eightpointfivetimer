import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "work_timer.db"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                name            TEXT    NOT NULL,
                token           TEXT    NOT NULL UNIQUE,
                duration_hours  REAL,
                created_at      TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS checkins (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                checkin_date  TEXT    NOT NULL,
                wake_time     TEXT    NOT NULL,
                target_time   TEXT    NOT NULL,
                created_at    TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, checkin_date)
            )
        """)


def add_user(name: str, token: str, duration_hours: float | None = None):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO users (name, token, duration_hours, created_at) VALUES (?, ?, ?, ?)",
            (name, token, duration_hours, datetime.now(timezone.utc).isoformat()),
        )


def list_users():
    with _conn() as conn:
        return conn.execute(
            "SELECT id, name, duration_hours, created_at FROM users ORDER BY created_at"
        ).fetchall()


def get_user_by_token(token: str):
    with _conn() as conn:
        return conn.execute(
            "SELECT id, name, duration_hours FROM users WHERE token = ?", (token,)
        ).fetchone()


def get_user_by_name(name: str):
    with _conn() as conn:
        return conn.execute(
            "SELECT id, name, duration_hours FROM users WHERE name = ? LIMIT 1", (name,)
        ).fetchone()


def remove_user_by_name(name: str) -> int:
    """Delete all users matching name (and their checkins). Returns how many users were removed."""
    with _conn() as conn:
        ids = [row["id"] for row in conn.execute("SELECT id FROM users WHERE name = ?", (name,)).fetchall()]
        for user_id in ids:
            conn.execute("DELETE FROM checkins WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE name = ?", (name,))
    return len(ids)


def get_or_create_checkin(user_id: int, wake_time_utc: datetime, checkin_date: str, target_time_utc: datetime):
    with _conn() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO checkins (user_id, checkin_date, wake_time, target_time, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                checkin_date,
                wake_time_utc.isoformat(),
                target_time_utc.isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        row = conn.execute(
            "SELECT wake_time, target_time FROM checkins WHERE user_id = ? AND checkin_date = ?",
            (user_id, checkin_date),
        ).fetchone()
    created = row["wake_time"] == wake_time_utc.isoformat()
    return row, created


def upsert_checkin(user_id: int, checkin_date: str, wake_time_utc: datetime, target_time_utc: datetime):
    """Create today's checkin, or overwrite it if one already exists (manual edit)."""
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO checkins (user_id, checkin_date, wake_time, target_time, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, checkin_date) DO UPDATE SET
                wake_time = excluded.wake_time,
                target_time = excluded.target_time
            """,
            (
                user_id,
                checkin_date,
                wake_time_utc.isoformat(),
                target_time_utc.isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )


def get_checkin_history(user_id: int, limit: int = 90):
    with _conn() as conn:
        return conn.execute(
            """
            SELECT checkin_date, wake_time, target_time
            FROM checkins
            WHERE user_id = ?
            ORDER BY checkin_date DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()


def get_today_checkins_for_dashboard(checkin_date: str):
    with _conn() as conn:
        return conn.execute(
            """
            SELECT u.id, u.name, c.wake_time, c.target_time
            FROM users u
            LEFT JOIN checkins c ON c.user_id = u.id AND c.checkin_date = ?
            ORDER BY u.name
            """,
            (checkin_date,),
        ).fetchall()
