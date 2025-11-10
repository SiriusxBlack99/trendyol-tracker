# -*- coding: utf-8 -*-
import os, requests
from dotenv import load_dotenv

load_dotenv()

def _get_proxy():
    proxy = os.getenv("HTTP_PROXY","").strip()
    return {"http": proxy, "https": proxy} if proxy else None

def tg_send(text: str) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat_id:
        print("[warn] Telegram not configured")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, data={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, timeout=25, proxies=_get_proxy())
        ok = r.status_code == 200 and r.json().get("ok", False)
        print("[tg]", r.status_code, r.text[:200])
        return ok
    except Exception as e:
        print("[tg error]", e)
        return False
