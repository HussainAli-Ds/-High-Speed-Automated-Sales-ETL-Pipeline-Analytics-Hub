"""
main.py
=======
Async entry point for the Sales ETL Pipeline.

Startup sequence
----------------
1.  Validate config & ensure directories exist.
2.  Test PostgreSQL connectivity (fail fast on misconfiguration).
3.  Start the watchdog observer thread.
4.  Scan Input_Files/ for any files already waiting.
5.  Run an async worker that pops Paths from the queue and calls
    processor.process_file() — one file at a time, fully awaited.

Stop with Ctrl+C.  A Telegram alert is sent on both start and stop.
"""

import asyncio
import sys
from pathlib import Path

# ── Make sure Code/ is on sys.path when running directly ─────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Config
from db import test_connection
from logger import logger
from processor import process_file
from telegram_bot import (
    alert_pipeline_boot,
    alert_pipeline_shutdown,
    alert_startup_warning,
)
from watcher import FileWatcher, scan_existing


# ── Async worker ──────────────────────────────────────────────────────────────

async def _worker(queue: asyncio.Queue) -> None:
    """
    Continuously consumes file Paths from the queue and processes them
    sequentially.  Unhandled exceptions are caught here as a safety net
    (processor.py already handles and logs its own errors).
    """
    while True:
        filepath: Path = await queue.get()
        try:
            await process_file(filepath)
        except Exception as exc:
            logger.critical(
                f"Unhandled exception in worker for {filepath.name}: {exc}",
                exc_info=True,
            )
        finally:
            queue.task_done()


# ── Main coroutine ────────────────────────────────────────────────────────────

async def main() -> None:
    # ── Banner ────────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("   SALES ETL PIPELINE  —  Starting up")
    logger.info("=" * 60)

    # ── Config validation ─────────────────────────────────────────────────────
    Config.ensure_directories()
    warnings = Config.validate()
    if warnings:
        for w in warnings:
            logger.warning(f"Config: {w}")
        alert_startup_warning(warnings)

    # ── DB connectivity check ─────────────────────────────────────────────────
    logger.info("Testing database connection…")
    if not test_connection():
        logger.critical(
            "Cannot reach PostgreSQL. "
            "Check your .env settings and that the Docker container is running."
        )
        logger.critical("  docker-compose up -d postgres")
        sys.exit(1)

    # ── Asyncio queue ─────────────────────────────────────────────────────────
    queue: asyncio.Queue[Path] = asyncio.Queue()
    loop  = asyncio.get_event_loop()

    # ── Start watchdog ────────────────────────────────────────────────────────
    watcher = FileWatcher(queue, loop)
    watcher.start()

    # ── Worker task ───────────────────────────────────────────────────────────
    worker_task = asyncio.create_task(_worker(queue))

    # ── Process files already in Input_Files/ ─────────────────────────────────
    await scan_existing(queue)

    # ── Telegram boot alert ───────────────────────────────────────────────────
    alert_pipeline_boot()
    logger.info("Pipeline running. Drop Excel files into Input_Files/")
    logger.info("Press Ctrl+C to stop.")

    # ── Run until interrupted ─────────────────────────────────────────────────
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        logger.info("Shutting down…")
        alert_pipeline_shutdown()
        watcher.stop()
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        logger.info("Pipeline stopped. Goodbye.")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())