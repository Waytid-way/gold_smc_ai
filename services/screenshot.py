"""services/screenshot.py — จับภาพกราฟ TradingView ด้วย Ctrl+Alt+S"""
import ctypes
import glob
import logging
import os
import time

import pyautogui
import pygetwindow as gw

import config

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────────


def _try_win32_focus(hwnd: int) -> bool:
    """Fallback: ใช้ win32gui โดยตรงเพื่อ focus หน้าต่างใน Multi-Monitor"""
    try:
        import win32gui
        import win32con
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception as e:
        logger.warning(f"win32gui fallback failed: {e}")
        return False


def _get_hwnd_by_title(title_keyword: str):
    """คืน hwnd ของหน้าต่างที่มีชื่อตรงกัน (ใช้กับ win32gui)"""
    try:
        import win32gui

        def callback(hwnd, result):
            if win32gui.IsWindowVisible(hwnd) and title_keyword.lower() in win32gui.GetWindowText(hwnd).lower():
                result.append(hwnd)

        hwnds = []
        win32gui.EnumWindows(callback, hwnds)
        return hwnds[0] if hwnds else None
    except Exception:
        return None


def focus_tradingview_window() -> bool:
    """พยายาม focus หน้าต่าง TradingView/XAUUSD ด้วยหลาย fallback
    คืน True ถ้าสำเร็จ, False ถ้าล้มเหลวทุก fallback
    """
    keywords = ["TradingView", "XAUUSD"]

    for kw in keywords:
        windows = gw.getWindowsWithTitle(kw)
        if not windows:
            continue
        win = windows[0]
        try:
            if win.isMinimized:
                win.restore()
            win.activate()
            if not win.isMaximized:
                win.maximize()
            time.sleep(1.5)
            logger.info(f"✅ pygetwindow focus สำเร็จ: {win.title}")
            # คลิกใกล้ขอบบนเพื่อให้แน่ใจว่า focus อยู่ใน client area
            pyautogui.click(win.left + 10, win.top + 10)
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.warning(f"pygetwindow activate ล้มเหลว ({e}) → ลอง win32gui...")
            hwnd = _get_hwnd_by_title(kw)
            if hwnd and _try_win32_focus(hwnd):
                time.sleep(1.5)
                logger.info(f"✅ win32gui focus สำเร็จ (hwnd={hwnd})")
                return True

    logger.warning("ไม่พบหน้าต่าง TradingView — จะเปิด URL ใหม่")
    return False


def send_ctrl_alt_s() -> None:
    """ส่งคีย์ลัด Ctrl+Alt+S ด้วย WinAPI"""
    user32 = ctypes.windll.user32
    logger.debug("⌨️ Sending Ctrl+Alt+S via WinAPI")
    user32.keybd_event(config.VK_CTRL, 0, 0, 0)
    user32.keybd_event(config.VK_ALT, 0, 0, 0)
    time.sleep(0.1)
    user32.keybd_event(config.VK_S, 0, 0, 0)
    user32.keybd_event(config.VK_S, 0, config.KEYEVENTF_KEYUP, 0)
    user32.keybd_event(config.VK_ALT, 0, config.KEYEVENTF_KEYUP, 0)
    user32.keybd_event(config.VK_CTRL, 0, config.KEYEVENTF_KEYUP, 0)


def wait_for_new_screenshot(timeout: int = 30, trigger_time: float | None = None) -> str:
    """รอไฟล์ PNG ใหม่หลังจากส่งคำสั่ง Ctrl+Alt+S
    คืน absolute path ของไฟล์ที่พบ หรือ raise TimeoutError
    """
    pattern = os.path.join(config.DOWNLOAD_DIR, config.SCREENSHOT_PATTERN)
    before_files = glob.glob(pattern)
    before = {
        p: (os.path.getmtime(p), os.path.getsize(p))
        for p in before_files
        if os.path.exists(p)
    }
    start = time.time()

    logger.debug(f"📂 Scanning: {config.DOWNLOAD_DIR}  pattern={config.SCREENSHOT_PATTERN}  existing={len(before)}")

    # Pre-scan: ไฟล์เก่าที่อัปเดตก่อน trigger_time จะถูกตรวจด้วย
    if trigger_time is not None:
        for path, (mtime, size) in before.items():
            if mtime >= (trigger_time - 0.25) and size > 0:
                logger.info(f"⚡ Pre-scan match: {path}")
                return path

    while time.time() - start < timeout:
        time.sleep(0.5)
        for path in glob.glob(pattern):
            if not os.path.exists(path):
                continue
            current_mtime = os.path.getmtime(path)
            current_size  = os.path.getsize(path)
            previous = before.get(path)
            is_new        = previous is None
            prev_mtime    = previous[0] if previous else 0.0
            is_after_trig = trigger_time is None or current_mtime >= (trigger_time - 0.25)

            if not is_after_trig:
                continue

            changed = is_new or current_mtime > prev_mtime or current_size != (previous[1] if previous else 0)
            if changed:
                logger.debug(f"✨ Detected: {path} (size={current_size})")
                time.sleep(1)
                if os.path.exists(path) and os.path.getsize(path) > 0:
                    logger.info(f"📸 พบไฟล์รูปใหม่: {path}")
                    return path

    # Timeout — log ไฟล์ล่าสุดช่วย debug
    all_files = glob.glob(os.path.join(config.DOWNLOAD_DIR, "*.*"))
    latest = sorted(all_files, key=os.path.getmtime, reverse=True)[:5]
    logger.error("❌ Timeout. ไฟล์ล่าสุดใน Downloads:")
    for f in latest:
        logger.error(f"  {os.path.basename(f)} ({time.ctime(os.path.getmtime(f))})")
    raise TimeoutError("ไม่พบไฟล์ screenshot ใหม่ภายในเวลาที่กำหนด")
