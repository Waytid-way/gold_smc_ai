import json
import base64
import requests
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")

img_path = r"C:\Users\com\Downloads\XAUUSD_2026-03-25_01-08-49.png"
with open(img_path, "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode("utf-8")

prompt = (
    "คุณคือเทรดเดอร์ SMC มืออาชีพ ชำนาญ XAUUSD ใช้แนวคิด BOS/CHoCH, "
    "Order Block, Liquidity, FVG, Premium/Discount.\n\n"
    "รูปนี้คือ dashboard จาก indicator ของผมที่รวม bias, OB, liquidity, FVG, RSI ฯลฯ\n"
    "จงวิเคราะห์ข้อมูลทั้งหมดจากรูปภาพอย่างละเอียด แล้วตอบตามหัวข้อดังต่อไปนี้:\n"
    "1. Market Analysis (แนวโน้มหลักและรอง)\n"
    "2. โซน Entry, Stop Loss (SL), และ Take Profit (TP)\n"
    "3. แผนการเทรดโดยสรุปอิงตามหลัก SMC เท่านั้น\n"
    "ไม่ต้องเกริ่นนำ ให้เริ่มวิเคราะห์เนื้อหาได้เลย"
)

contents = [
    {
        "role": "user",
        "parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/png", "data": img_b64}}
        ]
    }
]

url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"
payload = {
    "contents": contents,
    "generationConfig": {
        "temperature": 0.4,
        "maxOutputTokens": 1024,
    }
}

try:
    resp = requests.post(url, json=payload, timeout=30)
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
