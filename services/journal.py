"""services/journal.py — อ่าน/เขียน Trading Journal CSV + สถิติ + กราฟ"""
import csv
import io
import logging
import os
from datetime import datetime, timedelta

import config

logger = logging.getLogger(__name__)

# ───── CSV Columns ─────────────────────────────────────────────────────────
COLUMNS = ["Date", "Image File", "Trade Result", "RR", "PnL_USD", "AI Analysis"]


# ───── Write ───────────────────────────────────────────────────────────────

def save_to_journal(
    filename: str,
    result: str,
    analysis: str,
    rr: str = "",
    pnl: str = "",
) -> None:
    """บันทึกผลการเทรดลง CSV (backward-compatible กับข้อมูลเก่า)"""
    file_exists = os.path.isfile(config.JOURNAL_FILE)
    with open(config.JOURNAL_FILE, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(COLUMNS)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, filename, result, rr, pnl, analysis])
    logger.info(f"📝 บันทึก: {result} | RR={rr} | PnL={pnl} → {filename}")


def update_trade_detail(filename: str, rr: str, pnl: str) -> bool:
    """อัปเดต RR และ PnL ของ row ล่าสุดที่มีชื่อไฟล์ตรงกัน
    คืน True ถ้าอัปเดตสำเร็จ
    """
    if not os.path.isfile(config.JOURNAL_FILE):
        return False

    rows = _read_all_rows()
    updated = False
    for row in reversed(rows):
        if row.get("Image File") == filename:
            row["RR"] = rr
            row["PnL_USD"] = pnl
            updated = True
            break

    if updated:
        _write_all_rows(rows)
        logger.info(f"✏️ อัปเดต RR/PnL สำหรับ {filename}")
    return updated


# ───── Read ────────────────────────────────────────────────────────────────

def _read_all_rows() -> list[dict]:
    if not os.path.isfile(config.JOURNAL_FILE):
        return []
    with open(config.JOURNAL_FILE, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_all_rows(rows: list[dict]) -> None:
    fieldnames = rows[0].keys() if rows else COLUMNS
    with open(config.JOURNAL_FILE, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ───── Stats ───────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """คำนวณสถิติการเทรดทั้งหมดจาก CSV"""
    rows = _read_all_rows()
    total = len(rows)
    wins  = sum(1 for r in rows if "WIN" in r.get("Trade Result", "").upper())
    losses = sum(1 for r in rows if "LOSS" in r.get("Trade Result", "").upper())
    missed = sum(1 for r in rows if "MISSED" in r.get("Trade Result", "").upper())
    entered = wins + losses
    win_rate = (wins / entered * 100) if entered > 0 else 0.0

    # PnL รวม
    pnl_total = 0.0
    for r in rows:
        try:
            pnl_total += float(r.get("PnL_USD", "0") or "0")
        except ValueError:
            pass

    # Win streak สูงสุด
    max_streak = streak = 0
    for r in rows:
        if "WIN" in r.get("Trade Result", "").upper():
            streak += 1
            max_streak = max(max_streak, streak)
        else:
            streak = 0

    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "missed": missed,
        "entered": entered,
        "win_rate": round(win_rate, 1),
        "pnl_total": round(pnl_total, 2),
        "max_streak": max_streak,
    }


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


# ───── Chart ───────────────────────────────────────────────────────────────

def generate_stats_chart() -> bytes | None:
    """สร้างกราฟรายเดือน Win/Loss/Miss ด้วย matplotlib
    คืน PNG bytes หรือ None ถ้าไม่มีข้อมูล
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from collections import defaultdict
        import calendar

        rows = _read_all_rows()
        if not rows:
            return None

        monthly: dict[str, dict] = defaultdict(lambda: {"WIN": 0, "LOSS": 0, "MISSED": 0})
        for r in rows:
            try:
                dt = datetime.strptime(r["Date"], "%Y-%m-%d %H:%M:%S")
                key = dt.strftime("%Y-%m")
                result = r.get("Trade Result", "").upper()
                if "WIN" in result:
                    monthly[key]["WIN"] += 1
                elif "LOSS" in result:
                    monthly[key]["LOSS"] += 1
                elif "MISSED" in result:
                    monthly[key]["MISSED"] += 1
            except Exception:
                continue

        if not monthly:
            return None

        months = sorted(monthly.keys())
        wins   = [monthly[m]["WIN"] for m in months]
        losses = [monthly[m]["LOSS"] for m in months]
        misses = [monthly[m]["MISSED"] for m in months]
        labels = [datetime.strptime(m, "%Y-%m").strftime("%b %Y") for m in months]

        x = range(len(months))
        width = 0.28

        fig, ax = plt.subplots(figsize=(max(8, len(months) * 1.5), 5))
        ax.bar([i - width for i in x], wins,   width, label="✅ Win",   color="#4CAF50")
        ax.bar(x,                      losses,  width, label="❌ Loss",  color="#F44336")
        ax.bar([i + width for i in x], misses,  width, label="⏩ Miss",  color="#9E9E9E")

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
        logger.error(f"generate_stats_chart error: {e}")
        return None


# ───── Pending Trades ──────────────────────────────────────────────────────

def get_pending_trades(hours: float = config.PENDING_ALERT_HOURS) -> list[dict]:
    """คืน trades ที่ยังไม่ได้บันทึกผล (Trade Result ว่าง)
    และผ่านมาแล้วอย่างน้อย `hours` ชั่วโมง
    """
    rows = _read_all_rows()
    now  = datetime.now()
    pending = []
    for r in rows:
        if r.get("Trade Result", "").strip():
            continue
        try:
            dt = datetime.strptime(r["Date"], "%Y-%m-%d %H:%M:%S")
            if (now - dt) >= timedelta(hours=hours):
                pending.append(r)
        except Exception:
            pass
    return pending
