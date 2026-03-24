# 📈 TV Snap → Gemini → Telegram Bot

บอท Telegram ที่ช่วยให้คุณ **แคปจอ TradingView → วิเคราะห์ด้วย Gemini AI → ส่งผลกลับ Telegram** ได้ทันที พร้อมระบบ Trading Journal บันทึกผลลัพธ์ลง CSV

---

## 🚀 ฟีเจอร์หลัก

- **`/snap`** — สั่งแคปจอ TradingView อัตโนมัติ (จำลองการกด `Ctrl+Alt+S`)
- **Gemini AI** — วิเคราะห์กราฟ XAUUSD ตามแนวคิด SMC พร้อม **Conversation History** (ถามต่อเนื่องได้)
- **Custom Prompt** — ปรับ prompt ผ่าน `/prompt` ได้เลยโดยไม่ต้องแก้โค้ด
- **Inline Keyboard + RR/PnL** — กด 🟢 TP / 🔴 SL แล้วบอทจะถาม Risk:Reward และ PnL ก่อนบันทึก
- **`/stats`** — ดู Win Rate, PnL รวม พร้อมกราฟรายเดือน (matplotlib)
- **Pending Reminder** — แจ้งเตือนอัตโนมัติถ้ายังไม่ได้บันทึกผลออเดอร์หลัง X ชั่วโมง
- **Keyword Shortcut** — พิมพ์แค่ `snap` ก็ทำงานได้ ไม่ต้องพิมพ์ `/snap`

---

## 📁 โครงสร้างโปรเจกต์

```
code/
├── main.py                    # Entry point — รันบอท
├── config.py                  # API keys, constants, runtime state
├── requirements.txt           # Dependencies
├── bot/
│   ├── handlers.py            # /snap, /stats, /prompt, /clearchat, keyword
│   └── callbacks.py           # TP/SL/Miss + RR/PnL flow
├── services/
│   ├── screenshot.py          # pyautogui, win32gui fallback, wait_for_file
│   ├── gemini_api.py          # Gemini API + sliding-window conversation history
│   └── journal.py             # CSV read/write, stats, matplotlib chart
├── utils/
│   └── text.py                # escape_markdown, clean_gemini_response
├── trading_journal.csv        # บันทึกผลการเทรด (สร้างอัตโนมัติ)
├── bot.log                    # Log file (สร้างอัตโนมัติ, rotating 5MB×3)
└── .env                       # API Keys (ไม่ commit ขึ้น Git)
```

---

## ⚙️ การติดตั้ง

### 1. สร้าง Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt
```

### 3. ตั้งค่าไฟล์ `.env`

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash-lite
TG_BOT_TOKEN=your_telegram_bot_token_here
TG_CHAT_ID=your_telegram_chat_id_here

# Optional
DOWNLOAD_DIR=C:\Users\com\Downloads
SCREENSHOT_PATTERN=XAUUSD_*.png
PENDING_ALERT_HOURS=4
```

| ตัวแปร | คำอธิบาย |
|--------|-----------|
| `GEMINI_API_KEY` | API Key จาก [Google AI Studio](https://aistudio.google.com/) |
| `GEMINI_MODEL` | ชื่อโมเดล Gemini |
| `TG_BOT_TOKEN` | Token จาก [@BotFather](https://t.me/BotFather) |
| `TG_CHAT_ID` | Chat ID ของคุณ (หาได้จาก [@userinfobot](https://t.me/userinfobot)) |

---

## ▶️ วิธีรัน

```bash
.venv\Scripts\activate
python main.py
```

---

## 📱 คำสั่ง Telegram

| คำสั่ง | ฟังก์ชัน |
|--------|----------|
| `/snap` หรือพิมพ์ `snap` | แคปจอ TradingView แล้วส่ง Gemini วิเคราะห์ |
| `/stats` | ดูสถิติ Win Rate, PnL รวม + กราฟรายเดือน |
| `/prompt [ข้อความ]` | ปรับ prompt ที่ส่งให้ Gemini |
| `/prompt reset` | รีเซ็ต prompt กลับค่า default |
| `/clearchat` | ล้าง conversation history |
| ข้อความทั่วไป | ถาม Gemini ต่อเนื่องจาก analysis ล่าสุด |

---

## 📊 Trading Journal

ทุกครั้งที่กดปุ่มผลลัพธ์ ระบบจะถาม **RR** และ **PnL** ก่อนบันทึก:

| Date | Image File | Trade Result | RR | PnL_USD | AI Analysis |
|------|-----------|--------------|----|---------| ------------|
| 2026-03-25 10:00:00 | XAUUSD_1234.png | WIN (TP) | 1:2 | 10.50 | ... |

---

## ⚠️ ข้อควรระวัง

- เปิดหน้าต่าง TradingView ทิ้งไว้เป็น **Active Window** ก่อนสั่ง `/snap`
- ไฟล์ `.env` ห้าม commit ขึ้น Git เด็ดขาด

### `.gitignore` แนะนำ
```
.env
.venv/
bot.log
__pycache__/
*.pyc
```
