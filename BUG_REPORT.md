# Bug Report: Pending Orders Alert Loop

**Date:** 2026-03-25
**Project:** gold_smc_ai
**Issue:** Repeated pending trade alerts + accumulated unrecorded orders

---

## Problem Summary

1. **Alert spam**: Bot sends "⏰ แจ้งเตือน: มีออเดอร์ที่ยังไม่ได้บันทึกผล" repeatedly in short intervals
2. **Pending orders accumulate**: 7+ trades stuck without `Trade Result` recorded
3. **Stats anomaly**: Win Rate 100% but PnL $0.00

---

## Root Cause Analysis

### 1. Alert Loop Issue (`main.py:46-62`)

**Current Implementation:**
```python
def _pending_reminder_loop(bot: telebot.TeleBot):
    while True:
        time.sleep(config.PENDING_CHECK_INTERVAL_SEC)  # 1800s = 30 min
        pending = journal.get_pending_trades(hours=config.PENDING_ALERT_HOURS)  # 4 hours
        if not pending:
            continue
        # Send alert
```

**Problems:**
- No deduplication — same pending trades trigger alerts every 30 minutes forever
- No cooldown between alerts for the same pending trades
- No mechanism to mark alerts as "seen" or "dismissed"

**Possible Causes:**
- Multiple bot instances running simultaneously
- Bot restarts without proper state cleanup
- Pending trades never get resolved, so alerts loop infinitely

---

### 2. Pending Trades Never Clear (`journal.py:20-30`)

**Current Implementation:**
```python
def save_to_journal(filename: str, result: str, analysis: str, rr: str = "", pnl: str = ""):
    """บันทึกผลการเทรดลง CSV (backward-compatible กับข้อมูลเก่า)"""
    file_exists = os.path.isfile(config.JOURNAL_FILE)
    with open(config.JOURNAL_FILE, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(COLUMNS)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, filename, result, rr, pnl, analysis])
```

**Problems:**
- Always `mode="a"` (append) — creates NEW rows instead of updating existing ones
- No UPSERT logic — if user clicks TP/SL/Miss, it creates duplicate rows
- `Trade Result` is empty initially, so rows accumulate indefinitely

**Expected Behavior:**
- First call with empty result: Create row with empty result
- Second call with TP/SL/Miss: Update the SAME row (set `Trade Result`, `RR`, `PnL`)
- Or: Delete the first row and create new one with full data

---

### 3. Stats Calculation (`journal.py:80-95`)

**Current Implementation:**
```python
def get_stats() -> dict:
    rows = _read_all_rows()
    total = len(rows)
    wins = sum(1 for r in rows if "WIN" in r.get("Trade Result", "").upper())
    losses = sum(1 for r in rows if "LOSS" in r.get("Trade Result", "").upper())
    entered = wins + losses
    win_rate = (wins / entered * 100) if entered > 0 else 0.0

    pnl_total = 0.0
    for r in rows:
        try:
            pnl_total += float(r.get("PnL_USD", "0") or "0")
        except ValueError:
            pass
```

**Issues:**
- Correct logic, but if duplicate rows exist, stats are inflated
- PnL $0.00 because user entered "-" for PnL or skipped input (empty string treated as "0")

**Why Win Rate 100%:**
- `entered = wins + losses = 1 + 0 = 1`
- `win_rate = 1 / 1 * 100 = 100%` ✓ Mathematically correct

---

## Files to Investigate

### Core Files
- `main.py:46-62` — `_pending_reminder_loop()` — Alert loop logic
- `journal.py:20-30` — `save_to_journal()` — Should UPSERT, not INSERT
- `journal.py:80-95` — `get_stats()` — Stats calculation
- `callbacks.py:28-45` — Handle TP/SL/Miss callbacks — Check update logic

### Configuration
- `config.py:32-33` — `PENDING_ALERT_HOURS = 4`, `PENDING_CHECK_INTERVAL_SEC = 1800`

---

## Recommended Fixes

### Fix 1: UPSERT Logic for `save_to_journal()`

**Option A: Update existing row**
```python
def save_to_journal(filename: str, result: str, analysis: str, rr: str = "", pnl: str = ""):
    """บันทึกผลการเทรด (UPDATE if exists, INSERT if new)"""
    rows = _read_all_rows()
    updated = False

    for row in reversed(rows):
        if row.get("Image File") == filename:
            row["Trade Result"] = result
            row["RR"] = rr
            row["PnL_USD"] = pnl
            row["AI Analysis"] = analysis
            updated = True
            break

    if updated:
        _write_all_rows(rows)
    else:
        # Create new row
        file_exists = os.path.isfile(config.JOURNAL_FILE)
        with open(config.JOURNAL_FILE, mode="a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(COLUMNS)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow([timestamp, filename, result, rr, pnl, analysis])
```

**Option B: Delete old row + Insert new**
```python
def save_to_journal(filename: str, result: str, analysis: str, rr: str = "", pnl: str = ""):
    """บันทึกผลการเทรด (DELETE old row with same filename, INSERT new)"""
    rows = _read_all_rows()

    # Remove old row if exists
    rows = [r for r in rows if r.get("Image File") != filename]

    # Add new row
    file_exists = os.path.isfile(config.JOURNAL_FILE)
    with open(config.JOURNAL_FILE, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(COLUMNS)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, filename, result, rr, pnl, analysis])
```

---

### Fix 2: Deduplicate Alerts

**Option A: Track last notification timestamp**
```python
# In config.py
LAST_ALERT_TIMESTAMP = 0  # Unix timestamp

# In main.py
def _pending_reminder_loop(bot: telebot.TeleBot):
    global LAST_ALERT_TIMESTAMP
    while True:
        time.sleep(config.PENDING_CHECK_INTERVAL_SEC)
        pending = journal.get_pending_trades(hours=config.PENDING_ALERT_HOURS)
        if not pending:
            continue

        # Only send alert if last alert was > 1 hour ago
        if time.time() - LAST_ALERT_TIMESTAMP > 3600:
            # Send alert
            LAST_ALERT_TIMESTAMP = time.time()
```

**Option B: Mark alerts as seen (require /clear_pending)**
```python
# Add command: /clear_pending
# Removes all pending trades from journal
```

---

### Fix 3: Add `/clear_pending` Command

```python
@bot.message_handler(commands=["clear_pending"])
def handle_clear_pending(message):
    """ล้าง trades ที่ยังไม่ได้บันทึกผล"""
    pending = journal.get_pending_trades(hours=config.PENDING_ALERT_HOURS)
    if not pending:
        bot.reply_to(message, "📭 ไม่มี trades ที่ยังไม่ได้บันทึกผล")
        return

    # Remove pending rows
    rows = journal._read_all_rows()
    cleaned = [r for r in rows if r.get("Trade Result", "").strip()]

    if len(cleaned) == len(rows):
        bot.reply_to(message, "✅ ไม่มี pending trades")
        return

    journal._write_all_rows(cleaned)
    bot.reply_to(message, f"🗑️ ล้าง {len(rows) - len(cleaned)} pending trades แล้ว")
```

---

### Fix 4: Check for Zombie Processes

```bash
# Check running instances
ps aux | grep "main.py"

# Kill duplicate instances
pkill -f "python main.py"

# Restart with unique PID
nohup python main.py > bot.log 2>&1 &
```

---

## Debug Commands

### Check Running Instances
```bash
ps aux | grep "main.py"
```

### View Pending Trades
```bash
cat trading_journal.csv | grep -v "WIN\|LOSS\|MISSED" | head -20
```

### View All Trades
```bash
cat trading_journal.csv
```

### View Bot Logs
```bash
tail -f bot.log | grep -E "Pending|alert|save_to_journal"
```

### Kill Zombie Processes
```bash
pkill -9 -f "python main.py"
```

---

## Test Cases

### Test 1: Snap → Click TP
1. Run `/snap` → Trade saved with empty result
2. Click "🟢 TP (Win)" → Should UPDATE row, not create duplicate
3. Check stats: Should show 1 win, correct PnL

### Test 2: Snap → No Button Click
1. Run `/snap` → Trade saved with empty result
2. Wait 4+ hours → Should trigger alert
3. Run `/snap` again → Should NOT create duplicate row
4. Click button → Should UPDATE the same row

### Test 3: Stats Accuracy
1. Enter multiple trades (some with PnL, some without)
2. Run `/stats` → Verify Win Rate, PnL, Streak calculations
3. Check that duplicates don't inflate stats

---

## Priority Order

1. **High**: Fix `save_to_journal()` to UPSERT (not INSERT)
2. **High**: Check for zombie processes (multiple bot instances)
3. **Medium**: Add deduplication to alert loop
4. **Low**: Add `/clear_pending` command

---

## Notes

- Bot is currently running as PID 708 (root)
- CSV file location: unknown (not in workspace)
- Alert interval: 30 minutes
- Alert threshold: 4 hours

---

## Related Issues

- No GitHub issues found for this project
- No prior bug reports in logs
- First report from user: 2026-03-25

---

**Status:** 🚧 Awaiting Fix
**Reporter:** J Wei
**Assigned to:** OpenClaw Agent
