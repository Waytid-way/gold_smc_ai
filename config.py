"""config.py — โหลดและรวม config ทั้งหมดจาก .env และ constants"""
import os
from dotenv import load_dotenv

load_dotenv()

# ───── API Keys ─────
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL      = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID  = os.getenv("TG_CHAT_ID")

# ───── Web App ─────
# ต้องเป็น HTTPS เท่านั้น (ถ้ารัน local ต้องผ่าน ngrok)
_raw_url = os.getenv("WEBAPP_URL", "https://example.ngrok.app").strip()
if _raw_url and not _raw_url.startswith("http"):
    _raw_url = "https://" + _raw_url
WEBAPP_URL = _raw_url

# ───── Paths ─────
DOWNLOAD_DIR       = os.getenv("DOWNLOAD_DIR", r"C:\Users\com\Downloads")
SCREENSHOT_PATTERN = os.getenv("SCREENSHOT_PATTERN", "XAUUSD_*.png")
JOURNAL_FILE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading_journal.csv")
DB_FILE            = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading_journal.db")
LOG_FILE           = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log")

# ───── Keyboard VK Codes ─────
VK_CTRL        = 0x11
VK_ALT         = 0x12
VK_S           = 0x53
KEYEVENTF_KEYUP = 0x0002

# ───── Bot Behaviour ─────
CONVERSATION_HISTORY_LIMIT = 5   # จำนวน turns ที่เก็บใน memory
PENDING_ALERT_HOURS        = 4   # แจ้งเตือน pending trades หลังกี่ชั่วโมง
PENDING_CHECK_INTERVAL_SEC = 1800 # ตรวจทุก 30 นาที

# ───── Validation ─────
def validate():
    missing = [k for k, v in {
        "GEMINI_API_KEY": GEMINI_API_KEY,
        "TG_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TG_CHAT_ID": TELEGRAM_CHAT_ID,
    }.items() if not v]
    if missing:
        raise ValueError(f"❌ Missing required env vars: {', '.join(missing)}\nกรุณาตั้งค่าในไฟล์ .env")

# ───── Runtime mutable state (prompt ที่ผู้ใช้ปรับได้ผ่าน /prompt) ─────
custom_prompt: str = ""

BASE_PROMPT = (
    "คุณคือเทรดเดอร์ SMC ชำนาญ XAUUSD ใช้แนวคิด BOS/CHoCH, OB, Liquidity, Premium/Discount\n"
    "รูปนี้คือ dashboard จากตัวบ่งชี้ที่สะสม Bias, OB, Liquidity, FVG, RSI ฯลฯ\n\n"
    "📋 ให้ตอบเป็น JSON เท่านั้น โดยไม่มีข้อความอื่น:\n\n"
    "{\n"
    '  "entry": <เลขตัวเลขราคาเข้า>,\n'
    '  "tp": <เลขตัวเลขราคา Take Profit>,\n'
    '  "sl": <เลขตัวเลขราคา Stop Loss>,\n'
    '  "reason": "<สรุป 30-50 คำ: เหตุผลของ Trade Setup นี้ เช่น Support breakdown, Bearish OB, ลิควิดิตี้พร้อม>"\n'
    "}\n\n"
    "⚠️ IMPORTANT:\n"
    "- ให้ตอบแค่ JSON object เท่านั้น ไม่มี markdown code blocks หรือข้อความเพิ่มเติม\n"
    "- ราคาต้องเป็นตัวเลขเท่านั้น (เช่น 2100.50 ไม่ใช่ '2100.50 USD')\n"
    "- reason ต้องเป็น string เท่านั้น ห้ามใส่ emoji\n"
    "- ถ้าหากไม่มีสัญญาณชัดเจน ให้ตอบ null แทนราคา"
)
