#coding=utf-8
"""SQLite-backed analytics storage for whatsappni.

Pure functions for recording and querying user activity, independent of
python-telegram-bot's Update/Context objects. See project spec: analytics
layer for whatsappni (RU) for the full contract.
"""

import os
import sqlite3
from datetime import timedelta

DEFAULT_DB_PATH = "users.db"


def get_db_path():
    """AC-6: DB file path from the DB_PATH env var, or DEFAULT_DB_PATH if unset."""
    return os.getenv("DB_PATH") or DEFAULT_DB_PATH


def get_connection(db_path=None):
    """Open a sqlite3 connection to db_path (defaults to get_db_path())."""
    return sqlite3.connect(db_path or get_db_path())


def init_db(conn):
    """Create the `users` table (user_id, first_seen, last_seen, messages_count, username) if missing."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            messages_count INTEGER NOT NULL
        )
        """
    )
    existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)")}
    if "username" not in existing_columns:
        conn.execute("ALTER TABLE users ADD COLUMN username TEXT")
    conn.commit()


def record_activity(conn, user_id, now, username=None):
    """AC-1/AC-2: create-or-update the users row for user_id at time `now` (UTC)."""
    now_str = now.isoformat()
    existing = conn.execute(
        "SELECT user_id FROM users WHERE user_id = ?", (user_id,)
    ).fetchone()

    if existing is None:
        conn.execute(
            "INSERT INTO users (user_id, first_seen, last_seen, messages_count, username) "
            "VALUES (?, ?, ?, 1, ?)",
            (user_id, now_str, now_str, username),
        )
    else:
        conn.execute(
            "UPDATE users SET last_seen = ?, messages_count = messages_count + 1, "
            "username = COALESCE(?, username) WHERE user_id = ?",
            (now_str, username, user_id),
        )
    conn.commit()


def get_user(conn, user_id):
    """Return the stored row for user_id as a dict, or None if not found. Used by tests/inspection."""
    row = conn.execute(
        "SELECT user_id, first_seen, last_seen, messages_count, username FROM users WHERE user_id = ?",
        (user_id,),
    ).fetchone()

    if row is None:
        return None

    return {
        "user_id": row[0],
        "first_seen": row[1],
        "last_seen": row[2],
        "messages_count": row[3],
        "username": row[4],
    }


def get_stats(conn, now, days=7, exclude_user_id=None):
    """AC-4: return {'total': <row count>, 'active': <last_seen >= now - days, inclusive>}, optionally excluding one user_id (e.g. the admin)."""
    threshold = (now - timedelta(days=days)).isoformat()

    total = conn.execute(
        "SELECT COUNT(*) FROM users WHERE (? IS NULL OR user_id != ?)",
        (exclude_user_id, exclude_user_id),
    ).fetchone()[0]
    active = conn.execute(
        "SELECT COUNT(*) FROM users WHERE last_seen >= ? AND (? IS NULL OR user_id != ?)",
        (threshold, exclude_user_id, exclude_user_id),
    ).fetchone()[0]

    return {"total": total, "active": active}


def get_user_list(conn, exclude_user_id=None):
    """Return all users (excluding one user_id, e.g. the admin) as dicts, most recently active first."""
    rows = conn.execute(
        "SELECT user_id, first_seen, last_seen, messages_count, username FROM users "
        "WHERE (? IS NULL OR user_id != ?) ORDER BY last_seen DESC",
        (exclude_user_id, exclude_user_id),
    ).fetchall()

    return [
        {
            "user_id": row[0],
            "first_seen": row[1],
            "last_seen": row[2],
            "messages_count": row[3],
            "username": row[4],
        }
        for row in rows
    ]


def is_admin(user_id, admin_id_env):
    """AC-4/EC-1/ERR-1: True iff user_id matches admin_id_env parsed as an int."""
    if not admin_id_env:
        return False

    try:
        admin_id = int(admin_id_env)
    except (TypeError, ValueError):
        return False

    return user_id == admin_id
