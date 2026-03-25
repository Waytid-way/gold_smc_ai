#!/usr/bin/env python3
"""Clean up database by deleting old data while keeping schema"""

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

DB_PATH = "trading_journal.db"
BACKUP_PATH = f"trading_journal.db.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"

def backup_database():
    """Create backup of current database"""
    print(f"📦 Creating backup: {BACKUP_PATH}...")
    try:
        shutil.copy2(DB_PATH, BACKUP_PATH)
        print(f"✅ Backup created: {BACKUP_PATH}")
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

def clean_database():
    """Delete all data while keeping schema"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        print("\n🗑️  Cleaning database...")
        
        # Delete data from transaction tables (in order to respect FK constraints)
        tables_to_clean = [
            'reports',           # Delete reports first (FK to journal_entries)
            'journal_entries',   # Delete journal entries (FK to screenshots)
            'screenshots'        # Delete screenshots
        ]
        
        for table in tables_to_clean:
            try:
                cursor.execute(f"DELETE FROM {table}")
                count = cursor.rowcount
                print(f"  ✓ Deleted {count} rows from {table}")
            except Exception as e:
                print(f"  ❌ Error deleting from {table}: {e}")
        
        # Reset auto-increment for each table
        print("\n🔄 Resetting auto-increment counters...")
        for table in tables_to_clean:
            try:
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")
                print(f"  ✓ Reset {table} auto_increment")
            except Exception as e:
                # Table might not have auto_increment
                pass
        
        conn.commit()
        
        # Verify
        print("\n✅ Verification:")
        for table in tables_to_clean + ['trade_results', 'report_reasons']:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} rows")
        
        conn.close()
        print("\n✅ Database cleanup complete!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧹 Trading Journal Database Cleanup")
    print("=" * 60)
    
    # Verify database exists
    if not Path(DB_PATH).exists():
        print(f"❌ Database not found: {DB_PATH}")
        exit(1)
    
    # Backup first
    if not backup_database():
        exit(1)
    
    # Clean
    if not clean_database():
        exit(1)
    
    print("\n" + "=" * 60)
    print("✅ All done! Database is clean and ready for new data.")
    print(f"📦 Backup saved: {BACKUP_PATH}")
    print("=" * 60)
