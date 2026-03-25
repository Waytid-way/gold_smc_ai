#!/usr/bin/env python3
"""Database migration: Add new columns to journal_entries table"""
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_FILE = "trading_journal.db"

def migrate_add_trade_columns():
    """Add entry_price, tp_price, sl_price, trade_reason columns to journal_entries"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(journal_entries)")
        columns = {row[1] for row in cursor.fetchall()}
        
        new_columns = {
            'entry_price': 'REAL DEFAULT NULL',
            'tp_price': 'REAL DEFAULT NULL',
            'sl_price': 'REAL DEFAULT NULL',
            'trade_reason': 'TEXT DEFAULT NULL'
        }
        
        for col_name, col_def in new_columns.items():
            if col_name not in columns:
                logger.info(f"Adding column: {col_name}")
                cursor.execute(f"ALTER TABLE journal_entries ADD COLUMN {col_name} {col_def}")
            else:
                logger.info(f"Column {col_name} already exists, skipping")
        
        conn.commit()
        logger.info("✅ Migration successful! All new columns added.")
        
    except sqlite3.OperationalError as e:
        logger.error(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_add_trade_columns()
