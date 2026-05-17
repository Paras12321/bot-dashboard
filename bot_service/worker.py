"""
worker.py - Bot Service Worker
===============================
Polls the database for pending tasks and dispatches them to the correct
bot platform (Discord / Telegram) with bounded concurrency.

Usage:
    python worker.py
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

import db_access
from discord_bot import discord_handler
from telegram_bot import telegram_handler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("worker")


POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", 5))
WORKER_CONCURRENCY: int = int(os.getenv("WORKER_CONCURRENCY", 5))




async def process_task(task, semaphore: asyncio.Semaphore) -> None:
    """
    Execute a single task end-to-end under the concurrency semaphore:
      1. Route to the correct platform handler.
      2. Mark as done or failed in the database.
      3. Write an audit log entry.
    """
    async with semaphore:
        task_id = task["id"]
        bot_id = task["bot_id"]
        platform = task["platform"]
        token = task["token"]
        target_id = task["target_id"]
        message = task["message"]
        action = task["action"]
        bot_name = task["bot_name"]

        log.info("Processing task #%s | platform=%s action=%s bot=%s",
                 task_id, platform, action, bot_name)

        try:
            if action != "send_message":
                raise ValueError(f"Unsupported action: {action}")

            if platform == "discord":
                result = await discord_handler.send_message(token, int(target_id), message)
            elif platform == "telegram":
                result = await telegram_handler.send_message(token, target_id, message)
            else:
                raise ValueError(f"Unknown platform: {platform}")

            if result["status"] == "success":
                db_access.mark_task_done(task_id, status="done")
                db_access.create_log(
                    task_id=task_id,
                    bot_id=bot_id,
                    level="info",
                    message=f"Task #{task_id} succeeded via {platform}",
                    details=result.get("detail", ""),
                )
                log.info("Task #%s completed successfully.", task_id)
            else:
                db_access.mark_task_done(task_id, status="failed",
                                         error_message=result["detail"])
                db_access.create_log(
                    task_id=task_id,
                    bot_id=bot_id,
                    level="error",
                    message=f"Task #{task_id} failed via {platform}",
                    details=result.get("detail", ""),
                )
                log.warning("Task #%s failed: %s", task_id, result["detail"])

        except Exception as exc:
            log.exception("Unexpected error executing task #%s", task_id)
            db_access.mark_task_done(task_id, status="failed", error_message=str(exc))
            db_access.create_log(
                task_id=task_id,
                bot_id=bot_id,
                level="error",
                message=f"Exception during task #{task_id}",
                details=str(exc),
            )


async def worker_loop(stop_event: asyncio.Event) -> None:
    """
    Main loop — polls the DB for pending tasks and dispatches them
    concurrently (up to WORKER_CONCURRENCY at once).
    """
    semaphore = asyncio.Semaphore(WORKER_CONCURRENCY)

    log.info("Worker started | poll_interval=%ss concurrency=%s",
             POLL_INTERVAL, WORKER_CONCURRENCY)

    db_access.create_log(level="info", message="Bot service worker started")

    
    bots = db_access.get_active_bots()
    if bots:
        log.info("Active bots (%d): %s", len(bots),
                 ", ".join(f"{b['name']} ({b['platform']})" for b in bots))
    else:
        log.warning("No active bots found. Add bots via the dashboard.")

    in_flight: set[asyncio.Task] = set()

    while not stop_event.is_set():
        try:
            tasks = db_access.get_pending_tasks()

            if tasks:
                log.info("Found %d pending task(s).", len(tasks))
                for task in tasks:
                    t = asyncio.create_task(
                        process_task(task, semaphore),
                        name=f"task_{task['id']}",
                    )
                    in_flight.add(t)
                    t.add_done_callback(in_flight.discard)

        except Exception as exc:
            log.exception("Worker poll error: %s", exc)
            db_access.create_log(level="error", message="Worker poll error",
                                 details=str(exc))

        
        for _ in range(POLL_INTERVAL * 10):
            if stop_event.is_set():
                break
            await asyncio.sleep(0.1)

    
    if in_flight:
        log.info("Draining %d in-flight task(s)...", len(in_flight))
        await asyncio.gather(*in_flight, return_exceptions=True)

    log.info("Worker loop exited cleanly.")




async def shutdown(stop_event: asyncio.Event) -> None:
    """Signal the worker to stop and close all bot sessions."""
    log.info("Shutdown signal received.")
    stop_event.set()

    log.info("Closing Discord sessions...")
    await discord_handler.close_all()

    log.info("Closing Telegram sessions...")
    await telegram_handler.close_all()

    db_access.create_log(level="info", message="Bot service worker stopped")
    log.info("Shutdown complete.")




async def main() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    log.info(
        "Bot Service Worker starting at %s UTC",
        datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(
            sig,
            lambda: asyncio.create_task(shutdown(stop_event)),
        )

    try:
        await worker_loop(stop_event)
    except asyncio.CancelledError:
        pass
    finally:
        if not stop_event.is_set():
            await shutdown(stop_event)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)