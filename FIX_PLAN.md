# Fix Plan: gold_smc_ai Critical Issues

**Date:** 2026-03-26
**Priority Order:** High → Medium → Low

---

## Priority 1: SQL NULL Handling (CRITICAL)

### File: `services/journal.py`
### Function: `get_stats()`
### Line: ~80-95

**Current Code:**
```python
pnl_total = 0.0
for r in rows:
    try:
        pnl_total += float(r.get("PnL_USD", "0") or "0")
    except ValueError:
        pass
```

**Problem:**
- Using `r.get("PnL_USD", "0") or "0"` returns string "0" for NULL values
- This is incorrect — should use `COALESCE` or explicit casting per row
- Example: If PnL_USD is NULL, `float(NULL or "0")` = `float("0")` = 0.0 (correct)
- But if PnL_USD is "NULL" (string), `float("NULL" or "0")` = `float("NULL")` → ValueError → ignored

**Better Approach:**
```python
pnl_total = 0.0
for r in rows:
    try:
        pnl = float(r.get("PnL_USD") or 0)
        pnl_total += pnl
    except (ValueError, TypeError):
        pass
```

**Or use SQL COALESCE:**
```python
pnl_total = 0.0
for r in rows:
    try:
        pnl = float(r.get("PnL_USD") or 0)
        pnl_total += pnl
    except (ValueError, TypeError):
        pass
```

**Also check:**
- `wins` calculation — does it handle NULL correctly?
- `losses` calculation — does it handle NULL correctly?

---

## Priority 2: Handler Ordering (MEDIUM)

### File: `bot/handlers.py`
### Lines: ~80-120 (register_handlers function)

**Current Code:**
```python
@bot.message_handler(commands=["snap"])
def handle_snap(message):
    ...

@bot.message_handler(commands=["stats"])
def handle_stats(message):
    ...

@bot.message_handler(func=lambda m: m.text and m.text.strip().lower() == "snap")
def handle_snap_keyword(message):
    ...

@bot.message_handler(func=lambda m: (
    _is_authorized(m.chat.id)
    and m.text
    and not m.text.startswith("/")
    and m.text.strip().lower() != "snap"
    and m.chat.id not in _pending_rr
    and gemini_api.get_history_length() > 0
))
def handle_followup(message):
    ...
```

**Problem:**
- Generic `handle_followup` handler has `lambda m: True` condition (effectively all messages)
- This will swallow ANY message that doesn't match specific handlers
- If a user types "snap" after a followup, it won't trigger `handle_snap_keyword`

**Better Approach:**
```python
# 1. Specific command handlers FIRST
@bot.message_handler(commands=["snap"])
def handle_snap(message):
    ...

@bot.message_handler(commands=["stats"])
def handle_stats(message):
    ...

# 2. Keyword handlers SECOND
@bot.message_handler(func=lambda m: m.text and m.text.strip().lower() == "snap")
def handle_snap_keyword(message):
    ...

# 3. Generic handlers LAST (but with conditions)
@bot.message_handler(func=lambda m: (
    _is_authorized(m.chat.id)
    and m.text
    and not m.text.startswith("/")
    and m.text.strip().lower() != "snap"
    and m.chat.id not in _pending_rr
    and gemini_api.get_history_length() > 0
))
def handle_followup(message):
    ...
```

**Also check:**
- `/clearchat` handler — is it above generic handlers?
- `/prompt` handler — is it above generic handlers?
- Followup handler condition — ensure it doesn't match commands

---

## Priority 3: URL Validation (MEDIUM)

### File: `config.py`
### Line: ~15 (WEBAPP_URL)

**Current Code:**
```python
WEBAPP_URL = os.getenv("WEBAPP_URL", "")
```

**Problem:**
- No validation — users can set invalid URLs
- Example: `WEBAPP_URL="invalid"` or `WEBAPP_URL="http://"` → 400 Bad Request from Telegram

**Better Approach:**
```python
WEBAPP_URL = os.getenv("WEBAPP_URL", "")

def validate_webapp_url(url: str) -> bool:
    """Validate WEBAPP_URL format"""
    if not url:
        return False
    url = url.strip()
    # Must start with http:// or https://
    if not (url.startswith("http://") or url.startswith("https://")):
        return False
    # Must have a domain (at least one dot)
    if "." not in url.split("://")[1]:
        return False
    return True

if WEBAPP_URL and not validate_webapp_url(WEBAPP_URL):
    logger.warning(f"Invalid WEBAPP_URL: {WEBAPP_URL} — will cause 400 errors")
    # Optionally raise an error or set to empty string
    WEBAPP_URL = ""
```

**Also check:**
- `config.validate()` function — should we add URL validation there?

---

## Priority 4: Auto-Migration Safety (LOW)

### File: `services/journal.py`
### Function: `_write_all_rows()`
### Line: ~40-50

**Current Code:**
```python
def _write_all_rows(rows: list[dict]) -> None:
    fieldnames = rows[0].keys() if rows else COLUMNS
    with open(config.JOURNAL_FILE, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writeheader()
        writer.writerows(rows)
```

**Problem:**
- This overwrites CSV, but doesn't clear DB tables
- On next restart, DB tables are empty, but CSV has data
- If DB tables are recreated, CSV will be re-imported (auto-migration)

**Better Approach:**
- **Option A**: When clearing history, wipe DB AND CSV
- **Option B**: Add `clear_csv()` function
- **Option C**: Add `force_clear()` function that deletes CSV

**Recommended:**
```python
def clear_csv():
    """Delete CSV file (will be recreated on next insert)"""
    if os.path.isfile(config.JOURNAL_FILE):
        os.remove(config.JOURNAL_FILE)
        logger.info(f"🗑️ Deleted CSV: {config.JOURNAL_FILE}")

def force_clear():
    """Wipe DB tables AND CSV"""
    clear_database()
    clear_csv()
    logger.info("🔄 Force cleared database and CSV")
```

**Usage:**
```python
@bot.message_handler(commands=["clearchat"])
def handle_clearchat(message):
    # Wipe DB
    clear_database()
    # Wipe CSV
    clear_csv()
    # Clear Gemini history
    gemini_api.clear_history()
    bot.reply_to(message, "🗑️ ล้าง Conversation History, Database และ CSV แล้ว")
```

---

## Implementation Order

1. ✅ **Priority 1**: Fix SQL NULL handling in `journal.py`
2. ✅ **Priority 2**: Fix handler ordering in `bot/handlers.py`
3. ✅ **Priority 3**: Add URL validation in `config.py`
4. ✅ **Priority 4**: Add CSV clearing function in `journal.py`

---

## Test Plan

### Test 1: SQL NULL Handling
1. Insert trade with NULL PnL_USD
2. Run `/stats`
3. Verify PnL total is correct (should include 0 for NULL, not skip)

### Test 2: Handler Ordering
1. Send "snap" message after a followup
2. Verify it triggers `handle_snap_keyword`

### Test 3: URL Validation
1. Set `WEBAPP_URL="invalid"` in `.env`
2. Start bot
3. Verify warning logged (or bot fails gracefully)

### Test 4: CSV Clearing
1. Insert some trades
2. Run `/clearchat`
3. Verify DB is empty AND CSV is deleted
4. Restart bot
4. Verify no auto-import happens

---

## Expected Outcome

After all fixes:
- ✅ PnL calculations are accurate
- ✅ All commands work correctly
- ✅ No 400 errors from invalid URLs
- ✅ Clear history properly wipes both DB and CSV
- ✅ No data duplication from auto-migration

---

**Status:** 📋 Plan Ready
**Next Step:** Execute fixes in order
