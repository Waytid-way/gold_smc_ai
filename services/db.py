"""services/db.py — SQLite connection, init, and CSV migration for Trading Journal"""
import csv
import logging
import os
import sqlite3
from datetime import datetime

import config

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Schema path (relative to this file's directory)
_SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "db", "schema.sql")


# ──────────────────────────────────────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return a sqlite3 connection with row_factory and foreign keys enabled."""
    conn = sqlite3.connect(config.DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# ──────────────────────────────────────────────────────────────────────────────
# Init (create tables + seed)
# ──────────────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Run schema.sql to create tables and seed trade_results (idempotent)."""
    schema_path = os.path.normpath(_SCHEMA_PATH)
    if not os.path.isfile(schema_path):
        raise FileNotFoundError(f"schema.sql not found at: {schema_path}")
    with open(schema_path, encoding="utf-8") as f:
        sql = f.read()
    with get_connection() as conn:
        conn.executescript(sql)
    logger.info("📦 Database initialized: %s", config.DB_FILE)


# ──────────────────────────────────────────────────────────────────────────────
# One-time CSV → DB Migration
# ──────────────────────────────────────────────────────────────────────────────

def _result_code(result_text: str) -> str:
    """Map legacy CSV 'Trade Result' string to a result code."""
    upper = result_text.upper().strip()
    if "WIN" in upper:
        return "WIN"
    if "LOSS" in upper:
        return "LOSS"
    if "MISSED" in upper:
        return "MISSED"
    return "PENDING"


def migrate_from_csv() -> int:
    """
    One-time import of trading_journal.csv into the SQLite database.
    Skips rows whose filename already exists in `screenshots`.
    Returns number of rows imported.
    """
    if not os.path.isfile(config.JOURNAL_FILE):
        logger.info("📂 No CSV file found — skipping migration.")
        return 0

    with get_connection() as conn:
        existing_count = conn.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0]
        if existing_count > 0:
            logger.info("✅ DB already has %d screenshots — skipping CSV migration.", existing_count)
            return 0

        # Fetch result_id lookup
        result_rows = conn.execute("SELECT id, code FROM trade_results").fetchall()
        code_to_id = {r["code"]: r["id"] for r in result_rows}

    with open(config.JOURNAL_FILE, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        logger.info("📂 CSV is empty — skipping migration.")
        return 0

    imported = 0
    with get_connection() as conn:
        for row in rows:
            filename    = (row.get("Image File") or "").strip()
            captured_at = (row.get("Date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")).strip()
            ai_analysis = (row.get("AI Analysis") or "").strip()
            result_text = (row.get("Trade Result") or "").strip()
            rr          = (row.get("RR") or "").strip()
            pnl_str     = (row.get("PnL_USD") or "").strip()

            if not filename:
                continue

            # Upsert screenshot
            conn.execute(
                """
                INSERT OR IGNORE INTO screenshots (filename, captured_at, ai_analysis)
                VALUES (?, ?, ?)
                """,
                (filename, captured_at, ai_analysis),
            )
            sc_row = conn.execute(
                "SELECT id FROM screenshots WHERE filename = ?", (filename,)
            ).fetchone()
            screenshot_id = sc_row["id"]

            # Map result
            code      = _result_code(result_text)
            result_id = code_to_id.get(code, code_to_id["PENDING"])

            pnl_usd: float | None = None
            if pnl_str:
                try:
                    cleaned_pnl = pnl_str.replace('$', '').replace(',', '').replace('+', '').strip()
                    if cleaned_pnl:
                        pnl_usd = float(cleaned_pnl)
                except ValueError:
                    pass

            conn.execute(
                """
                INSERT INTO journal_entries
                    (screenshot_id, result_id, rr, pnl_usd, recorded_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (screenshot_id, result_id, rr, pnl_usd, captured_at),
            )
            imported += 1

    logger.info("✅ Migrated %d rows from CSV → SQLite.", imported)
    return imported
