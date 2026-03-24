"""utils/text.py — Telegram text formatting utilities"""
import re


def escape_markdown(text: str, version: int = 1) -> str:
    """Escape special characters for Telegram Markdown."""
    if version == 1:
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '|', '{', '}', '.']
    else:
        escape_chars = ['_', '*', '[', ']', '(', ')']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


def clean_gemini_response(text: str) -> str:
    """แปลง Markdown พิเศษจาก Gemini ให้อยู่ในฟอร์แมต HTML สำหรับ Telegram"""
    import html
    # Escape < > & เพื่อไม่ให้ Telegram HTML พัง
    text = html.escape(text)
    
    # 1. ลบ heading (แต่เน้นให้เป็นตัวหนาแทน)
    text = re.sub(r"^#{1,6}\s*(.+)$", r"<b>\1</b>", text, flags=re.MULTILINE)
    
    # 2. แปลง **text** เป็น <b>text</b>
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    
    # 3. แปลง *text* เป็น <i>text</i> ถ้าไม่ใช่ bullet point (ตรวจสอบว่าไม่มีเว้นวรรคหลัง *)
    text = re.sub(r"(?<!^)\*([^\s\*].+?)\*(?!$)", r"<i>\1</i>", text)
    
    # 4. แปลง inline code `text` เป็น <code>text</code>
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    
    # 5. ลดบรรทัดว่างที่ซ้ำซ้อน
    text = re.sub(r"\n{3,}", "\n\n", text)
    
    return text.strip()
