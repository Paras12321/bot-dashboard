"""
Bot Service Worker — runs continuously, polling the database for pending tasks
and dispatching them to the appropriate bot handler (Discord or Telegram).

Usage:
    python worker.py
"""

import asyncio
import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from bot_service.db_access import (
    get_pending_tasks,
    mark_task_done,
    create_log,
    get_active_bots
)
from bot_service.discord_bot import discord_handler
from bot_service.telegram_bot import telegram_handler

# Polling interval in seconds
POLL_INTERVAL = 5


async def process_task(task):
    """
    Process a single task by routing it to the correct bot handler.

    Args:
        task: SQLite Row object with task + bot details
    """
    task_id = task["id"]
    platform = task["platform"]
    token = task["token"]
    target_id = task["target_id"]
    message = task["message"]
    action = task["action"]
    bot_name = task["bot_name"]

    print(f"\n📋 Processing Task #{task_id}: [{platform}] {action}")
    print(f"   Bot: {bot_name} | Target: {target_id}")

    try:
        if action == "send_message":
            if platform == "discord":
                result = await discord_handler.send_message(token, target_id, message)
            elif platform == "telegram":
                result = await telegram_handler.send_message(token, target_id, message)
            else:
                result = {"status": "failed", "detail": f"Unknown platform: {platform}"}

            # Update task status based on result
            if result["status"] == "success":
                mark_task_done(task_id, status="done")
                create_log(
                    task_id=task_id,
                    bot_id=task["bot_id"],
                    level="success",
                    message=f"Message sent successfully via {platform}",
                    details=result.get("detail", "")
                )
                print(f"   ✅ Task #{task_id} completed successfully")
            else:
                mark_task_done(task_id, status="failed", error_message=result["detail"])
                create_log(
                    task_id=task_id,
                    bot_id=task["bot_id"],
                    level="error",
                    message=f"Failed to send message via {platform}",
                    details=result.get("detail", "")
                )
                print(f"   ❌ Task #{task_id} failed: {result['detail']}")
        else:
            mark_task_done(task_id, status="failed", error_message=f"Unsupported action: {action}")
            print(f"   ⚠️ Unsupported action: {action}")

    except Exception as e:
        mark_task_done(task_id, status="failed", error_message=str(e))
        create_log(
            task_id=task_id,
            bot_id=task["bot_id"],
            level="error",
            message=f"Exception during task execution",
            details=str(e)
        )
        print(f"   💥 Task #{task_id} error: {e}")


async def worker_loop():
    """
    Main worker loop — continuously polls for and processes pending tasks.
    """
    print("=" * 60)
    print("🤖 Bot Service Worker Started")
    print(f"⏱️  Polling interval: {POLL_INTERVAL}s")
    print("=" * 60)

    # Log startup
    create_log(level="info", message="Bot service worker started")

    # Show active bots
    bots = get_active_bots()
    if bots:
        print(f"\n📡 Active bots ({len(bots)}):")
        for bot in bots:
            print(f"   • {bot['name']} ({bot['platform']})")
    else:
        print("\n⚠️  No active bots found. Add bots via the dashboard.")

    print("\n🔄 Waiting for tasks...\n")

    while True:
        try:
            tasks = get_pending_tasks()

            if tasks:
                print(f"\n📬 Found {len(tasks)} pending task(s)")
                for task in tasks:
                    await process_task(task)

            await asyncio.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n🛑 Worker stopped by user")
            create_log(level="info", message="Bot service worker stopped")
            break

        except Exception as e:
            print(f"\n💥 Worker error: {e}")
            create_log(level="error", message="Worker loop error", details=str(e))
            await asyncio.sleep(POLL_INTERVAL)


def main():
    """Entry point for the worker."""
    try:
        asyncio.run(worker_loop())
    except KeyboardInterrupt:
        print("\n🛑 Shutdown complete.")


if __name__ == "__main__":
    main()
