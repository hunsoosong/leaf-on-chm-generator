import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from app.schemas.tasks import Task


def get_connection() -> sqlite3.Connection:
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect(os.environ["DB_FILE"])
    conn.row_factory = sqlite3.Row  # Enables dictionary-like row access
    return conn


def add_task(
    session_id: str,
    status: str,
    start_time: Optional[datetime] = datetime.now(tz=timezone.utc),
    end_time: Optional[datetime] = None,
    payload: Optional[str] = None,
) -> None:
    """Inserts a new task into the database."""
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO tasks (session_id, status, start_time, end_time, payload) VALUES (?, ?, ?, ?, ?)",
            (
                session_id,
                status,
                start_time,
                end_time,
                json.dumps(payload) if payload else None,
            ),
        )


def get_task(session_id: str) -> Optional[Task]:
    """Fetches single record from database."""
    conn = get_connection()
    with conn:
        result = conn.execute(
            f"SELECT * FROM tasks WHERE session_id = '{session_id}'"
        ).fetchone()

        return Task(**dict(result)) if result else None


def update_task(session_id: str, status: str, payload: Optional[str] = None) -> None:
    """Update record in database."""
    conn = get_connection()
    with conn:
        if status == "finished":
            end_time = datetime.now(tz=timezone.utc)
            if not payload:
                raise ValueError("Must include payload if status is 'finished.'")
            conn.execute(
                "UPDATE tasks SET status = ?, end_time = ?, payload = ? WHERE session_id = ?",
                (status, end_time, payload, session_id),
            )
        elif status == "error":
            end_time = datetime.now(tz=timezone.utc)
            conn.execute(
                "UPDATE tasks SET status = ?, end_time = ? WHERE session_id = ?",
                (status, end_time, session_id),
            )
        else:
            conn.execute(
                "UPDATE tasks SET status = ? WHERE session_id = ?", (status, session_id)
            )
