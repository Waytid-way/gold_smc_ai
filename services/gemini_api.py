"""services/gemini_api.py — เรียก Gemini API พร้อม Conversation History"""
import base64
import logging
from collections import deque

import requests

import config

logger = logging.getLogger(__name__)

# Sliding window: เก็บ multi-turn history สูงสุด CONVERSATION_HISTORY_LIMIT turns
# แต่ละ entry = {"role": "user" | "model", "parts": [...]}
_history: deque = deque(maxlen=config.CONVERSATION_HISTORY_LIMIT * 2)  # *2 เพราะ 1 turn = user + model


def clear_history() -> None:
    """ล้าง conversation history ทั้งหมด (สำหรับ /clearchat)"""
    _history.clear()
    logger.info("🗑️ ล้าง conversation history แล้ว")


def get_history_length() -> int:
    return len(_history) // 2


def call_gemini_image(image_path: str, prompt: str) -> str:
    """ส่งรูปเข้า Gemini พร้อม conversation history ก่อนหน้า
    - รูปใหม่แต่ละครั้งจะถูกเพิ่มเข้า history โดยอัตโนมัติ
    """
    with open(image_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    user_parts = [
        {"text": prompt},
        {"inline_data": {"mime_type": "image/png", "data": img_b64}},
    ]

    # สร้าง contents รวม history + turn ปัจจุบัน
    contents = list(_history) + [{"role": "user", "parts": user_parts}]

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent"
    )
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": 0.4},
    }
    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=payload,
        params={"key": config.GEMINI_API_KEY},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"RAW API RESPONSE: {data}")

    try:
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        answer = str(data)

    # บันทึก turn นี้เข้า history
    _history.append({"role": "user", "parts": [{"text": prompt}]})  # ไม่รวม image เพื่อประหยัด tokens
    _history.append({"role": "model", "parts": [{"text": answer}]})
    logger.info(f"📚 History: {get_history_length()} turns (limit={config.CONVERSATION_HISTORY_LIMIT})")

    return answer


def call_gemini_text(text: str) -> str:
    """ส่งข้อความ follow-up เข้า Gemini พร้อม history (สำหรับคำถามต่อเนื่อง)"""
    user_parts = [{"text": text}]
    contents = list(_history) + [{"role": "user", "parts": user_parts}]

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{config.GEMINI_MODEL}:generateContent"
    )
    payload = {
        "contents": contents,
        "generationConfig": {"temperature": 0.4},
    }
    resp = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json=payload,
        params={"key": config.GEMINI_API_KEY},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    logger.info(f"RAW TEXT API RESPONSE: {data}")

    try:
        answer = data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        answer = str(data)

    _history.append({"role": "user", "parts": user_parts})
    _history.append({"role": "model", "parts": [{"text": answer}]})
    return answer
