"""
Database access helper for the bot service worker.
Provides direct DB operations without FastAPI dependency injection.
"""

import sqlite3
import os
from contextlib import contextmanager
from datetime import datetime, timezone


DB_PATH = os.getenv(
    "BOT_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot_dashboard.db")
)


@contextmanager
def get_connection():
    """Context manager for safe SQLite connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_pending_tasks():
    """Fetch all pending tasks joined with their bot details."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT t.*, b.platform, b.token, b.name AS bot_name
            FROM tasks t
            JOIN bots b ON t.bot_id = b.id
            WHERE t.status = 'pending' AND b.is_active = 1
            ORDER BY t.created_at ASC
        """).fetchall()


def mark_task_done(task_id, status="done", error_message=None):
    """Update a task's status after execution."""
    with get_connection() as conn:
        conn.execute("""
            UPDATE tasks
            SET status = ?, error_message = ?, completed_at = ?
            WHERE id = ?
        """, (status, error_message, datetime.now(timezone.utc).isoformat(), task_id))
        conn.commit()


def create_log(task_id=None, bot_id=None, level="info", message="", details=None):
    """Insert a log entry into the database."""
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO logs (task_id, bot_id, level, message, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task_id, bot_id, level, message, details,
              datetime.now(timezone.utc).isoformat()))
        conn.commit()


def get_auto_replies(bot_id):
    """Get all active auto-reply rules for a specific bot."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM auto_replies          -- fixed: was 'auto_repliesz'
            WHERE bot_id = ? AND is_active = 1
        """, (bot_id,)).fetchall()


def get_welcome_messages(bot_id):
    """Get all active welcome messages for a specific bot."""
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM welcome_messages
            WHERE bot_id = ? AND is_active = 1
        """, (bot_id,)).fetchall()


def get_active_bots():
    """Get all active bots."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM bots WHERE is_active = 1"
        ).fetchall()