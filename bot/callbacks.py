"""bot/callbacks.py — Telegram inline keyboard callbacks (TP/SL/Miss) + RR/PnL input flow"""
import logging

import telebot
from telebot.types import ForceReply

import config
from services import journal
from utils.text import clean_gemini_response

logger = logging.getLogger(__name__)

# ── State: เก็บ filename ที่รอ RR input ─────────────────────────────────────
# key = chat_id, value = {"filename": str, "result": str, "step": "rr"|"pnl"}
_pending_rr: dict[int, dict] = {}


def _is_authorized(chat_id) -> bool:
    return str(chat_id) == str(config.TELEGRAM_CHAT_ID)


def register_callbacks(bot: telebot.TeleBot) -> None:
    """ลงทะเบียน callback query handlers กับ bot instance"""

    # ── TP / SL / Miss ────────────────────────────────────────────────────
    @bot.callback_query_handler(func=lambda call: call.data.split("|")[0] in ("tp", "sl", "miss"))
    def handle_feedback(call):
        if not _is_authorized(call.message.chat.id):
            bot.answer_callback_query(call.id, "คุณไม่มีสิทธิ์ใช้งานปุ่มนี้")
            return

        try:
            action, filename = call.data.split("|", 1)
        except ValueError:
            bot.answer_callback_query(call.id, "ข้อมูลปุ่มไม่ถูกต้อง")
            return

        result_map = {
            "tp": "WIN (TP)",
            "sl": "LOSS (SL)",
            "miss": "MISSED (ไม่ได้เข้าเทรด)",
        }
        result_text = result_map[action]

        if action == "miss":
            # Miss ไม่ต้องถาม RR/PnL — บันทึกเลย
            journal.save_to_journal(
                filename=filename,
                result=result_text,
                analysis=call.message.text or "",
            )
            bot.answer_callback_query(call.id, f"บันทึก: {result_text} ✅")
            _update_message_text(bot, call, result_text)
            logger.info(f"📝 บันทึก: {result_text} | {filename}")
        else:
            # TP/SL → ถาม RR ก่อน
            _pending_rr[call.message.chat.id] = {
                "filename": filename,
                "result": result_text,
                "analysis": call.message.text or "",
                "step": "rr",
            }
            bot.answer_callback_query(call.id, "กรุณากรอก RR ratio")
            bot.send_message(
                call.message.chat.id,
                f"📥 กรอก Risk:Reward ratio สำหรับออเดอร์ {result_text}\nเช่น: 1:2 หรือ 1:1.5\n\n_(พิมพ์ - ถ้าไม่ต้องการบันทึก)_",
                parse_mode="Markdown",
                reply_markup=ForceReply(selective=True),
            )

    # ── รับ RR / PnL จากผู้ใช้ ───────────────────────────────────────────
    @bot.message_handler(func=lambda m: m.chat.id in _pending_rr)
    def handle_rr_pnl_input(message):
        state = _pending_rr.get(message.chat.id)
        if not state:
            return

        user_input = message.text.strip()

        if state["step"] == "rr":
            state["rr"] = "" if user_input == "-" else user_input
            state["step"] = "pnl"
            bot.reply_to(
                message,
                "💰 กรอก PnL เป็น USD เช่น: 10.5 หรือ -5\n_(พิมพ์ - ถ้าไม่ต้องการบันทึก)_",
                parse_mode="Markdown",
                reply_markup=ForceReply(selective=True),
            )
        elif state["step"] == "pnl":
            pnl = "" if user_input == "-" else user_input
            rr = state.get("rr", "")

            journal.save_to_journal(
                filename=state["filename"],
                result=state["result"],
                analysis=state["analysis"],
                rr=rr,
                pnl=pnl,
            )

            bot.reply_to(
                message,
                f"✅ บันทึกผลการเทรดแล้ว!\n"
                f"📋 Result: {state['result']}\n"
                f"📐 RR: {rr or '-'}\n"
                f"💰 PnL: {pnl or '-'} USD",
            )
            logger.info(f"📝 บันทึก RR={rr} PnL={pnl} | {state['filename']}")
            del _pending_rr[message.chat.id]


def _update_message_text(bot: telebot.TeleBot, call, result_text: str) -> None:
    """อัปเดตข้อความในข้อความต้นฉบับให้แสดงผลลัพธ์"""
    updated = f"{call.message.text}\n\n{'='*24}\n📝 บันทึกผลการเทรด: {result_text}"
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=updated,
        )
    except Exception as e:
        logger.warning(f"edit_message_text failed: {e}")
