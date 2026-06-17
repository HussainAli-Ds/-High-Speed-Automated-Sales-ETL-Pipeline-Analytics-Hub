"""
db.py
=====
All database I/O lives here.

• ``bulk_load_to_staging``  – async wrapper for ADBC bulk insert (Polars → PostgreSQL)
• ``test_connection``       – verify connectivity at startup
• ``query_to_df``           – synchronous query → pandas DataFrame (for dashboard)
"""

import asyncio
from typing import Any

import polars as pl

from config import Config
from logger import logger


# ── Connection test ───────────────────────────────────────────────────────────

def test_connection() -> bool:
    """
    Open a transient ADBC connection and run SELECT 1.
    Returns True if the database is reachable, False otherwise.
    """
    try:
        import adbc_driver_postgresql.dbapi as pg  # noqa: PLC0415

        with pg.connect(Config.get_db_uri()) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        logger.info("Database connection OK.")
        return True
    except Exception as exc:
        logger.error(f"Database connection FAILED: {exc}")
        return False


# ── Bulk load (ADBC) ──────────────────────────────────────────────────────────

def _sync_bulk_load(df: pl.DataFrame) -> int:
    """
    Synchronous bulk load via ADBC ``adbc_ingest``.

    Converts the Polars DataFrame to Apache Arrow and streams it into
    the staging table.  Columns not present in the DataFrame (e.g. ``id``,
    ``loaded_at``) use their PostgreSQL DEFAULT values.
    """
    import adbc_driver_postgresql.dbapi as pg  # noqa: PLC0415

    arrow_table = df.to_arrow()

    with pg.connect(Config.get_db_uri()) as conn:
        with conn.cursor() as cur:
            cur.adbc_ingest(
                Config.STAGING_TABLE,
                arrow_table,
                mode="append",
            )
        conn.commit()

    logger.info(
        f"ADBC bulk load: {len(df)} rows → '{Config.STAGING_TABLE}'"
    )
    return len(df)


async def bulk_load_to_staging(df: pl.DataFrame) -> int:
    """
    Async wrapper: runs the synchronous ADBC bulk load in a thread-pool
    executor so it does not block the asyncio event loop.
    """
    loop = asyncio.get_event_loop()
    records = await loop.run_in_executor(None, _sync_bulk_load, df)
    return records


# ── Dashboard query helper (psycopg2 + pandas) ────────────────────────────────

def query_to_df(sql: str, params: tuple[Any, ...] | None = None):
    """
    Execute a SQL query and return the result as a **pandas** DataFrame.
    Used by the Taipy dashboard to read the analytical views.
    """
    import pandas as pd          # noqa: PLC0415
    import psycopg2              # noqa: PLC0415

    conn = psycopg2.connect(
        host     = Config.DB_HOST,
        port     = int(Config.DB_PORT),
        dbname   = Config.DB_NAME,
        user     = Config.DB_USER,
        password = Config.DB_PASSWORD,
    )
    try:
        df = pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()

    return df


def query_scalar(sql: str) -> Any:
    """Return a single scalar value from a SQL query."""
    import psycopg2  # noqa: PLC0415

    conn = psycopg2.connect(
        host     = Config.DB_HOST,
        port     = int(Config.DB_PORT),
        dbname   = Config.DB_NAME,
        user     = Config.DB_USER,
        password = Config.DB_PASSWORD,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()