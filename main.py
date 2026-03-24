"""main.py — Entry point: ประกอบ bot, ลงทะเบียน handlers, เริ่ม background tasks"""
import io
import logging
import logging.handlers
import threading
import time

import telebot

import config
from bot.handlers import register_handlers
from bot.callbacks import register_callbacks
from services import journal

# ───── Logging Setup ────────────────────────────────────────────────────────
def setup_logging():
    fmt = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    # Rotating file handler (5 MB × 3 files)
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(console)
    root.addHandler(file_handler)

    # ลด noise จาก telebot และ urllib3
    logging.getLogger("telebot").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


# ───── Pending Trade Reminder ────────────────────────────────────────────────
def _pending_reminder_loop(bot: telebot.TeleBot):
    """background thread: เช็ค pending trades และส่งแจ้งเตือน"""
    while True:
        time.sleep(config.PENDING_CHECK_INTERVAL_SEC)
        try:
            pending = journal.get_pending_trades(hours=config.PENDING_ALERT_HOURS)
            if not pending:
                continue
            lines = [f"⏰ *แจ้งเตือน: มีออเดอร์ที่ยังไม่ได้บันทึกผล {len(pending)} รายการ*\n"]
            for row in pending[:5]:  # แสดงสูงสุด 5 รายการ
                lines.append(f"• {row.get('Date', '?')} — `{row.get('Image File', '?')}`")
            if len(pending) > 5:
                lines.append(f"_(และอีก {len(pending)-5} รายการ)_")
            lines.append("\nพิมพ์ /stats เพื่อดูสถิติภาพรวม")
            bot.send_message(config.TELEGRAM_CHAT_ID, "\n".join(lines), parse_mode="Markdown")
            logger.info(f"📨 ส่งแจ้งเตือน pending trades {len(pending)} รายการ")
        except Exception as e:
            logger.error(f"pending_reminder_loop error: {e}")


# ───── Main ─────────────────────────────────────────────────────────────────
def main():
    setup_logging()
    config.validate()

    bot = telebot.TeleBot(config.TELEGRAM_BOT_TOKEN)

    register_handlers(bot)
    register_callbacks(bot)

    # เริ่ม background reminder thread
    reminder = threading.Thread(
        target=_pending_reminder_loop, args=(bot,), daemon=True, name="PendingReminder"
    )
    reminder.start()
    logger.info("⏰ Pending Trade Reminder thread เริ่มทำงาน")

    logger.info("=" * 55)
    logger.info("TV → GEMINI → TELEGRAM (BOT MODE)")
    logger.info("🤖 บอท Telegram พร้อมทำงานแล้ว!")
    logger.info("📱 คำสั่งที่ใช้ได้: /snap, /stats, /prompt, /clearchat")
    logger.info("💡 Keyword: พิมพ์ 'snap' เพื่อแคปจอโดยไม่ต้องใช้ /")
    logger.info("🛑 กด Ctrl+C เพื่อหยุด")
    logger.info("=" * 55)

    bot.infinity_polling()


if __name__ == "__main__":
    main()
