import io
import logging
import os
from datetime import datetime, timedelta

import config
from services.db import get_connection
from utils.text import parse_numeric

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _result_id(code: str) -> int:
    """Return trade_results.id for the given code (WIN/LOSS/MISSED/PENDING)."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM trade_results WHERE code = ?", (code,)
        ).fetchone()
    if row is None:
        raise ValueError(f"Unknown result code: {code!r}")
    return row["id"]


def _result_code_from_text(result_text: str) -> str:
    """Map a human-readable result string → internal code."""
    upper = result_text.upper().strip()
    if "WIN" in upper:
        return "WIN"
    if "LOSS" in upper:
        return "LOSS"
    if "MISSED" in upper:
        return "MISSED"
    return "PENDING"


# ──────────────────────────────────────────────────────────────────────────────
# Write
# ──────────────────────────────────────────────────────────────────────────────

def save_to_journal(
    filename: str,
    result: str,
    analysis: str,
    rr: str = "",
    pnl: str = "",
    trade_data: dict = None,
) -> None:
    """
    UPSERT ผลการเทรด:
    - ถ้าไม่มี screenshot สำหรับ filename นี้ → INSERT ใหม่ทั้ง screenshot และ journal_entry
    - ถ้ามีแล้ว → UPDATE journal_entry ล่าสุดที่ผูกกับ screenshot นั้น
    
    Args:
        filename: ชื่อไฟล์รูป
        result: ผลการเทรด (WIN/LOSS/MISSED/PENDING)
        analysis: ข้อความวิเคราะห์จาก Gemini (สำหรับ ai_analysis column)
        rr: Risk:Reward ratio (เช่น "1:2")
        pnl: Profit/Loss in USD
        trade_data: dict with 'entry', 'tp', 'sl', 'reason' for structured storage
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    code      = _result_code_from_text(result)
    result_id = _result_id(code)

    pnl_usd = parse_numeric(pnl)
    
    # Extract structured trade data if provided
    entry_price = None
    tp_price = None
    sl_price = None
    trade_reason = None
    
    if trade_data:
        try:
            entry_price = float(trade_data.get("entry")) if trade_data.get("entry") else None
            tp_price = float(trade_data.get("tp")) if trade_data.get("tp") else None
            sl_price = float(trade_data.get("sl")) if trade_data.get("sl") else None
            trade_reason = trade_data.get("reason")
        except (ValueError, TypeError):
            logger.warning("Invalid trade_data format, skipping structured storage")

    with get_connection() as conn:
        # 1. Upsert screenshot (filename is UNIQUE)
        conn.execute(
            """
            INSERT INTO screenshots (filename, captured_at, ai_analysis)
            VALUES (?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                ai_analysis = CASE
                    WHEN excluded.ai_analysis != '' THEN excluded.ai_analysis
                    ELSE ai_analysis
                END
            """,
            (filename, now, analysis),
        )

        sc_row = conn.execute(
            "SELECT id FROM screenshots WHERE filename = ?", (filename,)
        ).fetchone()
        screenshot_id = sc_row["id"]

        # 2. Check for existing journal_entry for this screenshot
        je_row = conn.execute(
            """
            SELECT id FROM journal_entries
            WHERE screenshot_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (screenshot_id,),
        ).fetchone()

        if je_row:
            # Update existing entry
            conn.execute(
                """
                UPDATE journal_entries
                SET result_id   = ?,
                    rr          = CASE WHEN ? != '' THEN ? ELSE rr END,
                    pnl_usd     = CASE WHEN ? IS NOT NULL THEN ? ELSE pnl_usd END,
                    entry_price = CASE WHEN ? IS NOT NULL THEN ? ELSE entry_price END,
                    tp_price    = CASE WHEN ? IS NOT NULL THEN ? ELSE tp_price END,
                    sl_price    = CASE WHEN ? IS NOT NULL THEN ? ELSE sl_price END,
                    trade_reason= CASE WHEN ? IS NOT NULL THEN ? ELSE trade_reason END,
                    recorded_at = ?
                WHERE id = ?
                """,
                (
                    result_id, 
                    rr, rr, 
                    pnl_usd, pnl_usd,
                    entry_price, entry_price,
                    tp_price, tp_price,
                    sl_price, sl_price,
                    trade_reason, trade_reason,
                    now, 
                    je_row["id"]
                ),
            )
            logger.info("📝 อัปเดต: %s | RR=%s | PnL=%s → %s", result, rr, pnl, filename)
        else:
            # Insert new entry
            conn.execute(
                """
                INSERT INTO journal_entries
                    (screenshot_id, result_id, rr, pnl_usd, entry_price, tp_price, sl_price, trade_reason, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (screenshot_id, result_id, rr, pnl_usd, entry_price, tp_price, sl_price, trade_reason, now),
            )
            logger.info("📝 บันทึกใหม่: %s | RR=%s | PnL=%s → %s", result, rr, pnl, filename)


def update_trade_detail(filename: str, rr: str, pnl: str) -> bool:
    """อัปเดต RR และ PnL ของ journal_entry ล่าสุดที่ผูกกับ filename นั้น"""
    pnl_usd = parse_numeric(pnl)

    with get_connection() as conn:
        result = conn.execute(
            """
            UPDATE journal_entries
            SET rr      = ?,
                pnl_usd = ?
            WHERE id = (
                SELECT je.id FROM journal_entries je
                JOIN screenshots s ON s.id = je.screenshot_id
                WHERE s.filename = ?
                ORDER BY je.id DESC LIMIT 1
            )
            """,
            (rr, pnl_usd, filename),
        )
    updated = result.rowcount > 0
    if updated:
        logger.info("✏️ อัปเดต RR/PnL สำหรับ %s", filename)
    return updated


def save_report(trade_id: int, reason_code: str, details: str = "") -> bool:
    """
    บันทึกการรายงานความผิดพลาดสำหรับ trade นั้นๆ
    
    Args:
        trade_id: journal_entries.id
        reason_code: 'ANALYSIS_ERROR' | 'DATA_ERROR' | 'BUG' | 'OTHER'
        details: รายละเอียดเพิ่มเติม
    
    Returns:
        True if saved successfully
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with get_connection() as conn:
            # Get reason_id from reason_code
            reason_row = conn.execute(
                "SELECT id FROM report_reasons WHERE code = ?", (reason_code,)
            ).fetchone()
            
            if not reason_row:
                logger.warning("⚠️ Unknown report reason: %s", reason_code)
                return False
            
            reason_id = reason_row["id"]
            
            # Insert report
            conn.execute(
                """
                INSERT INTO reports (journal_entry_id, reason_id, details, reported_at)
                VALUES (?, ?, ?, ?)
                """,
                (trade_id, reason_id, details, now)
            )
            
            logger.info("🚩 บันทึกรายงาน: Trade #%d | Reason: %s", trade_id, reason_code)
            return True
    except Exception as e:
        logger.error("❌ Error saving report: %s", e)
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Read (internal — keeps backward compat for handlers that still use these)
# ──────────────────────────────────────────────────────────────────────────────

def _read_all_rows() -> list[dict]:
    """Return all journal entries as list of dict (compatible with old CSV format)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                je.recorded_at          AS "Date",
                s.filename              AS "Image File",
                CASE tr.code
                    WHEN 'PENDING' THEN ''
                    ELSE tr.label_th
                END                     AS "Trade Result",
                je.rr                   AS "RR",
                CAST(je.pnl_usd AS TEXT) AS "PnL_USD",
                s.ai_analysis           AS "AI Analysis"
            FROM journal_entries je
            JOIN screenshots    s  ON s.id  = je.screenshot_id
            JOIN trade_results  tr ON tr.id = je.result_id
            ORDER BY je.id ASC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def delete_pending_trades() -> int:
    """ลบ journal_entries ที่ยังเป็น PENDING ทิ้ง คืนจำนวนที่ลบ"""
    with get_connection() as conn:
        pending_id = conn.execute(
            "SELECT id FROM trade_results WHERE code = 'PENDING'"
        ).fetchone()["id"]

        result = conn.execute(
            "DELETE FROM journal_entries WHERE result_id = ?", (pending_id,)
        )
        deleted = result.rowcount

    if deleted:
        logger.info("🗑️ ลบ Pending trades %d รายการ", deleted)
    return deleted


# ──────────────────────────────────────────────────────────────────────────────
# Stats
# ──────────────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """
    คำนวณสถิติการเทรดทั้งหมดจาก DB 
    ใช้ SQL Aggregation ตามโครงสร้างฐานข้อมูลแบบ 3NF เพื่อลดภาระการวนลูปใน Python
    """
    stats = {
        "total": 0,
        "wins": 0,
        "losses": 0,
        "missed": 0,
        "pnl_total": 0.0,
        "win_rate": 0.0,
        "max_streak": 0,
    }
    
    with get_connection() as conn:
        # SQL Aggregation ยิงเพียงครั้งเดียวเพื่อสรุปข้อมูลทั้งหมด
        row = conn.execute(
            """
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN tr.code = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN tr.code = 'LOSS' THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN tr.code = 'MISSED' THEN 1 ELSE 0 END) as missed,
                SUM(CASE WHEN tr.code IN ('WIN', 'LOSS') THEN COALESCE(je.pnl_usd, 0) ELSE 0 END) as pnl_total
            FROM journal_entries je
            JOIN trade_results tr ON tr.id = je.result_id
            WHERE tr.code != 'PENDING'
            """
        ).fetchone()
        
        if row and row["total_trades"] > 0:
            stats["total"] = row["total_trades"]
            stats["wins"] = row["wins"] or 0
            stats["losses"] = row["losses"] or 0
            stats["missed"] = row["missed"] or 0
            stats["pnl_total"] = float(row["pnl_total"] or 0.0)
            
            entered = stats["wins"] + stats["losses"]
            if entered > 0:
                stats["win_rate"] = round((stats["wins"] / entered) * 100, 1)

        # Streak calculation (ลำดับสำคัญมาก ดึงเฉพา code มาวนลูปสั้นๆ เพื่อหา Peak Streak)
        streak_rows = conn.execute(
            """
            SELECT tr.code 
            FROM journal_entries je
            JOIN trade_results tr ON tr.id = je.result_id
            WHERE tr.code != 'PENDING'
            ORDER BY je.id ASC
            """
        ).fetchall()
        
    current_streak = 0
    for r in streak_rows:
        code = r["code"]
        if code == "WIN":
            current_streak += 1
            stats["max_streak"] = max(stats["max_streak"], current_streak)
        elif code == "LOSS":
            current_streak = 0
                
    return stats



def format_stats_text(stats: dict) -> str:
    """แปลง dict สถิติเป็นข้อความสำหรับส่งใน Telegram"""
    return (
        f"📊 สถิติการเทรด (ทั้งหมด {stats['total']} รายการ)\n"
        f"├ ✅ Win (TP):   {stats['wins']} ครั้ง\n"
        f"├ ❌ Loss (SL):  {stats['losses']} ครั้ง\n"
        f"└ ⏩ Miss:       {stats['missed']} ครั้ง\n\n"
        f"📈 Win Rate: {stats['win_rate']}% (เฉพาะที่เข้าออเดอร์)\n"
        f"💰 PnL รวม: ${stats['pnl_total']:+.2f}\n"
        f"🔥 Win Streak สูงสุด: {stats['max_streak']} ครั้ง"
    )


# ──────────────────────────────────────────────────────────────────────────────
# Chart
# ──────────────────────────────────────────────────────────────────────────────

def generate_stats_chart() -> bytes | None:
    """สร้างกราฟรายเดือน Win/Loss/Miss คืน PNG bytes หรือ None ถ้าไม่มีข้อมูล"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from collections import defaultdict

        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT je.recorded_at AS date, tr.code AS result_code
                FROM journal_entries je
                JOIN trade_results tr ON tr.id = je.result_id
                WHERE tr.code IN ('WIN', 'LOSS', 'MISSED')
                ORDER BY je.id ASC
                """
            ).fetchall()

        if not rows:
            return None

        monthly: dict[str, dict] = defaultdict(lambda: {"WIN": 0, "LOSS": 0, "MISSED": 0})
        for r in rows:
            try:
                dt  = datetime.strptime(r["date"], "%Y-%m-%d %H:%M:%S")
                key = dt.strftime("%Y-%m")
                monthly[key][r["result_code"]] += 1
            except Exception:
                continue

        if not monthly:
            return None

        months = sorted(monthly.keys())
        wins   = [monthly[m]["WIN"]    for m in months]
        losses = [monthly[m]["LOSS"]   for m in months]
        misses = [monthly[m]["MISSED"] for m in months]
        labels = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in months]

        x     = range(len(months))
        width = 0.28

        fig, ax = plt.subplots(figsize=(max(8, len(months) * 1.5), 5))
        ax.bar([i - width for i in x], wins,   width, label="✅ Win",  color="#4CAF50")
        ax.bar(x,                      losses,  width, label="❌ Loss", color="#F44336")
        ax.bar([i + width for i in x], misses,  width, label="⏩ Miss", color="#9E9E9E")

        ax.set_title("📊 Trading Result by Month", fontsize=14, pad=12)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=30, ha="right")
        ax.set_ylabel("จำนวนออเดอร์")
        ax.legend()
        ax.yaxis.get_major_locator().set_params(integer=True)
        plt.tight_layout()

        buf = io.BytesIO()
        plt.savefig(buf, format="png", dpi=120)
        plt.close(fig)
        buf.seek(0)
        return buf.read()

    except ImportError:
        logger.warning("matplotlib ไม่ได้ติดตั้ง — ไม่สามารถสร้างกราฟได้")
        return None
    except Exception as e:
        logger.error("generate_stats_chart error: %s", e)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Pending Trades
# ──────────────────────────────────────────────────────────────────────────────

def get_pending_trades(hours: float = config.PENDING_ALERT_HOURS) -> list[dict]:
    """
    คืน trades ที่ยังเป็น PENDING และผ่านมาแล้วอย่างน้อย `hours` ชั่วโมง
    Format คืนเป็น dict ที่ Compatible กับ main.py loop เดิม
    """
    cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                je.recorded_at  AS "Date",
                s.filename      AS "Image File"
            FROM journal_entries je
            JOIN screenshots    s  ON s.id  = je.screenshot_id
            JOIN trade_results  tr ON tr.id = je.result_id
            WHERE tr.code = 'PENDING'
              AND je.recorded_at <= ?
            ORDER BY je.id ASC
            """,
            (cutoff,),
        ).fetchall()

    return [dict(r) for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# CSV Clearing
# ──────────────────────────────────────────────────────────────────────────────

def clear_csv():
    """Delete CSV file (will be recreated on next insert)"""
    if os.path.isfile(config.JOURNAL_FILE):
        os.remove(config.JOURNAL_FILE)
        logger.info(f"🗑️ Deleted CSV: {config.JOURNAL_FILE}")


# ──────────────────────────────────────────────────────────────────────────────
# Clear All History
# ──────────────────────────────────────────────────────────────────────────────

def clear_all_history() -> tuple[int, int]:
    """
    ลบประวัติการเทรดทั้งหมด (รีเซ็ต DB และ CSV)
    Returns: (จำนวน journal_entries, จำนวน screenshots)
    """
    with get_connection() as conn:
        je_count = conn.execute("DELETE FROM journal_entries").rowcount
        sc_count = conn.execute("DELETE FROM screenshots").rowcount
    
    # ล้าง CSV ด้วย ป้องกันไม่ให้ db_service.migrate_from_csv() 
    # ดูดข้อมูลเก่ากลับเข้ามาอีกตอนเปิดบอทใหม่
    if os.path.exists(config.JOURNAL_FILE):
        try:
            with open(config.JOURNAL_FILE, "w", encoding="utf-8-sig") as f:
                f.write("Date,Image File,Trade Result,RR,PnL_USD,AI Analysis\n")
        except Exception as e:
            logger.error("❌ ไม่สามารถล้างไฟล์ CSV ได้: %s", e)
            
    logger.info("🗑️ ล้างประวัติทั้งหมด: %d journals, %d screenshots", je_count, sc_count)
    return je_count, sc_count
