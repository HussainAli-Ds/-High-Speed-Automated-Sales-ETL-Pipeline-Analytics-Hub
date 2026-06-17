"""
logger.py
=========
Configures a unified logger that writes to:
  • Console  (INFO and above, coloured)
  • Logs/pipeline.log  (DEBUG and above, with timestamps)

Import `logger` from anywhere in the project:
    from logger import logger
"""

import logging
import sys
from pathlib import Path

# ── Lazy import to avoid circular deps ────────────────────────────────────────
def _get_log_dir() -> Path:
    from config import Config  # noqa: PLC0415
    return Config.LOG_DIR


# ── Colour codes (Windows CMD + modern terminals) ─────────────────────────────
class _AnsiColour:
    RESET  = "\033[0m"
    GREY   = "\033[90m"
    CYAN   = "\033[96m"
    YELLOW = "\033[93m"
    RED    = "\033[91m"
    BOLD   = "\033[1m"


class _ColouredFormatter(logging.Formatter):
    """Apply ANSI colours to console log levels."""

    LEVEL_COLOURS = {
        logging.DEBUG:    _AnsiColour.GREY,
        logging.INFO:     _AnsiColour.CYAN,
        logging.WARNING:  _AnsiColour.YELLOW,
        logging.ERROR:    _AnsiColour.RED,
        logging.CRITICAL: _AnsiColour.BOLD + _AnsiColour.RED,
    }

    def format(self, record: logging.LogRecord) -> str:
        colour = self.LEVEL_COLOURS.get(record.levelno, "")
        record.levelname = f"{colour}{record.levelname:<8}{_AnsiColour.RESET}"
        return super().format(record)


def setup_logger(name: str = "sales_pipeline") -> logging.Logger:
    """
    Build and return a configured logger instance.
    Safe to call multiple times — handlers are only added once.
    """
    log_dir = _get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)

    if logger.handlers:
        # Already configured — return as-is
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    _fmt      = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    _date_fmt = "%Y-%m-%d %H:%M:%S"

    # ── File handler — full DEBUG log ─────────────────────────────────────────
    log_file = log_dir / "pipeline.log"
    fh = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_fmt, datefmt=_date_fmt))
    logger.addHandler(fh)

    # ── Console handler — INFO and above, coloured ────────────────────────────
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(_ColouredFormatter(_fmt, datefmt=_date_fmt))
    logger.addHandler(ch)

    return logger


# ── Module-level singleton ────────────────────────────────────────────────────
logger = setup_logger()