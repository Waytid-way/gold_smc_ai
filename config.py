"""config.py — โหลดและรวม config ทั้งหมดจาก .env และ constants"""
import os
from dotenv import load_dotenv

load_dotenv()

# ───── API Keys ─────
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL      = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID  = os.getenv("TG_CHAT_ID")

# ───── Paths ─────
DOWNLOAD_DIR       = os.getenv("DOWNLOAD_DIR", r"C:\Users\com\Downloads")
SCREENSHOT_PATTERN = os.getenv("SCREENSHOT_PATTERN", "XAUUSD_*.png")
JOURNAL_FILE       = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading_journal.csv")
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
    "คุณคือเทรดเดอร์ SMC ชำนาญ XAUUSD ใช้แนวคิด BOS/CHoCH, OB, Liquidity\n"
    "รูปนี้คือ dashboard จาก indicator ของผม จงอ่านค่าและวิเคราะห์แบบ 'สั้น กระชับ ตรงประเด็นที่สุด'\n"
    "ตอบเพียงหัวข้อเหล่านี้ ห้ามเกริ่นนำ:\n"
    "🎯 Bias: [Bullish / Bearish / Neutral]\n"
    "📍 Entry: [ราคา]\n"
    "🛑 SL: [ราคา]\n"
    "💰 TP: [ราคา]\n"
    "💡 แผนการเทรด: [สรุปสั้นๆ 2-3 บรรทัด เช่น รอราคาย่อเข้า OB แล้ว Sell]"
)
