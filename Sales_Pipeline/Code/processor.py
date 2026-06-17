"""
processor.py
============
Core ETL logic for a single file:

  1. Wait for Windows file lock to release
  2. Read Excel (openpyxl fallback to pandas) via strict context managers
  3. Fuzzy-map column headers          ← thefuzz / rapidfuzz
  4. Standardise + cast types          ← Polars (structural work only)
  5. Bulk-load to staging table        ← ADBC
  6. Move file to Processed/ or Failed/

── TYPE RULES (ADBC binary COPY is strict) ──────────────────────────────────
  quantity       →  Polars Int32   (Arrow int32   = PostgreSQL INTEGER 4-byte)
  price_per_unit →  Polars Float64 (Arrow float64 = PostgreSQL FLOAT8  8-byte)
  sales_amount   →  Polars Float64 (Arrow float64 = PostgreSQL FLOAT8  8-byte)

All analytics / aggregations live in PostgreSQL views (init.sql).
"""

import asyncio
import gc  # Force Windows file descriptor releases
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

import polars as pl

from column_mapper import CANONICAL_COLUMNS, map_columns, validate_required_columns
from config import Config
from db import bulk_load_to_staging
from logger import logger
from telegram_bot import (
    alert_corrupted,
    alert_failure,
    alert_file_detected,
    alert_file_locked,
    alert_success,
)

# ── Excel date serial ─────────────────────────────────────────────────────────
_EXCEL_EPOCH = datetime(1899, 12, 30)
_SERIAL_MIN  = 30_000   # ≈ 1982
_SERIAL_MAX  = 65_000   # ≈ 2078


def _excel_serial_to_date_str(value) -> str | None:
    """Convert an Excel date serial number to ISO date string."""
    try:
        if value is None:
            return None
        serial = int(float(value))
        if serial < 1:
            return None
        return (_EXCEL_EPOCH + timedelta(days=serial)).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OverflowError):
        return None


def _looks_like_excel_serial(value) -> bool:
    try:
        return _SERIAL_MIN < float(value) < _SERIAL_MAX
    except (TypeError, ValueError):
        return False


# ── Windows file-lock handling ────────────────────────────────────────────────

def wait_for_file_release(filepath: Path) -> bool:
    """
    Poll until the file can be opened exclusively or the timeout expires.
    Handles Windows file locks (e.g. Excel still holding the file).
    """
    timeout  = Config.FILE_LOCK_TIMEOUT
    interval = Config.FILE_LOCK_RETRY_INTERVAL
    start    = time.monotonic()
    alerted  = False

    while time.monotonic() - start < timeout:
        try:
            with open(filepath, "rb") as fh:
                fh.read(1)
            return True
        except (IOError, PermissionError, OSError):
            if not alerted:
                logger.warning(f"File locked: {filepath.name} — waiting…")
                alert_file_locked(filepath.name)
                alerted = True
            time.sleep(interval)

    logger.error(f"File still locked after {timeout}s: {filepath.name}")
    return False


async def _move_with_retry(
    src: Path,
    dest: Path,
    max_attempts: int = 6,
    delay: float = 2.0,
) -> None:
    """
    Async retry wrapper for shutil.move.

    On Windows, after a failed ADBC ingest the Excel file may still be
    referenced by openpyxl's internal read buffers for a brief window.
    We wait asynchronously between attempts so the event loop stays alive.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            shutil.move(str(src), str(dest))
            return                              # success
        except (PermissionError, OSError) as exc:
            if attempt < max_attempts:
                logger.warning(
                    f"Move attempt {attempt}/{max_attempts} blocked "
                    f"(Windows file lock): {exc}. Retrying in {delay}s…"
                )
                await asyncio.sleep(delay)
            else:
                raise   # exhausted retries — re-raise for the caller


# ── Excel reader ──────────────────────────────────────────────────────────────

def _read_excel(filepath: Path) -> pl.DataFrame:
    """
    Read an Excel workbook into a Polars DataFrame.
    Uses strict memory context managers to prevent underlying file handle retention.
    """
    # ── Polars native ─────────────────────────────────────────────────────
    try:
        with open(filepath, "rb") as f:
            df = pl.read_excel(source=f, engine="openpyxl")
        if not df.is_empty():
            logger.debug(f"Read via polars/openpyxl: {len(df)} rows")
            return df
    except Exception as exc:
        logger.debug(f"polars/openpyxl failed: {exc}")

    # ── Pandas fallback ───────────────────────────────────────────────────
    try:
        import pandas as pd   # noqa: PLC0415
        with open(filepath, "rb") as f:
            pdf = pd.read_excel(f)
        df  = pl.from_pandas(pdf)
        logger.debug(f"Read via pandas fallback: {len(df)} rows")
        return df
    except Exception as exc:
        raise ValueError(
            f"Cannot read '{filepath.name}' with any engine: {exc}"
        ) from exc


# ── Column standardisation ────────────────────────────────────────────────────

def _standardise(df: pl.DataFrame, source_file: str) -> pl.DataFrame:
    """
    Map headers → cast types → attach metadata.

    TYPE CONTRACT (must match init.sql column definitions exactly so that
    the ADBC binary COPY protocol does not raise format errors):

        quantity       Int32   → PostgreSQL INTEGER  (4-byte signed)
        price_per_unit Float64 → PostgreSQL FLOAT8   (8-byte double)
        sales_amount   Float64 → PostgreSQL FLOAT8   (8-byte double)
        sale_date      Date    → PostgreSQL DATE
        *text columns* Utf8    → PostgreSQL TEXT
    """

    # ── 1. Fuzzy header mapping ───────────────────────────────────────────
    col_map = map_columns(df.columns)
    ok, missing = validate_required_columns(col_map)
    if not ok:
        raise ValueError(
            f"Missing required columns after fuzzy mapping: {missing}. "
            f"Raw headers: {df.columns}"
        )

    df = df.rename({orig: canon for orig, canon in col_map.items()})

    # ── 2. Keep only canonical columns (drop extras) ──────────────────────
    keep = [c for c in CANONICAL_COLUMNS if c in df.columns]
    df   = df.select(keep)

    # ── 3a. sale_date — multi-format detection ────────────────────────────
    if "sale_date" in df.columns:
        dtype  = df["sale_date"].dtype
        sample = df["sale_date"].drop_nulls().head(5).to_list()

        if dtype == pl.Date:
            pass  # openpyxl already parsed it

        elif str(dtype).startswith("Datetime"):
            df = df.with_columns(
                pl.col("sale_date").cast(pl.Date).alias("sale_date")
            )

        elif sample and _looks_like_excel_serial(sample[0]):
            # Numeric Excel serial (e.g. 44929 → 2023-01-01)
            df = df.with_columns(
                pl.col("sale_date")
                  .map_elements(_excel_serial_to_date_str, return_dtype=pl.Utf8)
                  .str.to_date("%Y-%m-%d", strict=False)
                  .alias("sale_date")
            )
        else:
            # String date — attempt common formats in order
            parsed = False
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                try:
                    df = df.with_columns(
                        pl.col("sale_date")
                          .cast(pl.Utf8)
                          .str.to_date(fmt, strict=False)
                          .alias("sale_date")
                    )
                    parsed = True
                    break
                except Exception:
                    continue
            if not parsed:
                logger.warning("sale_date: unrecognised format — some values may be null.")
                df = df.with_columns(
                    pl.col("sale_date")
                      .cast(pl.Utf8)
                      .str.to_date(strict=False)
                      .alias("sale_date")
                )

    # ── 3b. quantity → Int32 (PostgreSQL INTEGER = 4-byte) ───────────────
    if "quantity" in df.columns:
        df = df.with_columns(
            pl.col("quantity")
              .cast(pl.Float64, strict=False)   # 20 / 20.0 / "20" / "20.0"
              .round(0)
              .cast(pl.Int32, strict=False)     # Int32 ↔ PostgreSQL INTEGER
              .alias("quantity")
        )

    # ── 3c. decimal columns → Float64 (PostgreSQL FLOAT8 = 8-byte) ───────
    for col in ("price_per_unit", "sales_amount"):
        if col in df.columns:
            df = df.with_columns(
                pl.col(col)
                  .cast(pl.Utf8, strict=False)
                  .str.strip_chars()
                  .str.replace_all(r"[,\s]", "")
                  .cast(pl.Float64, strict=False)
                  .alias(col)
            )

    # ── 3d. text columns — strip whitespace ───────────────────────────────
    for col in (
        "customer_name", "city", "state", "region",
        "product_category", "product_name",
    ):
        if col in df.columns:
            df = df.with_columns(
                pl.col(col).cast(pl.Utf8, strict=False).str.strip_chars().alias(col)
            )

    # ── 4. Drop rows with null critical fields ────────────────────────────
    critical = ["sale_date", "customer_name", "sales_amount"]
    before   = len(df)
    df       = df.drop_nulls(subset=[c for c in critical if c in df.columns])
    dropped  = before - len(df)
    if dropped:
        logger.warning(f"Dropped {dropped} rows with null in critical columns.")

    if df.is_empty():
        raise ValueError("No valid rows remain after cleaning.")

    # ── 5. Metadata column ────────────────────────────────────────────────
    df = df.with_columns(pl.lit(source_file).alias("source_file"))

    # ── 6. Log final schema for debugging ────────────────────────────────
    logger.debug(
        "Schema → " +
        ", ".join(f"{c}:{df[c].dtype}" for c in df.columns)
    )

    return df


# ── Main async processor ──────────────────────────────────────────────────────

async def process_file(filepath: Path) -> None:
    """
    Full ETL pipeline for one Excel file.
    All exceptions move the file to Failed_Files/ and fire Telegram alerts.
    """
    filename   = filepath.name
    start_time = time.monotonic()

    logger.info("─" * 55)
    logger.info(f"Processing : {filename}")
    alert_file_detected(filename)

    try:
        # ── Step 1: Windows file lock ─────────────────────────────────────
        if not wait_for_file_release(filepath):
            raise IOError(
                f"'{filename}' remained locked for "
                f"{Config.FILE_LOCK_TIMEOUT}s — aborting."
            )

        # ── Step 2: Read Excel ────────────────────────────────────────────
        df_raw = _read_excel(filepath)
        logger.info(
            f"Read       : {len(df_raw):,} rows × {len(df_raw.columns)} cols"
        )
        if df_raw.is_empty():
            raise ValueError("Workbook contains no data rows.")

        # ── Step 3: Standardise + cast ────────────────────────────────────
        df_clean = _standardise(df_raw, filename)
        logger.info(f"Cleaned    : {len(df_clean):,} rows ready for load")

        # ── Step 4: ADBC bulk load ────────────────────────────────────────
        records  = await bulk_load_to_staging(df_clean)
        duration = time.monotonic() - start_time

        logger.info(f"Loaded     : {records:,} records in {duration:.2f}s ✅")
        alert_success(filename, records, duration)

        # ── Step 5: Archive → Processed/ ─────────────────────────────────
        Config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = Config.PROCESSED_DIR / f"{ts}_{filename}"
        await _move_with_retry(filepath, dest)
        logger.info(f"Archived   : → Processed_Files/{dest.name}")

    except Exception as exc:
        error_str = str(exc)
        logger.error(f"FAILED     : {filename} — {error_str}", exc_info=True)
        alert_failure(filename, error_str)

        # ── Explicit Reference Breakdown & GC collect sweep ───────────────
        if 'df_clean' in locals(): del df_clean
        if 'df_raw' in locals(): del df_raw
        gc.collect()

        # ── Quarantine → Failed_Files/ (async retry for Windows locks) ───
        try:
            Config.FAILED_DIR.mkdir(parents=True, exist_ok=True)
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = Config.FAILED_DIR / f"{ts}_{filename}"
            await _move_with_retry(filepath, dest)
            alert_corrupted(filename, error_str)
            logger.info(f"Quarantined: → Failed_Files/{dest.name}")
        except Exception as move_err:
            logger.critical(
                f"Cannot quarantine '{filename}' even after retries: {move_err}. "
                f"Please move it manually."
            )