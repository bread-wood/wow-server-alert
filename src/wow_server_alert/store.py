"""SQLite state — tracks per-realm status and transition timestamps."""

import sqlite3
import time
from pathlib import Path

_DDL = """
CREATE TABLE IF NOT EXISTS realm_watch (
    realm_id     INTEGER PRIMARY KEY,
    realm_name   TEXT    NOT NULL,
    last_status  TEXT    NOT NULL,
    last_changed REAL    NOT NULL,
    notified_at  REAL
);
"""


def init_db(db_path: str) -> None:
    """Create schema if not present. Enables WAL mode."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_DDL)
        conn.commit()
    finally:
        conn.close()


def get_realm(db_path: str, realm_id: int) -> dict | None:
    """Return the stored row for realm_id, or None if unseen."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM realm_watch WHERE realm_id = ?", (realm_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def upsert_realm(
    db_path: str,
    realm_id: int,
    realm_name: str,
    status: str,
    notified_at: float | None = None,
) -> None:
    """Insert or update realm status. last_changed is set only when status changes."""
    conn = sqlite3.connect(db_path)
    try:
        existing = conn.execute(
            "SELECT last_status, last_changed FROM realm_watch WHERE realm_id = ?",
            (realm_id,),
        ).fetchone()

        now = time.time()
        if existing is None:
            conn.execute(
                """
                INSERT INTO realm_watch (realm_id, realm_name, last_status, last_changed, notified_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (realm_id, realm_name, status, now, notified_at),
            )
        else:
            last_changed = now if existing[0] != status else existing[1]
            conn.execute(
                """
                UPDATE realm_watch
                SET realm_name=?, last_status=?, last_changed=?, notified_at=?
                WHERE realm_id=?
                """,
                (realm_name, status, last_changed, notified_at, realm_id),
            )
        conn.commit()
    finally:
        conn.close()
