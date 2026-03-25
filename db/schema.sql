-- schema.sql — Trading Journal SQLite Schema (3NF)
-- Idempotent: safe to run multiple times (CREATE IF NOT EXISTS)

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- ─────────────────────────────────────────────────────────────────
-- 1. trade_results  (lookup / reference table)
--    Stores the finite set of possible trade outcomes.
--    Eliminates transitive dependency: journal_entry → result_code → label
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS trade_results (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    code     TEXT    UNIQUE NOT NULL,   -- e.g. WIN, LOSS, MISSED, PENDING
    label_th TEXT    NOT NULL           -- e.g. "WIN (TP)", "LOSS (SL)"
);

-- Seed data (INSERT OR IGNORE = idempotent)
INSERT OR IGNORE INTO trade_results (code, label_th) VALUES
    ('PENDING', ''),
    ('WIN',     'WIN (TP)'),
    ('LOSS',    'LOSS (SL)'),
    ('MISSED',  'MISSED (ไม่ได้เข้าเทรด)');


-- ─────────────────────────────────────────────────────────────────
-- 2. screenshots  (one record per chart image captured)
--    Primary entity: one screenshot = one Gemini analysis session
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS screenshots (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT    UNIQUE NOT NULL,   -- e.g. XAUUSD_2026-03-25_01-29-53.png
    captured_at TEXT    NOT NULL,          -- ISO-8601  "2026-03-25 01:29:53"
    ai_analysis TEXT    DEFAULT ''         -- full Gemini analysis text
);

CREATE INDEX IF NOT EXISTS idx_screenshots_filename
    ON screenshots (filename);


-- ─────────────────────────────────────────────────────────────────
-- 3. journal_entries  (one record per trade outcome recorded)
--    Many-to-one with screenshots (one image can be re-evaluated,
--    but only the latest meaningful entry is used in stats).
--    FK → trade_results ensures referential integrity.
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS journal_entries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    screenshot_id INTEGER NOT NULL REFERENCES screenshots(id) ON DELETE CASCADE,
    result_id     INTEGER NOT NULL REFERENCES trade_results(id)
                          DEFAULT 1,       -- 1 = PENDING (seed row)
    rr            TEXT    DEFAULT '',      -- Risk:Reward e.g. "1:2"
    pnl_usd       REAL    DEFAULT NULL,    -- profit/loss in USD
    entry_price   REAL    DEFAULT NULL,    -- structured entry from Gemini JSON
    tp_price      REAL    DEFAULT NULL,    -- structured TP from Gemini JSON
    sl_price      REAL    DEFAULT NULL,    -- structured SL from Gemini JSON
    trade_reason  TEXT    DEFAULT NULL,    -- structured reason from Gemini JSON
    recorded_at   TEXT    NOT NULL         -- ISO-8601 timestamp of this record
);

CREATE INDEX IF NOT EXISTS idx_journal_screenshot
    ON journal_entries (screenshot_id);

CREATE INDEX IF NOT EXISTS idx_journal_result
    ON journal_entries (result_id);


-- ─────────────────────────────────────────────────────────────────
-- 4. report_reasons  (lookup table for report types)
--    Standardized reasons for flagging trades
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS report_reasons (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    code     TEXT    UNIQUE NOT NULL,   -- e.g. ANALYSIS_ERROR, DATA_ERROR, etc
    label_th TEXT    NOT NULL           -- Human-readable label in Thai
);

INSERT OR IGNORE INTO report_reasons (code, label_th) VALUES
    ('ANALYSIS_ERROR', '❌ AI Analysis ผิด'),
    ('DATA_ERROR',     '❌ ข้อมูลผิด'),
    ('BUG',            '🐛 Bug ระบบ'),
    ('OTHER',          '📝 อื่นๆ');


-- ─────────────────────────────────────────────────────────────────
-- 5. reports  (user feedback / bug reports)
--    FK → journal_entries: which trade is being reported
--    FK → report_reasons: category of the report
-- ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    journal_entry_id INTEGER NOT NULL REFERENCES journal_entries(id) ON DELETE CASCADE,
    reason_id       INTEGER NOT NULL REFERENCES report_reasons(id),
    details         TEXT    DEFAULT '',      -- user's detailed description
    reported_at     TEXT    NOT NULL         -- ISO-8601 timestamp of report
);

CREATE INDEX IF NOT EXISTS idx_reports_entry
    ON reports (journal_entry_id);

CREATE INDEX IF NOT EXISTS idx_reports_reason
    ON reports (reason_id);

CREATE INDEX IF NOT EXISTS idx_reports_timestamp
    ON reports (reported_at DESC);
