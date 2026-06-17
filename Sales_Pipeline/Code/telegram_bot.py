"""
telegram_bot.py
===============
Thin wrapper around the Telegram Bot API.
Sends structured alerts for every pipeline lifecycle event.

All credentials are read from Config — nothing is hard-coded.
Failures to send are logged but never crash the pipeline.
"""

import requests
from requests.exceptions import RequestException

from config import Config
from logger import logger

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
_MAX_MSG_LEN  = 4096   # Telegram hard limit


def _send(message: str, parse_mode: str = "HTML") -> bool:
    """
    Core send function.  Returns True on success, False on any error.
    Silent if credentials are not configured.
    """
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        logger.debug("Telegram not configured — skipping notification.")
        return False

    url     = _TELEGRAM_API.format(token=Config.TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id":    Config.TELEGRAM_CHAT_ID,
        "text":       message[:_MAX_MSG_LEN],
        "parse_mode": parse_mode,
    }

    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.debug("Telegram alert sent.")
        return True
    except RequestException as exc:
        logger.warning(f"Telegram send failed: {exc}")
        return False


# ── Public alert helpers ──────────────────────────────────────────────────────

def alert_pipeline_boot() -> None:
    _send(
        "🟢 <b>Sales ETL Pipeline Online</b>\n"
        "👁 Watching <code>Input_Files/</code> for Excel workbooks…"
    )


def alert_pipeline_shutdown() -> None:
    _send("🔴 <b>Sales ETL Pipeline Stopped</b>")


def alert_file_detected(filename: str) -> None:
    _send(
        f"📂 <b>New File Detected</b>\n"
        f"📄 <code>{filename}</code>\n"
        f"⏳ Starting processing…"
    )


def alert_file_locked(filename: str) -> None:
    _send(
        f"🔒 <b>File Lock Detected</b>\n"
        f"📄 <code>{filename}</code>\n"
        f"⏳ Waiting for the file to be released (Windows lock)…"
    )


def alert_success(filename: str, records: int, duration: float) -> None:
    _send(
        f"✅ <b>Pipeline Success</b>\n"
        f"📄 File  : <code>{filename}</code>\n"
        f"📊 Rows  : <b>{records:,}</b>\n"
        f"⏱ Time  : <b>{duration:.2f} s</b>"
    )


def alert_failure(filename: str, error: str) -> None:
    _send(
        f"❌ <b>Pipeline Failed</b>\n"
        f"📄 File  : <code>{filename}</code>\n"
        f"⚠️ Error : <code>{error[:600]}</code>"
    )


def alert_corrupted(filename: str, reason: str) -> None:
    _send(
        f"🗑 <b>File Moved to Failed_Files</b>\n"
        f"📄 File   : <code>{filename}</code>\n"
        f"📝 Reason : <code>{reason[:400]}</code>"
    )


def alert_db_error(error: str) -> None:
    _send(
        f"🛢 <b>Database Error</b>\n"
        f"⚠️ <code>{error[:600]}</code>"
    )


def alert_startup_warning(warnings: list[str]) -> None:
    body = "\n".join(f"  • {w}" for w in warnings)
    _send(
        f"⚠️ <b>Pipeline Config Warnings</b>\n"
        f"<pre>{body}</pre>"
    )