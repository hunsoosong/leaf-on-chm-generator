import os
import sqlite3


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    status TEXT NOT NULL,
    start_time DATETIME,
    end_time DATETIME,
    payload TEXT
);
"""


def initialize_db() -> None:
    """Creates the tasks table if it does not exist."""
    DB_FILE = os.environ.get("DB_FILE")
    print(DB_FILE)
    if not DB_FILE:
        raise ValueError("'DB_FILE' environment variable not set.")

    conn = sqlite3.connect(DB_FILE)
    with conn:
        conn.execute(CREATE_TABLE_SQL)


if __name__ == "__main__":
    initialize_db()
    print("Database initialized successfully.")
