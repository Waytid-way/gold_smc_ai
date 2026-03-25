"""web_server.py — รัน Flask เพื่อเสิร์ฟหน้า Web App UI ให้ Telegram"""
import os
import logging
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from services import journal

logger = logging.getLogger(__name__)

# ระบุตำแหน่งโฟลเดอร์ webapp ที่บรรจุหน้า HTML/CSS/JS
WEBAPP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")

app = Flask(__name__, static_folder=WEBAPP_DIR)
CORS(app)  # อนุญาตให้เชื่อมต่อข้ามโดเมนได้ (จำเป็นสำหรับ Web App API)

@app.route("/")
def index():
    """หน้าแรก: เสิร์ฟไฟล์ index.html"""
    return send_from_directory(app.static_folder, "index.html")

@app.route("/admin")
def admin():
    """Admin Dashboard: เสิร์ฟไฟล์ admin.html"""
    return send_from_directory(app.static_folder, "admin.html")

@app.route("/<path:filename>")
def static_files(filename):
    """เสิร์ฟไฟล์ .js, .css และอื่นๆ ในโฟลเดอร์ webapp"""
    return send_from_directory(app.static_folder, filename)

@app.route("/api/trades", methods=["GET"])
def get_trades_api():
    """API: ส่งข้อมูลสถิติ PnL ออกไปให้ Javascript ในรูปแบบ JSON"""
    try:
        # ดึง Stats ตัวเดิมที่เราเขียน Python คำนวณรัดกุมไว้แล้ว
        stats = journal.get_stats()
        
        # ดึง History (Raw list ของ trades) ออกมาส่งให้ JS วาด Grid
        from services.db import get_connection
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT je.id, tr.code, je.pnl_usd, je.recorded_at, je.rr
                FROM journal_entries je
                JOIN trade_results tr ON tr.id = je.result_id
                WHERE tr.code != 'PENDING'
                ORDER BY je.id ASC
                """
            ).fetchall()
            
        history = [dict(r) for r in rows]
        
        return jsonify({
            "status": "success",
            "stats": stats,
            "history": history
        })
    except Exception as e:
        logger.exception("🚨 API Error: ")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/trade/<int:trade_id>", methods=["GET"])
def get_trade_detail(trade_id):
    """API: ส่งรายละเอียด Trade รวม AI Analysis"""
    try:
        from services.db import get_connection
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT je.id, je.rr, je.pnl_usd, je.recorded_at,
                       tr.code, tr.label_th,
                       sc.ai_analysis
                FROM journal_entries je
                JOIN trade_results tr ON tr.id = je.result_id
                JOIN screenshots sc ON sc.id = je.screenshot_id
                WHERE je.id = ?
                """,
                (trade_id,)
            ).fetchone()
        
        if not row:
            return jsonify({"status": "error", "message": "Trade not found"}), 404
        
        return jsonify({
            "status": "success",
            "trade": {
                "id": row["id"],
                "rr": row["rr"],
                "pnl_usd": row["pnl_usd"],
                "recorded_at": row["recorded_at"],
                "result_code": row["code"],
                "result_label": row["label_th"],
                "ai_analysis": row["ai_analysis"]
            }
        })
    except Exception as e:
        logger.exception("🚨 API Error: ")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/trades/history", methods=["GET"])
def get_trades_history():
    """API: ส่งข้อมูล Trade History พร้อม Pagination & Filters
    
    Query params:
    - page: int (default 1)
    - limit: int (default 20)
    - result: str (WIN|LOSS|MISSED, default: all)
    - start_date: str (YYYY-MM-DD)
    - end_date: str (YYYY-MM-DD)
    """
    try:
        from services.db import get_connection
        from datetime import datetime
        
        # Parse query parameters
        page = max(1, int(request.args.get('page', 1)))
        limit = min(100, int(request.args.get('limit', 20)))  # Max 100
        result_filter = request.args.get('result', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        offset = (page - 1) * limit
        
        with get_connection() as conn:
            # Build WHERE clause
            where_clauses = ["tr.code != 'PENDING'"]
            params = []
            
            if result_filter and result_filter in ['WIN', 'LOSS', 'MISSED']:
                where_clauses.append("tr.code = ?")
                params.append(result_filter)
            
            if start_date:
                where_clauses.append("DATE(je.recorded_at) >= ?")
                params.append(start_date)
            
            if end_date:
                where_clauses.append("DATE(je.recorded_at) <= ?")
                params.append(end_date)
            
            where_str = " AND ".join(where_clauses)
            
            # Get total count
            count_query = f"SELECT COUNT(*) as cnt FROM journal_entries je JOIN trade_results tr ON tr.id = je.result_id WHERE {where_str}"
            count_result = conn.execute(count_query, params).fetchone()
            total = count_result['cnt']
            
            # Get paginated data
            query = f"""
                SELECT je.id, je.rr, je.pnl_usd, je.recorded_at,
                       tr.code, tr.label_th
                FROM journal_entries je
                JOIN trade_results tr ON tr.id = je.result_id
                WHERE {where_str}
                ORDER BY je.recorded_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            rows = conn.execute(query, params).fetchall()
        
        trades = [dict(r) for r in rows]
        total_pages = (total + limit - 1) // limit
        
        return jsonify({
            "status": "success",
            "data": trades,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": total_pages,
                "has_prev": page > 1,
                "has_next": page < total_pages
            }
        })
    except Exception as e:
        logger.exception("🚨 API Error: ")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/trade/<int:trade_id>/report", methods=["POST"])
def report_trade_issue(trade_id):
    """API: บันทึกรายงานความผิดพลาดสำหรับ trade นั้นๆ
    
    Body JSON:
    {
        "reason": "ANALYSIS_ERROR" | "DATA_ERROR" | "BUG" | "OTHER",
        "details": "optional description"
    }
    """
    try:
        data = request.get_json() or {}
        reason = data.get('reason', 'OTHER')
        details = data.get('details', '')
        
        # Save report
        success = journal.save_report(trade_id, reason, details)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Report submitted for Trade #{trade_id}"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to save report"
            }), 400
    except Exception as e:
        logger.exception("🚨 API Error: ")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/reports", methods=["GET"])
def get_reports():
    """API: ดึงรายงานทั้งหมด (Admin Dashboard)
    
    Query params:
    - limit: จำนวนรายการต่อหน้า (default 50)
    - page: หน้าที่ (default 1)
    - sort: sorting field: reported_at | reason | trade_id (default: reported_at DESC)
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        page = request.args.get('page', 1, type=int)
        sort = request.args.get('sort', 'reported_at', type=str)
        
        if limit > 500:
            limit = 500
        
        offset = (page - 1) * limit
        
        # Validate sort field
        valid_sorts = ['reported_at', 'reason', 'trade_id']
        if sort not in valid_sorts:
            sort = 'reported_at'
        
        from services.db import get_connection
        with get_connection() as conn:
            # Get total count
            total = conn.execute(
                "SELECT COUNT(*) as cnt FROM reports"
            ).fetchone()['cnt']
            
            # Get reports with pagination
            rows = conn.execute(f"""
                SELECT 
                    r.id,
                    r.journal_entry_id as trade_id,
                    je.recorded_at as trade_date,
                    rr.code as reason_code,
                    rr.label_th as reason_label,
                    r.details,
                    r.reported_at,
                    tr.code as trade_result,
                    je.rr,
                    je.pnl_usd
                FROM reports r
                JOIN journal_entries je ON je.id = r.journal_entry_id
                JOIN report_reasons rr ON rr.id = r.reason_id
                JOIN trade_results tr ON tr.id = je.result_id
                ORDER BY r.{sort} DESC
                LIMIT ? OFFSET ?
            """, (limit, offset)
            ).fetchall()
            
        reports = [dict(row) for row in rows]
        
        return jsonify({
            "status": "success",
            "reports": reports,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit,
                "has_prev": page > 1,
                "has_next": page < (total + limit - 1) // limit
            }
        })
    except Exception as e:
        logger.exception("🚨 API Error: ")
        return jsonify({"status": "error", "message": str(e)}), 500

def run_server():
    """รัน Flask Server (พอร์ต 5050)"""
    logger.info("🌐 Web App Server เริ่มทำงานที่พอร์ต 5050...")
    # ตั้ง use_reloader=False ป้องกันปัญหา Thread ชนกับ Telebot
    app.run(host="127.0.0.1", port=5055, debug=False, use_reloader=False)

if __name__ == "__main__":
    run_server()
