"""bot/handlers.py — Telegram command handlers: /snap, /stats, /prompt, /clearchat, keyword 'snap'"""
import io
import logging
import os
import time
import webbrowser

import pyautogui
import pygetwindow as gw
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply, WebAppInfo
from telebot.util import smart_split

import config
from services import screenshot as sc
from services import gemini_api
from services import journal
from services import formatter
from utils.text import clean_gemini_response
from bot.callbacks import _pending_rr

logger = logging.getLogger(__name__)

# ───── State ────────────────────────────────────────────────────────────────
is_processing = False  # ป้องกัน /snap ซ้อนกัน


# ───── Auth Helper ──────────────────────────────────────────────────────────
def _is_authorized(chat_id) -> bool:
    return str(chat_id) == str(config.TELEGRAM_CHAT_ID)


# ───── /snap (และ keyword 'snap') ───────────────────────────────────────────
def _do_snap(bot: telebot.TeleBot, chat_id: int, reply_to_msg_id: int | None = None) -> None:
    global is_processing
    if is_processing:
        bot.send_message(chat_id, "⏳ บอทกำลังประมวลผลคำสั่งก่อนหน้า กรุณารอสักครู่...")
        return

    is_processing = True
    logger.info("🚀 เริ่ม snap command")

    try:
        bot.send_message(chat_id, "⚙️ สั่งแคปหน้าจอ TradingView แล้ว! กำลังรอระบบประมวลผล...")

        # 1. Focus หน้าต่าง TradingView
        bot.send_message(chat_id, "🔍 กำลังสลับหน้าจอไปที่ TradingView...")
        focused = sc.focus_tradingview_window()

        if not focused:
            target_url = "https://www.tradingview.com/chart/Q5l4KMA2/?symbol=PEPPERSTONE%3AXAUUSD"
            webbrowser.open(target_url)
            bot.send_message(chat_id, "🌐 กำลังเปิดหน้าเว็บใหม่ รอโหลดกราฟสักครู่...")
            time.sleep(10)
            screen_w, screen_h = pyautogui.size()
            pyautogui.click(screen_w / 2, screen_h / 2)
            time.sleep(0.5)

        time.sleep(0.5)

        active_win = gw.getActiveWindow()
        logger.debug(f"🎯 Active Window: {active_win.title if active_win else 'None'}")

        capture_trigger_time = time.time()

        # 2. ส่ง Ctrl+Alt+S หลายครั้ง (retry)
        for attempt in range(1, 4):
            logger.info(f"⌨️ Ctrl+Alt+S attempt {attempt}/3")
            sc.send_ctrl_alt_s()
            time.sleep(0.75)
            after = gw.getActiveWindow()
            if after and "Chrome" in after.title:
                break

        # 3. รอไฟล์
        img_path = sc.wait_for_new_screenshot(timeout=30, trigger_time=capture_trigger_time)
        filename = os.path.basename(img_path)

        # 4. ส่งรูปเข้าแชท และส่งให้ Gemini
        bot.send_message(chat_id, "🧠 แคปจอสำเร็จ! อัปโหลดรูปและส่งให้ Gemini วิเคราะห์ต่อ...")
        try:
            with open(img_path, "rb") as photo:
                bot.send_photo(chat_id, photo)
        except Exception as e:
            logger.error(f"Cannot upload photo to Telegram: {e}")


        prompt = config.custom_prompt if config.custom_prompt else config.BASE_PROMPT
        t0 = time.time()
        analysis = gemini_api.call_gemini_image(img_path, prompt)
        logger.info(f"Gemini ตอบกลับใน {time.time() - t0:.1f}s")

        # 5. พยายามแยก JSON จาก response
        parsed_json = formatter.parse_gemini_json_response(analysis)
        
        if parsed_json:
            # ✅ JSON parse สำเร็จ
            logger.info(f"✅ Parsed JSON: {parsed_json}")
            formatted_msg = formatter.format_trade_analysis(parsed_json)
            reply_text = f"<b>📊 ผลการวิเคราะห์ XAUUSD</b>\n\n{formatted_msg}"
            
            # เก็บข้อมูล JSON ลง journal ด้วย
            trade_data = {
                "entry": parsed_json.get("entry"),
                "tp": parsed_json.get("tp"),
                "sl": parsed_json.get("sl"),
                "reason": parsed_json.get("reason")
            }
        else:
            # ❌ JSON parse ไม่สำเร็จ ใช้เหมือนเดิม
            logger.warning("⚠️ JSON parse failed, using raw text fallback")
            cleaned = clean_gemini_response(analysis)
            reply_text = f"<b>ผลการวิเคราะห์ XAUUSD</b>\n\n{cleaned}"
            trade_data = None

        markup = InlineKeyboardMarkup()
        markup.row_width = 3
        markup.add(
            InlineKeyboardButton("🟢 TP (Win)", callback_data=f"tp|{filename}"),
            InlineKeyboardButton("🔴 SL (Loss)", callback_data=f"sl|{filename}"),
            InlineKeyboardButton("⚪️ ไม่ได้เข้า", callback_data=f"miss|{filename}"),
        )

        msg_chunks = smart_split(reply_text, chars_per_string=3000)
        for i, chunk in enumerate(msg_chunks):
            is_last = (i == len(msg_chunks) - 1)
            current_markup = markup if is_last else None
            try:
                bot.send_message(
                    chat_id, chunk, parse_mode="HTML", reply_markup=current_markup
                )
            except Exception:
                bot.send_message(chat_id, chunk, reply_markup=current_markup)

        # บันทึกลง journal ด้วย Trade Result ว่าง (จะอัปเดตเมื่อกดปุ่ม)
        # เก็บ JSON data ถ้ามี
        journal.save_to_journal(filename, "", analysis, trade_data=trade_data)

    except TimeoutError:
        bot.send_message(
            chat_id,
            "❌ ไม่พบไฟล์รูปใหม่\nกรุณาเช็คว่าเปิดหน้าต่าง TradingView ทิ้งไว้หรือไม่",
        )
        logger.error("Timeout: ไม่เจอไฟล์รูปใหม่")
    except Exception as e:
        bot.send_message(chat_id, f"❌ เกิดข้อผิดพลาด: {e}")
        logger.exception(f"snap error: {e}")
    finally:
        is_processing = False
        logger.info("ปลดล็อกสถานะ พร้อมรับคำสั่งใหม่")


def register_handlers(bot: telebot.TeleBot) -> None:
    """ลงทะเบียน handlers ทั้งหมดกับ bot instance"""

    # ── /snap ──────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["snap"])
    def handle_snap(message):
        if not _is_authorized(message.chat.id):
            bot.reply_to(message, "⛔️ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
            return
        _do_snap(bot, message.chat.id)

    # ── Keyword shortcut: ส่งแค่ 'snap' ────────────────────────────────────
    @bot.message_handler(func=lambda m: m.text and m.text.strip().lower() == "snap")
    def handle_snap_keyword(message):
        if not _is_authorized(message.chat.id):
            return
        _do_snap(bot, message.chat.id)

    # ── /stats ─────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["stats"])
    def handle_stats(message):
        if not _is_authorized(message.chat.id):
            return
        stats = journal.get_stats()
        if stats["total"] == 0:
            bot.send_message(message.chat.id, "📭 ยังไม่มีข้อมูลการเทรดใน Journal ครับ")
            return
            
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📊 เปิดดู PnL รายเดือน (Grid)", web_app=WebAppInfo(url=config.WEBAPP_URL)))
        
        bot.send_message(message.chat.id, journal.format_stats_text(stats), reply_markup=markup)

        chart_bytes = journal.generate_stats_chart()
        if chart_bytes:
            bot.send_photo(message.chat.id, io.BytesIO(chart_bytes), caption="📊 กราฟผลการเทรดรายเดือน")

    # ── /prompt ────────────────────────────────────────────────────────────
    @bot.message_handler(commands=["prompt"])
    def handle_prompt(message):
        if not _is_authorized(message.chat.id):
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or parts[1].strip().lower() == "reset":
            config.custom_prompt = ""
            bot.reply_to(message, "✅ รีเซ็ต prompt กลับเป็นค่า default แล้ว")
            return
        config.custom_prompt = parts[1].strip()
        preview = config.custom_prompt[:100] + ("..." if len(config.custom_prompt) > 100 else "")
        bot.reply_to(message, f"✅ บันทึก Custom Prompt แล้ว:\n\n_{preview}_", parse_mode="Markdown")

    # ── /clearchat ─────────────────────────────────────────────────────────
    @bot.message_handler(commands=["clearchat"])
    def handle_clearchat(message):
        if not _is_authorized(message.chat.id):
            return
        gemini_api.clear_history()
        bot.reply_to(message, "🗑️ ล้าง Conversation History แล้ว Gemini จะเริ่มตอบโดยไม่จำบริบทก่อนหน้าครับ")

    # ── /clear_pending ─────────────────────────────────────────────────────
    @bot.message_handler(commands=["clear_pending"])
    def handle_clear_pending(message):
        if not _is_authorized(message.chat.id):
            return

        deleted = journal.delete_pending_trades()

        if deleted == 0:
            bot.reply_to(message, "✅ ไม่มีออเดอร์ค้างในระบบเลยครับ")
        else:
            bot.reply_to(message, f"🗑️ ล้างออเดอร์ที่ยังไม่ได้บันทึกผล (Pending) ไปแล้วจำนวน {deleted} รายการครับ!")

    # ── /clear_history ─────────────────────────────────────────────────────
    @bot.message_handler(commands=["clear_history"])
    def handle_clear_history(message):
        if not _is_authorized(message.chat.id):
            return

        je_deleted, sc_deleted = journal.clear_all_history()
        
        bot.reply_to(
            message,
            f"🧹 **เคลียร์ประวัติเก่าทั้งหมดเรียบร้อยแล้ว!**\n\n"
            f"• รายการเทรด (Journal): ลบ `{je_deleted}` รายการ\n"
            f"• รูปภาพ (Screenshots): ลบ `{sc_deleted}` รายการ\n\n"
            f"✨ พิมพ์ `/stats` เพื่อแสดงตารางที่ว่างเปล่าได้เลยครับ",
            parse_mode="Markdown"
        )

    # ── Follow-up text (ถามต่อเนื่องจาก analysis) ──────────────────────────
    @bot.message_handler(func=lambda m: (
        _is_authorized(m.chat.id)
        and m.text
        and not m.text.startswith("/")
        and m.text.strip().lower() != "snap"
        and m.chat.id not in _pending_rr
        and gemini_api.get_history_length() > 0
    ))
    def handle_followup(message):
        try:
            bot.send_chat_action(message.chat.id, "typing")
            answer = gemini_api.call_gemini_text(message.text)
            cleaned = clean_gemini_response(answer)
            msg_chunks = smart_split(cleaned, chars_per_string=3000)
            for i, chunk in enumerate(msg_chunks):
                if i == 0:
                    bot.reply_to(message, chunk, parse_mode="HTML")
                else:
                    bot.send_message(message.chat.id, chunk, parse_mode="HTML")
        except Exception as e:
            bot.reply_to(message, f"❌ เกิดข้อผิดพลาด: {e}")
            logger.exception(f"followup error: {e}")
