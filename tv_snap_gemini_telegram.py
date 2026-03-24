# tv_snap_gemini_telegram.py
# สั่งงานผ่าน Telegram ด้วยคำสั่ง /snap -> จำลองกด Ctrl+Alt+S -> ส่ง Gemini -> ส่งกลับ Telegram
# + ระบบ Trading Journal (บันทึกผลลัพธ์การเทรดลงไฟล์ CSV)

import os
import glob
import base64
import csv
import time
import ctypes
from datetime import datetime
import requests
import pyautogui
import pygetwindow as gw
import webbrowser
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# โหลดค่าจากไฟล์ .env
load_dotenv()

# ───────────────── CONFIG ─────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
TELEGRAM_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TELEGRAM_CHAT_ID   = os.getenv("TG_CHAT_ID")

DOWNLOAD_DIR = r"C:\Users\com\Downloads"
SCREENSHOT_PATTERN = "XAUUSD_*.png"
JOURNAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trading_journal.csv")

VK_CTRL = 0x11
VK_ALT = 0x12
VK_S = 0x53
KEYEVENTF_KEYUP = 0x0002

# Validate Telegram Bot Token
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is not set. Please check your .env file.")

# Initialize Telegram Bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# ───────────────── ESCAPE MARKDOWN ─────────────────
def escape_markdown(text: str, version: int = 1) -> str:
    """Escape special characters for Telegram Markdown V1."""
    if version == 1:
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '|', '{', '}', '.']
    else:
        escape_chars = ['_', '*', '[', ']', '(', ')']  # Minimal escape for better formatting

    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

# ───────────────── UTILITIES ─────────────────
def wait_for_new_screenshot(timeout: int = 30, trigger_time: float | None = None) -> str:
    """รอไฟล์ใหม่หลังจากส่งคำสั่งแคปจอ"""
    pattern = os.path.join(DOWNLOAD_DIR, SCREENSHOT_PATTERN)
    before_files = glob.glob(pattern)
    before = {
        path: (os.path.getmtime(path), os.path.getsize(path))
        for path in before_files
        if os.path.exists(path)
    }
    start  = time.time()

    print(f"[DEBUG] 📂 Scanning directory: {DOWNLOAD_DIR}")
    print(f"[DEBUG] 🔍 Target Pattern: {SCREENSHOT_PATTERN}")
    print(f"[DEBUG] 📄 Files already exist: {len(before)}")
    if trigger_time is not None:
        print(f"[DEBUG] ⏱️ Trigger time: {time.ctime(trigger_time)}")

    if trigger_time is not None:
        for path in before.keys():
            current_mtime = os.path.getmtime(path)
            current_size = os.path.getsize(path)
            if current_mtime >= (trigger_time - 0.25) and current_size > 0:
                print(
                    f"[DEBUG] ⚡ Pre-scan match: {path} "
                    f"(Modified: {time.ctime(current_mtime)}, Size: {current_size} bytes)"
                )
                return path

    while time.time() - start < timeout:
        time.sleep(0.5)  # Reduced from 1 second to 0.5 seconds for faster polling
        after_files = glob.glob(pattern)
        for path in after_files:
            if not os.path.exists(path):
                continue

            current_mtime = os.path.getmtime(path)
            current_size = os.path.getsize(path)
            previous = before.get(path)
            is_after_trigger = trigger_time is not None and current_mtime >= (trigger_time - 0.25)

            if previous is None and is_after_trigger:
                print(f"[DEBUG] ✨ New File Detected: {path} (Size: {current_size} bytes)")
                time.sleep(1)  # Reduced from 1.5 seconds to 1 second for faster confirmation
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    print(f"[INFO] 📸 พบไฟล์รูปใหม่: {path}")
                    return path

            if previous is not None:
                previous_mtime, previous_size = previous
            else:
                previous_mtime, previous_size = 0.0, 0

            if is_after_trigger and (current_mtime > previous_mtime or current_size != previous_size):
                print(
                    f"[DEBUG] ✨ Modified Screenshot Detected: {path} "
                    f"(Old: {time.ctime(previous_mtime)}, New: {time.ctime(current_mtime)}, Size: {current_size} bytes)"
                )
                time.sleep(1)  # Reduced from 1.5 seconds to 1 second for faster confirmation
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    print(f"[INFO] 📸 พบไฟล์รูปที่อัปเดตแล้ว: {path}")
                    return path

    print("[ERROR] ❌ Timeout reached. Listing last 5 files in Downloads for diagnosis:")
    all_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.*"))
    latest_files = sorted(all_files, key=os.path.getmtime, reverse=True)[:5]
    for file_path in latest_files:
        print(f"  - {os.path.basename(file_path)} (Modified: {time.ctime(os.path.getmtime(file_path))})")

    raise TimeoutError("ไม่พบไฟล์ screenshot ใหม่ภายในเวลาที่กำหนด")

def call_gemini_image(image_path: str, base_prompt: str) -> str:
    """ส่งรูปเข้า Gemini 3.1 Flash-Lite"""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"ไม่พบไฟล์รูป: {image_path}")

    with open(image_path, "rb") as f:
        img_bytes = f.read()

    img_b64 = base64.b64encode(img_bytes).decode("utf-8")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    headers = {"Content-Type": "application/json"}

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": base_prompt},
                    {"inline_data": {"mime_type": "image/png", "data": img_b64}}
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 1024,
        },
    }

    params = {"key": GEMINI_API_KEY}
    resp = requests.post(url, headers=headers, json=payload, params=params, timeout=45)
    resp.raise_for_status()
    data = resp.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return str(data)

def clean_gemini_response(text: str) -> str:
    """ทำความสะอาด response จาก Gemini ก่อนส่งไปยัง Telegram
    - ลบ markdown ที่ Gemini สร้างมา เช่น **bold**, ##heading
    - ตัดช่องว่างซ้ำและบรรทัดว่างเกิน
    """
    import re
    # ลบ heading markdown (## / ### ฯลฯ)
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
    # ลบ bold/italic (**text**, *text*, __text__, _text_)
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", text)
    # ลบ inline code backtick
    text = re.sub(r"`(.+?)`", r"\1", text)
    # ลดบรรทัดว่างซ้ำ (เกิน 2 บรรทัดติดกัน)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def save_to_journal(filename: str, result: str, analysis: str):
    """บันทึกข้อมูลการเทรดลงไฟล์ CSV"""
    file_exists = os.path.isfile(JOURNAL_FILE)

    with open(JOURNAL_FILE, mode="a", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["Date", "Image File", "Trade Result", "AI Analysis"])

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, filename, result, analysis])

def send_ctrl_alt_s() -> None:
    """ส่งคีย์ลัด Ctrl+Alt+S ด้วย WinAPI เพื่อความเสถียรบน Windows"""
    user32 = ctypes.windll.user32

    print("[INFO] ⌨️ Sending Ctrl+Alt+S via WinAPI...")
    user32.keybd_event(VK_CTRL, 0, 0, 0)
    print("[DEBUG] ⌨️ keyDown(ctrl)")
    user32.keybd_event(VK_ALT, 0, 0, 0)
    print("[DEBUG] ⌨️ keyDown(alt)")
    time.sleep(0.1)  # Reduced from 0.15 to 0.1 for faster execution
    user32.keybd_event(VK_S, 0, 0, 0)
    print("[DEBUG] ⌨️ keyDown(s)")
    user32.keybd_event(VK_S, 0, KEYEVENTF_KEYUP, 0)
    print("[DEBUG] ⌨️ keyUp(s)")
    user32.keybd_event(VK_ALT, 0, KEYEVENTF_KEYUP, 0)
    print("[DEBUG] ⌨️ keyUp(alt)")
    user32.keybd_event(VK_CTRL, 0, KEYEVENTF_KEYUP, 0)
    print("[DEBUG] ⌨️ keyUp(ctrl)")


# ───────────────── TELEGRAM COMMAND HANDLER ─────────────────

is_processing = False

@bot.message_handler(commands=['snap'])
def handle_snap_command(message):
    global is_processing
    """ฟังก์ชันนี้จะทำงานทันทีที่คุณพิมพ์ /snap ใน Telegram"""
    
    # 1. ตรวจสอบสิทธิ์ (ทำรายการได้เฉพาะ Chat ID ของคุณเท่านั้น)
    if str(message.chat.id) != str(TELEGRAM_CHAT_ID):
        bot.reply_to(message, "⛔️ คุณไม่มีสิทธิ์ใช้งานคำสั่งนี้")
        print(f"[WARN] Unauthorized access attempt from Chat ID: {message.chat.id}")
        return

    if is_processing:
        bot.reply_to(message, "⏳ บอทกำลังประมวลผลคำสั่งก่อนหน้า กรุณารอสักครู่...")
        print("[WARN] ปฏิเสธคำสั่งซ้ำ เนื่องจากกำลังทำงานอยู่")
        return

    is_processing = True

    bot.reply_to(message, "⚙️ สั่งแคปหน้าจอ TradingView แล้ว! กำลังรอระบบประมวลผล...")
    print("\n[INFO] 🚀 ได้รับคำสั่ง /snap จาก Telegram")

    try:
        # 2. จำลองการกดคีย์บอร์ด Ctrl + Alt + S
        bot.send_message(message.chat.id, "🔍 กำลังสลับหน้าจอไปที่ TradingView อัตโนมัติ...")
        print("[INFO] 🔍 ค้นหาหน้าต่าง TradingView...")

        tv_windows = gw.getWindowsWithTitle("TradingView")
        if not tv_windows:
            tv_windows = gw.getWindowsWithTitle("XAUUSD")

        if tv_windows:
            win = tv_windows[0]
            try:
                if win.isMinimized:
                    win.restore()
                win.activate()
                if not win.isMaximized:
                    win.maximize()
                print(f"[INFO] ✅ สลับไปที่หน้าต่าง: {win.title}")
            except Exception as e:
                print(f"[WARN] ไม่สามารถดึงหน้าต่างได้ ({e})")

            time.sleep(1.5)

            print("[INFO] 🖱️ คลิกบนหน้าต่าง Chrome เพื่อโฟกัส...")
            win_top_x = win.left + 10  # Click near the top-left corner
            win_top_y = win.top + 10

            if win_top_x > 0 and win_top_y > 0:
                pyautogui.click(win_top_x, win_top_y)
                time.sleep(0.5)
        else:
            print("[INFO] 🌐 ไม่พบหน้าต่างที่เปิดอยู่ กำลังเปิด URL ใหม่...")
            target_url = "https://www.tradingview.com/chart/Q5l4KMA2/?symbol=PEPPERSTONE%3AXAUUSD"
            webbrowser.open(target_url)
            bot.send_message(message.chat.id, "🌐 กำลังเปิดหน้าเว็บใหม่ รอโหลดกราฟสักครู่...")
            time.sleep(10)

            screen_w, screen_h = pyautogui.size()
            pyautogui.click(screen_w / 2, screen_h / 2)
            time.sleep(0.5)

        time.sleep(0.5)

        active_win = gw.getActiveWindow()
        active_title = active_win.title if active_win else "None"
        print(f"[DEBUG] 🎯 Actual Active Window: {active_title}")

        capture_trigger_time = time.time()

        for attempt in range(1, 4):
            print(f"[INFO] ⌨️ Sending Ctrl+Alt+S... attempt {attempt}/3")
            send_ctrl_alt_s()
            time.sleep(0.75)
            after_active_win = gw.getActiveWindow()
            after_title = after_active_win.title if after_active_win else "None"
            print(f"[DEBUG] 🎯 Active Window after attempt {attempt}: {after_title}")
            if after_active_win and "Chrome" in after_title:
                break

        # 3. รอไฟล์รูปเกิดใหม่
        img_path = wait_for_new_screenshot(timeout=30, trigger_time=capture_trigger_time)
        filename = os.path.basename(img_path)

        # 4. ส่งให้ Gemini
        bot.send_message(message.chat.id, "🧠 แคปจอสำเร็จ! ส่งให้ Gemini วิเคราะห์ต่อ...")
        print("[INFO] Calling Gemini...")
        
        base_prompt = (
            "คุณคือเทรดเดอร์ SMC มืออาชีพ ชำนาญ XAUUSD ใช้แนวคิด BOS/CHoCH, "
            "Order Block, Liquidity, FVG, Premium/Discount.\n\n"
            "รูปนี้คือ dashboard จาก indicator ของผมที่รวม bias, OB, liquidity, FVG, RSI ฯลฯ "
            "ให้คุณอ่านข้อมูลทั้งหมดจากรูปทันที:\n"
        )
        
        start = time.time()
        analysis = call_gemini_image(img_path, base_prompt)
        elapsed = time.time() - start
        print(f"[INFO] Gemini ตอบกลับใน {elapsed:.1f} วินาที")

        # 5. Process Gemini response and send back to chat
        cleaned_analysis = clean_gemini_response(analysis)
        safe_analysis = escape_markdown(cleaned_analysis, version=2)
        reply_text = f"*ผลการวิเคราะห์ XAUUSD*\n\n{safe_analysis}"

        markup = InlineKeyboardMarkup()
        markup.row_width = 3
        markup.add(
            InlineKeyboardButton("🟢 TP (Win)", callback_data=f"tp|{filename}"),
            InlineKeyboardButton("🔴 SL (Loss)", callback_data=f"sl|{filename}"),
            InlineKeyboardButton("⚪️ ไม่ได้เข้า", callback_data=f"miss|{filename}"),
        )
        
        try:
            # แผน A: ลองส่งแบบจัดหน้ากระดาษ Markdown
            bot.send_message(message.chat.id, reply_text, parse_mode="Markdown", reply_markup=markup)
            print("[DONE] ส่งผลลัพธ์แบบ Markdown สำเร็จ")
        except Exception as e:
            print(f"[WARN] Telegram จัดฟอร์แมตไม่ได้ ({e}) -> กำลังส่งใหม่แบบสลับเป็นข้อความธรรมดา")
            # แผน B: ถ้าฟอร์แมตพัง ให้ส่งเป็นข้อความธรรมดาทันที
            bot.send_message(message.chat.id, reply_text, reply_markup=markup)
            print("[DONE] ส่งผลลัพธ์แบบข้อความธรรมดาสำเร็จ")

    # 👇 นำ except 2 บล็อกนี้กลับมาเพื่อรับกับ try ในขั้นตอนที่ 2
    except TimeoutError:
        error_msg = "❌ **Error:** ไม่พบไฟล์รูปใหม่\nกรุณาเช็คว่าเปิดหน้าต่าง TradingView ค้างไว้และเป็นหน้าต่างหลัก (Active Window) หรือไม่"
        bot.send_message(message.chat.id, error_msg)
        print("[ERROR] Timeout: ไม่เจอไฟล์รูปใหม่")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ **เกิดข้อผิดพลาด:** {e}")
        print(f"[ERROR] {e}")
    finally:
        is_processing = False
        print("[INFO] ปลดล็อกสถานะการทำงาน พร้อมรับคำสั่งใหม่")


# ───────────────── TELEGRAM CALLBACK HANDLER (รับค่าจากปุ่มกด) ─────────────────
@bot.callback_query_handler(func=lambda call: True)
def handle_feedback(call):
    """ฟังก์ชันนี้จะทำงานเมื่อคุณกดปุ่ม TP / SL / ไม่ได้เข้า"""
    if str(call.message.chat.id) != str(TELEGRAM_CHAT_ID):
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
    result_text = result_map.get(action, "Unknown")
    analysis_text = call.message.text

    save_to_journal(filename, result_text, analysis_text)

    bot.answer_callback_query(call.id, f"บันทึกผลลัพธ์: {result_text} ลง Journal แล้ว! 📝")
    print(f"[INFO] 📝 บันทึกผลลัพธ์ {result_text} สำหรับไฟล์ {filename} เรียบร้อย")

    updated_text = f"{call.message.text}\n\n========================\n📝 บันทึกผลการเทรด: {result_text}"
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=updated_text,
    )


# ───────────────── MAIN ─────────────────
if __name__ == "__main__":
    # ตรวจสอบ API keys ให้เรียบร้อย
    if not GEMINI_API_KEY or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("❌ กรุณาตั้งค่า API Keys และ Chat ID ในไฟล์ .env ให้ครบถ้วน")
        
    print("========== TV → GEMINI → TELEGRAM (BOT MODE) ==========")
    print("🤖 บอท Telegram พร้อมทำงานแล้ว!")
    print("⚠️  ข้อควรระวัง: กรุณาเปิดหน้าต่าง TradingView ทิ้งไว้ให้เป็น 'หน้าต่างที่กำลังใช้งานอยู่' (Active Window)")
    print("📱 พิมพ์ /snap ในแชท Telegram ของคุณเพื่อทดสอบได้เลย")
    print("🛑 กด Ctrl+C เพื่อหยุดการทำงาน")
    
    # เปิดการเชื่อมต่อกับ Telegram ทิ้งไว้เพื่อรอรับคำสั่งตลอดเวลา
    bot.infinity_polling()