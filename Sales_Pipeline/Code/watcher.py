"""
watcher.py
==========
Watches Input_Files/ for new Excel workbooks and pushes their Paths
onto an asyncio.Queue for the async worker to consume.

Design
------
• watchdog.Observer runs in its own OS thread (it is blocking).
• Events are posted back onto the asyncio event loop via
  ``loop.call_soon_threadsafe`` — keeping the event loop thread-safe.
• On startup, any Excel files already present in the folder are
  queued immediately (picked up via ``scan_existing``).
• ``on_moved`` catches files that are *dropped* into the folder by
  Windows Explorer / file managers (they move from a temp name).
"""

import time
from pathlib import Path

from watchdog.events import (
    FileCreatedEvent,
    FileMovedEvent,
    FileSystemEventHandler,
)
from watchdog.observers import Observer

from config import Config
from logger import logger


class _ExcelEventHandler(FileSystemEventHandler):
    """Watchdog event handler that filters for Excel files only."""

    def __init__(self, queue, loop) -> None:  # queue: asyncio.Queue
        super().__init__()
        self._queue = queue
        self._loop  = loop

    def _enqueue(self, path: Path) -> None:
        """Thread-safe push onto the asyncio queue."""
        if path.suffix.lower() in Config.EXCEL_EXTENSIONS:
            # Brief pause — ensures the writing process has fully closed
            # the file before we attempt to read it (important on Windows).
            time.sleep(0.5)
            logger.info(f"Queued: {path.name}")
            self._loop.call_soon_threadsafe(self._queue.put_nowait, path)

    def on_created(self, event: FileCreatedEvent) -> None:
        if not event.is_directory:
            self._enqueue(Path(event.src_path))

    def on_moved(self, event: FileMovedEvent) -> None:
        """Catches files moved/saved into the watch folder."""
        if not event.is_directory:
            self._enqueue(Path(event.dest_path))


class FileWatcher:
    """
    High-level watcher.  Wraps watchdog's Observer thread and exposes
    a simple ``start`` / ``stop`` API.
    """

    def __init__(self, queue, loop) -> None:
        self._queue    = queue
        self._loop     = loop
        self._observer = Observer()

    def start(self) -> None:
        Config.INPUT_DIR.mkdir(parents=True, exist_ok=True)
        handler = _ExcelEventHandler(self._queue, self._loop)
        self._observer.schedule(
            handler,
            str(Config.INPUT_DIR),
            recursive=False,
        )
        self._observer.start()
        logger.info(f"Watching : {Config.INPUT_DIR}")

    def stop(self) -> None:
        self._observer.stop()
        self._observer.join()
        logger.info("Watcher stopped.")


async def scan_existing(queue) -> None:
    """
    At startup, push any Excel files already sitting in Input_Files/
    onto the queue so they are not silently ignored.
    """
    Config.INPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing: list[Path] = []
    for ext in Config.EXCEL_EXTENSIONS:
        existing.extend(Config.INPUT_DIR.glob(f"*{ext}"))

    if existing:
        logger.info(
            f"Found {len(existing)} existing file(s) in Input_Files/ — "
            f"queuing for processing."
        )
        for filepath in sorted(existing):
            await queue.put(filepath)
    else:
        logger.info("Input_Files/ is empty — waiting for new files…")