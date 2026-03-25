# 📈 TV Snap → Gemini → Telegram Bot (SQLite Edition)

บอท Telegram ที่ช่วยให้คุณ **แคปจอ TradingView → วิเคราะห์ด้วย Gemini AI → ส่งผลกลับ Telegram** ได้ทันที พร้อมระบบ Trading Journal ที่ขับเคลื่อนด้วย **SQLite (3rd Normal Form Architecture)** เพื่อประสิทธิภาพและความถูกต้องของข้อมูลสูงสุด

---

## 🚀 ฟีเจอร์หลัก

- **`/snap`** — สั่งแคปจอ TradingView อัตโนมัติ (จำลองการกด `Ctrl+Alt+S`)
- **🟢 Gemini AI (JSON Output)** — วิเคราะห์กราฟ XAUUSD ตามแนวคิด SMC พร้อม:
  - **JSON Enforcement**: Gemini บังคับส่ง JSON format `{entry, tp, sl, reason}`
  - **Auto SELL/BUY Detection**: ระบบอัตโนมัติแยกแยะว่าเป็น BUY 🟢 หรือ SELL 🔴 จากราคา Entry vs TP
  - **Structured Data Storage**: บันทึก entry_price, tp_price, sl_price, trade_reason เป็นโครงสร้างใน Database
  - **Conversation History**: ถามต่อเนื่องได้
- **Custom Prompt** — ปรับ prompt ผ่าน `/prompt` ได้เลยโดยไม่ต้องแก้โค้ด
- **Automated Trading Journal (SQLite)** — บันทึกข้อมูลแบบ Relational Database (3NF) รองรับ UPSERT, ป้องกัน Update Anomaly และ Query สถิติด้วย SQL Aggregates ที่รวดเร็ว
- **One-time CSV Migration** — ระบบจะดึงข้อมูลจาก `trading_journal.csv` เดิมเข้าสู่ DB ใหม่โดยอัตโนมัติเมื่อรันครั้งแรก
- **Inline Keyboard + RR/PnL** — กด 🟢 TP / 🔴 SL แล้วบอทจะถาม Risk:Reward และ PnL ก่อนบันทึก
- **`/stats` & `/clear_pending`** — ดู Win Rate, PnL รวม พร้อมกราฟรายเดือน หรือกวาดล้างออเดอร์ค้างได้ในคลิกเดียว
- **Pending Reminder** — แจ้งเตือนอัตโนมัติถ้ายังไม่ได้บันทึกผลออเดอร์หลัง X ชั่วโมง
- **🌐 Web Mini App** — Dashboard แสดง Trade History, สถิติ, และระบบ Report/Flag เพื่อรายงานข้อผิดพลาด

---

## 📁 โครงสร้างโปรเจกต์ & ฐานข้อมูล

```
code/
├── main.py                    # Entry point — รันบอท + DB Init/Migration
├── config.py                  # API keys, constants, DB_FILE path, prompt templates
├── requirements.txt           # Dependencies
├── web_server.py              # Flask server สำหรับ Mini App + API endpoints
├── db/                        # Database Layer
│   └── schema.sql             # SQLite DDL (3NF Schema)
├── bot/
│   ├── handlers.py            # /snap, /stats, /prompt, /clearchat commands
│   └── callbacks.py           # TP/SL/Miss + RR/PnL flow + Report system
├── services/
│   ├── db.py                  # SQLite Connection Manager & CSV Migration
│   ├── screenshot.py          # pyautogui, win32gui fallback
│   ├── gemini_api.py          # Gemini API + sliding-window history
│   ├── formatter.py           # JSON parser + Telegram message formatter (NEW)
│   └── journal.py             # SQLite UPSERT, SQL Aggregates, charts
├── utils/
│   └── text.py                # HTML escape, number parsing
├── webapp/                    # Web Mini App (Flask frontend)
│   ├── app.js                 # Dashboard + History + Admin
│   ├── history.js             # History page logic + Report modal
│   ├── admin.js               # Admin dashboard for reports
│   ├── index.html             # Dashboard view
│   ├── history.html           # History page with detailed trades
│   ├── admin.html             # Admin panel for reports
│   └── style.css              # Glassmorphism styling
├── trading_journal.db         # Primary Database (SQLite WAL mode)
├── migrate_db.py              # Migration script for new columns (NEW)
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
| `/clear_pending` | ล้างออเดอร์ที่ค้างและยังไม่มีผลลัพธ์ออกจาก Database |
| `/clear_history` | ล้างประวัติเทรดเก่าทั้งหมด (รีเซ็ตทั้งใน DB และลบแคช CSV) |
| ข้อความทั่วไป | ถาม Gemini ต่อเนื่องจาก analysis ล่าสุด |

---

## � 3-Step Architecture: Gemini JSON → Formatter → Database

ระบบทำงานเป็น 3 ขั้นตอน เพื่อให้ข้อมูล "สะอาด" และ "มีโครงสร้าง":

```
┌─────────────────┐
│ TradingView     │
│   Screenshot    │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ Step 1: Gemini AI (NEW JSON Prompt) │
│ รับ: Screenshot image               │
│ ส่งออก: JSON format                 │
│ {                                   │
│   "entry": 2100.50,                 │
│   "tp": 2150.00,                    │
│   "sl": 2080.00,                    │
│   "reason": "Support + OB"          │
│ }                                   │
└────────┬────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Step 2: Formatter Module             │
│ • Parse JSON (handles markdown)      │
│ • Auto-detect BUY/SELL direction     │
│ • Format for Telegram display        │
│                                      │
│ 🟢 BUY                               │
│ ———————————————                      │
│ 📊 Analysis:                         │
│ 🎯 Entry: 2,100.50                   │
│ 📈 TP: 2,150.00                      │
│ 🛑 SL: 2,080.00                      │
│ 💡 Reason: Support + OB...           │
└────────┬───────────────────────────┘
         │
         ▼
┌──────────────────────────────────────┐
│ Step 3: Database Storage             │
│ • Store structured entry_price       │
│ • Store structured tp_price          │
│ • Store structured sl_price          │
│ • Store structured trade_reason      │
│ • Display in History page            │
└──────────────────────────────────────┘
```

**ประโยชน์**: 
- ✅ ข้อมูลเป็นโครงสร้าง (Structured) ไม่ใช่ unstructured text
- ✅ History page สามารถแสดง price levels ได้เลย
- ✅ สร้างสถิติ/รายงาน อย่างแม่นยำ
- ✅ ไม่พึ่งพากับการ parse text อีกต่อไป

---

## �🗄️ Database Architecture (3NF)

ระบบใช้ **SQLite** เป็นฐานข้อมูลหลัก โดยออกแบบ Schema ให้อยู่ในระดับ **3rd Normal Form (3NF)** เพื่อขจัดปัญหาความทับซ้อนของข้อมูล (Data Redundancy) และเพิ่ม Data Integrity สูงสุด:

1. **`trade_results` (Reference Table):** เก็บชุดรหัสคงที่ (`WIN`, `LOSS`, `MISSED`, `PENDING`) ช่วยขจัด Transitive Dependency ของป้ายกำกับ

2. **`screenshots` (Entity Table):** เก็บชื่อไฟล์ภาพที่ถูกบันทึก และบทวิเคราะห์จาก Gemini `ai_analysis` โดยบังคับ `UNIQUE`

3. **`journal_entries` (Transaction Table):** เชื่อมโยง Screenshot ID เข้ากับ Result ID และจัดเก็บข้อมูลเฉพาะการเทรดนั้นๆ เช่น:
   - `rr` — Risk:Reward ratio (เช่น "1:2")
   - `pnl_usd` — Profit/Loss in USD
   - **`entry_price`** — Structured entry from Gemini JSON *(NEW)*
   - **`tp_price`** — Structured TP from Gemini JSON *(NEW)*
   - **`sl_price`** — Structured SL from Gemini JSON *(NEW)*
   - **`trade_reason`** — Structured reason from Gemini JSON *(NEW)*
   - `recorded_at` — Timestamp

4. **`report_reasons` (Reference Table):** ประเภทการรายงานข้อผิดพลาด (ANALYSIS_ERROR, DATA_ERROR, BUG, OTHER)

5. **`reports` (Feedback Table):** ระบบรายงานข้อผิดพลาดจากผู้ใช้เพื่อให้ Gemini AI ดีขึ้น

*หมายเหตุ: Database ทำงานในโหมด WAL (Write-Ahead Logging) เพื่อประสิทธิภาพการอ่าน/เขียนพร้อมกัน และบังคับใช้ Foreign Key constraints เสมอ*

---

## 🛠️ Database Management Scripts

สำหรับการจัดการ Database มี utility scripts ดังนี้:

| Script | ฟังก์ชัน |
|--------|---------|
| `migrate_db.py` | เพิ่มคอลัมน์ใหม่ (entry_price, tp_price, sl_price, trade_reason) ให้กับ existing database |
| `cleanup_database_complete.py` | ล้างข้อมูลการเทรดทั้งหมด + reset auto-increment counters |

**ลองใช้:**
```bash
# Migrate existing database (one-time only)
python migrate_db.py

# Clean all trading data
python cleanup_database_complete.py
```

---

## ⚠️ ข้อควรระวัง

- เปิดหน้าต่าง TradingView ทิ้งไว้เป็น **Active Window** ก่อนสั่ง `/snap`
- ไฟล์ `.env` ห้าม commit ขึ้น Git เด็ดขาด

### `.gitignore` แนะนำ
```
.env
.venv/
bot.log
*.db
*.csv
__pycache__/
*.pyc
```
