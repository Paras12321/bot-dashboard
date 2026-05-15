"""
Database access helper for the bot service worker.
Provides direct DB operations without FastAPI dependency injection.
"""

import sqlite3
import os
from datetime import datetime

# Path to the SQLite database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot_dashboard.db")


def get_connection():
    """Get a direct SQLite connection."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_pending_tasks():
    """Fetch all pending tasks from the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.*, b.platform, b.token, b.name as bot_name
        FROM tasks t
        JOIN bots b ON t.bot_id = b.id
        WHERE t.status = 'pending' AND b.is_active = 1
        ORDER BY t.created_at ASC
    """)
    tasks = cursor.fetchall()
    conn.close()
    return tasks


def mark_task_done(task_id, status="done", error_message=None):
    """Update a task's status after execution."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE tasks
        SET status = ?, error_message = ?, completed_at = ?
        WHERE id = ?
    """, (status, error_message, datetime.utcnow().isoformat(), task_id))
    conn.commit()
    conn.close()


def create_log(task_id=None, bot_id=None, level="info", message="", details=None):
    """Insert a log entry into the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (task_id, bot_id, level, message, details, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (task_id, bot_id, level, message, details, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def get_auto_replies(bot_id):
    """Get all active auto-reply rules for a specific bot."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM auto_replies
        WHERE bot_id = ? AND is_active = 1
    """, (bot_id,))
    rules = cursor.fetchall()
    conn.close()
    return rules


def get_welcome_messages(bot_id):
    """Get all active welcome messages for a specific bot."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM welcome_messages
        WHERE bot_id = ? AND is_active = 1
    """, (bot_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages


def get_active_bots():
    """Get all active bots."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bots WHERE is_active = 1")
    bots = cursor.fetchall()
    conn.close()
    return bots
