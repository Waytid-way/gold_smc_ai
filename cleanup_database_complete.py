#!/usr/bin/env python3
"""Clean database: Delete all data AND reset auto-increment counters"""
import sqlite3
from datetime import datetime

DB_FILE = "trading_journal.db"

def clean_database_complete():
    """
    ล้างข้อมูลการเทรดทั้งหมด + reset auto-increment
    - ลบทั้งหมด: reports, journal_entries, screenshots
    - รักษา: trade_results, report_reasons (lookup tables)
    - Reset: autoincrement counters ให้ 1
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        print("🧹 กำลังล้างข้อมูลการเทรดทั้งหมด...")
        
        # ลบข้อมูล (เรียงลำดับ FK constraints)
        cursor.execute("DELETE FROM reports")
        j_count = cursor.rowcount
        
        cursor.execute("DELETE FROM journal_entries")
        je_count = cursor.rowcount
        
        cursor.execute("DELETE FROM screenshots")
        s_count = cursor.rowcount
        
        # Reset auto-increment counters
        print("\n🔄 Reset Auto-Increment Counters...")
        
        # ตรวจสอบว่า sqlite_sequence table มีอยู่
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
        if cursor.fetchone():
            cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('screenshots', 'journal_entries', 'reports')")
            cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('screenshots', 0)")
            cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('journal_entries', 0)")
            cursor.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('reports', 0)")
        
        conn.commit()
        
        print(f"\n✅ ล้างข้อมูลเรียบร้อย:")
        print(f"   📊 ลบ screenshots: {s_count} รายการ")
        print(f"   📝 ลบ journal_entries: {je_count} รายการ")
        print(f"   🚩 ลบ reports: {j_count} รายการ")
        print(f"   🆗 Reset auto-increment counters ให้เป็น 1")
        
        # ตรวจสอบ
        cursor.execute("SELECT COUNT(*) FROM screenshots")
        sc = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM journal_entries")
        je = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM reports")
        rp = cursor.fetchone()[0]
        
        print(f"\n✓ ตรวจสอบหลังล้าง:")
        print(f"   Screenshots: {sc} ✓")
        print(f"   Journal Entries: {je} ✓")
        print(f"   Reports: {rp} ✓")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    clean_database_complete()
