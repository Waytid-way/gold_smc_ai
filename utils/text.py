import re

def parse_numeric(val: str) -> float | None:
    """
    🧹 Data Sanitization Boundary
    รับค่า string ที่อาจจะมีความสกปรก (ติดเครื่องหมาย $, +, , หรือข้อความอื่นๆ)
    แล้วทำความสะอาดให้เหลือแค่ตัวเลขทศนิยม (float) บริสุทธิ์
    
    เช่น:
    - "$+20.50" -> 20.5
    - "- 10.0"  -> -10.0
    - "กำไร 5.5"  -> 5.5 (รวบรวมเฉพาะส่วนที่เป็นตัวเลขและจุด)
    - ""        -> None
    """
    if not val:
        return None
        
    # ลบช่องว่างและดึงเฉพาะตัวเลข, จุด, และเครื่องหมายลบด้านหน้าสุดออกมา
    # (รองรับทั้งเลขบวกและลบ)
    cleaned = re.sub(r'[^\d.-]', '', val)
    
    # ถ้าเหลือแต่เครื่องหมายลบ หรือจุด หรือความว่างเปล่า ให้คืนค่า None
    if not cleaned or cleaned in ['-', '.', '-.']:
        return None
        
    try:
        return float(cleaned)
    except ValueError:
        return None

def clean_gemini_response(text: str) -> str:
    """
    🧹 ทำความสะอาดข้อความจาก Gemini API 
    เพื่อป้องกัน Markdown parse error ใน Telegram
    และตัดครอบ Markdown blocks ที่ไม่จำเป็นออก
    """
    if not text:
        return ""
    
    # เอา ```markdown หรือ ``` ออก
    text = re.sub(r'```[a-zA-Z]*\n', '', text)
    text = text.replace('```', '')
    
    # Escape อักขระพิเศษบางตัวเพื่อให้รอดพ้น Markdown V2 ของ Telegram ถ้าจำเป็น
    # แต่ปกติ Telegram parser แบบเดิม (Markdown) จะมีปัญหากับ * สลับกัน
    # แต่เราเปลี่ยนให้เป็นตัวหนา/เอียงปกติก็พอ
    return text.strip()
