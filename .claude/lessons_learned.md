# Lessons Learned & AI Mistakes Memory

This document acts as persistent memory for **AI Assistants** (Claude, Gemini, Cursor) who might work on this repository. Before starting new coding tasks, **READ THIS FILE FIRST** to avoid making past mistakes.

---

## 🛑 Bug Memory 1: SQLite `SUM` with `NULL` (PnL Calculation)

**Issue:** 
When querying the total PnL (`/stats`), the AI incorrectly wrote the query using `SUM(CASE WHEN ...)`, which aggregated `NULL` values out of missed or pending trades, dragging the entire SUM to `NULL`, resulting in `$0.00` total profit for the user!

**Incorrect Code:**
```sql
COALESCE(SUM(CASE WHEN tr.code != 'PENDING' AND tr.code != 'MISSED'
                  THEN je.pnl_usd ELSE 0 END), 0)
```

**✅ The Fix (Lesson):**
Never unnecessarily `COALESCE` the fallback outside if the interior is complex and mixes NULLs.
Always explicitly cast `NULL` to 0 *per row*, and filter strictly:
```sql
SUM(COALESCE(je.pnl_usd, 0)) AS pnl_total
...
WHERE tr.code IN ('WIN', 'LOSS')
```

---

## 🛑 Bug Memory 2: Automated File Edits matching Trailing Whitespace (`Return\n`)

**Issue:**
When attempting to use an automated File Search & Replace tool via a Python script to rewrite a block inside `bot/handlers.py`, the AI's regex/direct-string matching failed **10 times in a row** due to trailing spaces right behind a `return` keyword (`"return\n          \n"`).

**✅ The Fix (Lesson):**
Do not use `str.replace` over massive blocks of un-normalized python code containing hidden trailing spaces. Use dedicated codebase tools like `multi_replace_file_content` targeting small, exact chunks, or use direct `view_file` to see exact line numbers and byte combinations before attempting a replacement.

---

## 🛑 Bug Memory 3: Chat Handlers & Function Ordering

**Issue:**
Telegram's `bot.message_handler` checks handlers linearly from top to bottom. If a generic `func=lambda m: True` is placed *above* a specific `/stats` or explicit matching handler, the generic handler swallows everything.

**✅ The Fix (Lesson):**
When modifying `handlers.py`, ALWAYS declare specific command handlers (like `/snap` or `/clear_pending`) **ABOVE** generic conversation or fallback routines.

## 🛑 General Architecture Standard
- **Always update the `README.md`** when altering structural constraints.
- DO NOT use flat files CSV for storing records. Stick to the 3NF SQLite database. The CSV exists ONLY as a fallback / static legacy file. Do not run DB mutations using `pandas`.

---

## 🛑 Bug Memory 4: Telegram `BUTTON_URL_INVALID`
**Issue:** 
When setting up `WEBAPP_URL` in `.env`, the user accidentally chopped off the TLD (e.g. `.d/` instead of `.app`) or missed the `https://`. Telegram performs strict TLD/String validation on `InlineKeyboardButton(web_app=WebAppInfo(url=...))` and will crash the bot with `400 Bad Request` if it detects invalid URL structures.
**✅ The Fix (Lesson):**
Sanitization logic in `config.py` using `.strip()` and auto-prepending `https://`. Instruct users to explicitly double-check the Top Level Domain.

---

## 🛑 Bug Memory 5: Flask Port 5050 collision with `pgAdmin`
**Issue:** 
Flask was set to run on port `5050`. However, `pgAdmin 4` commonly binds to port `5050` by default. When the user tunneled via ngrok to `5050`, the Telegram WebApp opened the pgAdmin login page instead of the bot's frontend. Additionally, running multiple `ngrok` instances requires a paid plan or specific explicit pooling flags, causing `ERR_NGROK_334` when the user tried to restart it.
**✅ The Fix (Lesson):**
Avoid common ports like `5000` (macOS AirPlay), `5050` (pgAdmin), `8080`, `3000`. We switched to `5055`. Instruct users to close old ngrok terminals before starting new ones.

---

## 🛑 Bug Memory 6: CSV Auto-Import Loophole & Fake Calendar Grid
**Issue:** 
When attempting to clear old records by dropping DB tables, the system auto-reimported legacy rows on reboot because `migrate_from_csv()` noticed `existing_count == 0` and blindly parsed the untouched `trading_journal.csv`. Furthermore, the WebApp previously used a lazy fake layout producing exact 31 boxes regardless of month offset.
**✅ The Fix (Lesson):**
We instituted `/clear_history` to explicitly wipe DB tables *AND* overwrite the CSV with an empty header row. We updated the web framework to calculate `new Date()` dynamics matching real calendar bounds.
