"""
config.py
=========
Single source of truth for all runtime configuration.
Every value is loaded from the .env file — nothing is hard-coded.
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

# ── Locate .env (project root, two levels up from Code/) ────────────────────
BASE_DIR: Path = Path(__file__).resolve().parent.parent

_env_path = BASE_DIR / ".env"
if not _env_path.exists():
    print(
        f"[CONFIG] WARNING: .env not found at {_env_path}. "
        "Using environment variables / defaults.",
        file=sys.stderr,
    )
load_dotenv(_env_path, override=False)


class Config:
    """All pipeline configuration loaded from environment variables."""

    # ── Database ─────────────────────────────────────────────────────────────
    DB_HOST: str     = os.getenv("DB_HOST", "localhost")
    DB_PORT: str     = os.getenv("DB_PORT", "5432")
    DB_NAME: str     = os.getenv("DB_NAME", "sales_db")
    DB_USER: str     = os.getenv("DB_USER", "sales_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    @classmethod
    def get_db_uri(cls) -> str:
        """Build a PostgreSQL ADBC/psycopg2-compatible URI, URL-encoding the password."""
        password = quote_plus(cls.DB_PASSWORD)
        return (
            f"postgresql://{cls.DB_USER}:{password}"
            f"@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        )

    # ── Telegram ──────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID: str   = os.getenv("TELEGRAM_CHAT_ID", "")

    # ── Directory paths ───────────────────────────────────────────────────────
    INPUT_DIR: Path     = BASE_DIR / os.getenv("INPUT_DIR",     "Input_Files")
    PROCESSED_DIR: Path = BASE_DIR / os.getenv("PROCESSED_DIR", "Processed_Files")
    FAILED_DIR: Path    = BASE_DIR / os.getenv("FAILED_DIR",    "Failed_Files")
    LOG_DIR: Path       = BASE_DIR / os.getenv("LOG_DIR",       "Logs")

    # ── Pipeline ──────────────────────────────────────────────────────────────
    STAGING_TABLE: str = os.getenv("STAGING_TABLE", "staging_sales")

    # File-lock retry (Windows)
    FILE_LOCK_TIMEOUT: int          = int(os.getenv("FILE_LOCK_TIMEOUT",        "30"))
    FILE_LOCK_RETRY_INTERVAL: float = float(os.getenv("FILE_LOCK_RETRY_INTERVAL","1.0"))

    # Fuzzy column-header matching sensitivity
    FUZZY_THRESHOLD: int = int(os.getenv("FUZZY_THRESHOLD", "70"))

    # ── Dashboard ─────────────────────────────────────────────────────────────
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "5000"))
    DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")

    # ── Supported Excel extensions ────────────────────────────────────────────
    EXCEL_EXTENSIONS: tuple = (".xlsx", ".xls", ".xlsm")

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all runtime directories if they do not exist."""
        for d in (cls.INPUT_DIR, cls.PROCESSED_DIR, cls.FAILED_DIR, cls.LOG_DIR):
            d.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> list[str]:
        """
        Return a list of configuration warnings (non-fatal issues).
        Called at startup to surface misconfiguration early.
        """
        warnings: list[str] = []
        if not cls.DB_PASSWORD:
            warnings.append("DB_PASSWORD is empty.")
        if not cls.TELEGRAM_BOT_TOKEN:
            warnings.append("TELEGRAM_BOT_TOKEN not set — Telegram alerts disabled.")
        if not cls.TELEGRAM_CHAT_ID:
            warnings.append("TELEGRAM_CHAT_ID not set — Telegram alerts disabled.")
        return warnings