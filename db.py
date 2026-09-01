"""SQLite persistence for meetings, action items, and the reminder log."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "app.db"
DB_PATH.parent.mkdir(exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    transcript TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS action_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER NOT NULL REFERENCES meetings(id),
    decision TEXT NOT NULL,
    task TEXT NOT NULL,
    owner TEXT NOT NULL,
    deadline TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_item_id INTEGER NOT NULL REFERENCES action_items(id),
    message TEXT NOT NULL,
    sent_at TEXT NOT NULL
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_meeting(title: str, transcript: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO meetings (title, transcript, created_at) VALUES (?, ?, ?)",
            (title, transcript, now_iso()),
        )
        return cur.lastrowid


def create_action_item(meeting_id: int, decision: str, task: str, owner: str, deadline: str | None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO action_items (meeting_id, decision, task, owner, deadline, status, created_at)
               VALUES (?, ?, ?, ?, ?, 'pending', ?)""",
            (meeting_id, decision, task, owner, deadline, now_iso()),
        )
        return cur.lastrowid


def list_meetings():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM meetings ORDER BY created_at DESC").fetchall()


def list_action_items(status: str | None = None):
    with get_conn() as conn:
        if status:
            return conn.execute(
                """SELECT ai.*, m.title AS meeting_title FROM action_items ai
                   JOIN meetings m ON m.id = ai.meeting_id
                   WHERE ai.status = ? ORDER BY ai.deadline IS NULL, ai.deadline ASC""",
                (status,),
            ).fetchall()
        return conn.execute(
            """SELECT ai.*, m.title AS meeting_title FROM action_items ai
               JOIN meetings m ON m.id = ai.meeting_id
               ORDER BY ai.deadline IS NULL, ai.deadline ASC"""
        ).fetchall()


def mark_complete(item_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE action_items SET status = 'completed', completed_at = ? WHERE id = ?",
            (now_iso(), item_id),
        )


def reopen_item(item_id: int):
    with get_conn() as conn:
        conn.execute(
            "UPDATE action_items SET status = 'pending', completed_at = NULL WHERE id = ?",
            (item_id,),
        )


def log_reminder(item_id: int, message: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO reminders (action_item_id, message, sent_at) VALUES (?, ?, ?)",
            (item_id, message, now_iso()),
        )


def reminders_for_item(item_id: int):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM reminders WHERE action_item_id = ? ORDER BY sent_at DESC", (item_id,)
        ).fetchall()


def all_reminders():
    with get_conn() as conn:
        return conn.execute(
            """SELECT r.*, ai.task, ai.owner FROM reminders r
               JOIN action_items ai ON ai.id = r.action_item_id
               ORDER BY r.sent_at DESC LIMIT 50"""
        ).fetchall()


def last_reminder_time(item_id: int) -> str | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT sent_at FROM reminders WHERE action_item_id = ? ORDER BY sent_at DESC LIMIT 1",
            (item_id,),
        ).fetchone()
        return row["sent_at"] if row else None
