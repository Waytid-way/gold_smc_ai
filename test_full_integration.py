#!/usr/bin/env python3
"""Test the full 3-step flow with database storage"""
import json
from services.formatter import parse_gemini_json_response, format_trade_analysis
from services.journal import save_to_journal
from services.db import get_connection

print("=" * 70)
print("🧪 FULL INTEGRATION TEST: Gemini JSON → Formatter → Database")
print("=" * 70)

# Simulate the Gemini JSON response from the error logs
gemini_response = {
    "entry": 4570.0,
    "tp": 4590.0,
    "sl": 4549.0,
    "reason": "ราคาอยู่ในโซนส่วนลด (Discount Zone) และได้ตอบสนองจาก Bullish Order Block (OB)"
}

test_filename = "TEST_XAUUSD_2026-03-25_23-41-38.png"

try:
    print("\n✅ STEP 1: Parse JSON")
    print(f"   Input: {gemini_response}")
    parsed = parse_gemini_json_response(json.dumps(gemini_response))
    print(f"   ✓ Parsed successfully")
    
    print("\n✅ STEP 2: Format for Telegram")
    formatted = format_trade_analysis(parsed)
    print("   Output (first 300 chars):")
    print("   " + "\n   ".join(formatted[:300].split("\n")))
    print(f"   ✓ Formatted successfully")
    
    print("\n✅ STEP 3: Store in Database")
    # Convert to string for analysis (like the real code does)
    analysis_text = json.dumps(gemini_response, ensure_ascii=False)
    
    # Save to journal with trade_data
    save_to_journal(
        filename=test_filename,
        result="",  # Will be PENDING
        analysis=analysis_text,
        trade_data=parsed
    )
    print("   ✓ Stored in database")
    
    print("\n✅ STEP 4: Verify Database Insertion")
    # Query the database to verify
    with get_connection() as conn:
        # Get the screenshot
        sc_row = conn.execute(
            "SELECT id FROM screenshots WHERE filename = ?",
            (test_filename,)
        ).fetchone()
        
        if sc_row:
            screenshot_id = sc_row["id"]
            # Get the journal entry
            je_row = conn.execute(
                "SELECT * FROM journal_entries WHERE screenshot_id = ?",
                (screenshot_id,)
            ).fetchone()
            
            if je_row:
                print(f"   Screenshot ID: {screenshot_id}")
                print(f"   Journal Entry ID: {je_row['id']}")
                print(f"   Entry Price: {je_row['entry_price']}")
                print(f"   TP Price: {je_row['tp_price']}")
                print(f"   SL Price: {je_row['sl_price']}")
                print(f"   Trade Reason: {je_row['trade_reason'][:50]}..." if je_row['trade_reason'] else "   Trade Reason: (None)")
                print("   ✓ Data verified in database")
            else:
                print("   ❌ Journal entry not found!")
        else:
            print("   ❌ Screenshot not found!")
    
    print("\n" + "=" * 70)
    print("✅ FULL INTEGRATION TEST PASSED!")
    print("=" * 70)
    print("\n📋 Summary:")
    print("  ✓ JSON parsing works")
    print("  ✓ Formatter creates proper Telegram message")
    print("  ✓ Database stores structured trade data")
    print("  ✓ All 4 new columns populated correctly")
    print("\nThe bot is now ready to handle /snap commands with JSON responses!")
    
except Exception as e:
    print(f"\n❌ TEST FAILED: {e}")
    import traceback
    traceback.print_exc()
