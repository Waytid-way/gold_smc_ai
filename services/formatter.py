"""services/formatter.py — JSON → Telegram Message Formatter"""
import json
import logging

logger = logging.getLogger(__name__)


def determine_direction(entry: float, tp: float) -> str:
    """
    กำหนดทิศทางเทรด (SELL/BUY) จากราคา Entry และ TP
    - BUY: Entry < TP (ราคาไปขึ้น)
    - SELL: Entry > TP (ราคาไปลง)
    """
    if entry < tp:
        return "BUY"
    elif entry > tp:
        return "SELL"
    else:
        return "NEUTRAL"  # ไม่มีทิศทาง


def format_trade_analysis(json_response: dict) -> str:
    """
    แปลง Gemini JSON response → Telegram message format
    
    Input:
    {
        "entry": 2100.50,
        "tp": 2150.00,
        "sl": 2080.00,
        "reason": "Support level breakdown + lower lows"
    }
    
    Output:
    🔴 **SELL** / 🟢 **BUY**
    ─────────────────────────
    📊 Analysis:
    🎯 Entry: 2,100.50
    📈 TP: 2,150.00
    🛑 SL: 2,080.00
    💡 Reason: Support level breakdown + lower lows
    """
    
    try:
        entry = float(json_response.get("entry", 0))
        tp = float(json_response.get("tp", 0))
        sl = float(json_response.get("sl", 0))
        reason = json_response.get("reason", "No reason provided")
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid JSON format: {e}")
        return "❌ Invalid trade data format"
    
    # หา direction
    direction = determine_direction(entry, tp)
    direction_emoji = "🔴" if direction == "SELL" else "🟢" if direction == "BUY" else "⚪️"
    
    # สร้าง message
    message = (
        f"{direction_emoji} <b>{direction}</b>\n"
        f"———————————————————\n"
        f"📊 <b>Analysis:</b>\n"
        f"🎯 <b>Entry:</b> {entry:,.2f}\n"
        f"📈 <b>TP:</b> {tp:,.2f}\n"
        f"🛑 <b>SL:</b> {sl:,.2f}\n"
        f"💡 <b>Reason:</b> {reason}"
    )
    
    return message


def format_trade_analysis_html(json_response: dict) -> str:
    """
    แปลง Gemini JSON → HTML format สำหรับ Telegram parse_mode="HTML"
    (เหมือนกับ format_trade_analysis แต่เอา Markdown ออก)
    """
    return format_trade_analysis(json_response)


def parse_gemini_json_response(raw_text: str) -> dict | None:
    """
    พยายามแยก JSON จากข้อความ Gemini response
    รองรับ JSON embedded ใน markdown code blocks หรือ plain JSON
    """
    import re
    
    # ลอง 1: หา json code block (```json ... ```)
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # ลอง 2: หา JSON object ตรง ({...})
    json_match = re.search(r'\{.*?\}', raw_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    # ลอง 3: parse เป็น JSON ทั้งหมด
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("Cannot parse Gemini response as JSON")
        return None


if __name__ == "__main__":
    # ทดสอบ
    test_json = {
        "entry": 2100.50,
        "tp": 2150.00,
        "sl": 2080.00,
        "reason": "Support level breakdown + lower lows, bearish sentiment"
    }
    
    print(format_trade_analysis(test_json))
    print("\n" + "="*50 + "\n")
    
    # ทดสอบ SELL
    test_sell = {
        "entry": 2150.00,
        "tp": 2100.00,
        "sl": 2170.00,
        "reason": "Resistance rejected, supply zone"
    }
    print(format_trade_analysis(test_sell))
