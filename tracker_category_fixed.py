# -*- coding: utf-8 -*-
import asyncio, json, os, re, time
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv
load_dotenv()
import playwright.async_api as pw
import requests

ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
SEEN_PATH = "seen.json"

def num(s):
    if not s:
        return None
    s = s.replace("\u066c", "").replace("\u066b", ".")
    s = s.translate(ARABIC_DIGITS)
    s = re.sub(r"[^0-9\.]", "", s)
    try:
        return float(s) if s else None
    except:
        return None

def load_cfg():
    with open("config.json","r",encoding="utf-8") as f:
        return json.load(f)

def is_excluded(title, cfg):
    t = (title or "").lower()
    for w in cfg.get("exclude_keywords", []):
        if w.strip() and w.strip().lower() in t:
            return True
    inc = cfg.get("include_keywords", [])
    if inc:
        return not any(w.strip().lower() in t for w in inc if w.strip())
    return False

def passes_policy(item, cfg):
    limit = float(cfg.get("alert_price_sar", 20))
    pct = float(cfg.get("percent_drop_at", 0))
    p = item.get("price")
    o = item.get("orig")
    if p is None: 
        return False, "no price"
    if p <= limit:
        return True, f"price <= {limit}"
    if pct > 0 and p is not None and o:
        try:
            drop = (o - p) / o * 100.0
            if drop >= pct:
                return True, f"drop {drop:.1f}%"
        except:
            pass
    return False, ""

def save_seen(seen):
    try:
        with open(SEEN_PATH,"w",encoding="utf-8") as f:
            json.dump(list(seen), f)
    except:
        pass

def load_seen():
    try:
        with open(SEEN_PATH,"r",encoding="utf-8") as f:
            return set(json.load(f))
    except:
        return set()

def tg_send(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID","").strip()
    if not token or not chat_id:
        print("[warn] TELEGRAM credentials missing")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": chat_id, "text": text, "disable_web_page_preview": True}, timeout=15)
        if r.status_code != 200:
            print(f"[warn] telegram send failed {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[warn] telegram error {e}")

async def accept_cookies(page):
    texts = ["قبول", "أوافق", "Kabul Et", "Kabul", "Accept All", "Accept"]
    for selector in [
        'button:has-text("قبول")',
        'button:has-text("أوافق")',
        'button:has-text("Kabul")',
        'button:has-text("Accept")',
        '[data-testid="privacy-accept"] button',
        'button#onetrust-accept-btn-handler'
    ]:
        try:
            btn = page.locator(selector).first
            if await btn.count():
                await btn.click()
                await page.wait_for_timeout(400)
                return True
        except:
            pass
    # try by text scan
    for t in texts:
        try:
            btn = page.get_by_text(t, exact=False).first
            if await btn.count():
                await btn.click()
                await page.wait_for_timeout(400)
                return True
        except:
            pass
    return False

async def wait_products(page, timeout=15000):
    sels = [
        '[data-testid="productCardItem"]',
        'div.p-card-wrppr',
        'div.product-card',
        'div.prdct-cntnr-card',
    ]
    for s in sels:
        try:
            await page.wait_for_selector(s, timeout=timeout)
            return s
        except:
            continue
    return None

async def scroll_all(page, card_sel, max_rounds=20):
    prev = 0
    same = 0
    for i in range(max_rounds):
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await page.wait_for_timeout(700)
        count = await page.locator(card_sel).count()
        if count == prev:
            same += 1
        else:
            same = 0
        prev = count
        if same >= 3:  # stopped loading
            break
    return prev

async def extract_products(page, card_sel):
    cards = page.locator(card_sel)
    n = await cards.count()
    out = []
    for i in range(n):
        c = cards.nth(i)
        title = await c.locator('h3[data-testid="productName"]').first.text_content().catch(lambda _: None)
        if not title:
            title = await c.locator("h3").first.text_content().catch(lambda _: None)
        price_text = None
        for sel in ['[data-testid="price-current"]',
                    '.prc-box-dscntd',
                    '.prc-box-sllng',
                    '[class*=\"price\"][class*=\"current\"]']:
            try:
                t = await c.locator(sel).first.text_content()
                if t: 
                    price_text = t
                    break
            except:
                pass
        orig_text = None
        for sel in ['[data-testid=\"price-original\"]',
                    '.prc-box-orgnl',
                    '.prc-box-orgnl-prc']:
            try:
                t = await c.locator(sel).first.text_content()
                if t:
                    orig_text = t
                    break
            except:
                pass
        href = None
        try:
            href = await c.locator("a").first.get_attribute("href")
        except:
            pass
        p = num(price_text)
        o = num(orig_text)
        out.append({
            "title": (title or "").strip(),
            "price": p,
            "orig": o,
            "url": ("https://www.trendyol.com" + href) if href and href.startswith("/") else href
        })
    return out

async def collect_category(cfg):
    url = cfg["category_url"]
    headless = bool(cfg.get("headless", True))
    max_pages = int(cfg.get("max_pages", 1))
    stop_on_empty = bool(cfg.get("stop_on_empty", True))
    min_rating = float(cfg.get("min_rating", 0))
    min_reviews = int(cfg.get("min_reviews", 0))  # placeholders

    seen = load_seen()
    alerts = 0
    total_seen = 0

    async with pw.async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context(locale="ar", extra_http_headers={
            "Accept-Language": "ar,en;q=0.9,tr;q=0.8"
        }, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")
        page = await ctx.new_page()

        for pi in range(1, max_pages+1):
            final_url = url
            # ensure page index
            if "pi=" not in final_url:
                join = "&" if "?" in final_url else "?"
                final_url = f"{final_url}{join}pi={pi}"
            print(f"[page] {final_url}")
            await page.goto(final_url, wait_until="domcontentloaded", timeout=60000)
            await accept_cookies(page)
            sel = await wait_products(page)
            if not sel:
                print("[info] no items found on this page")
                if stop_on_empty:
                    break
                else:
                    continue

            await scroll_all(page, sel, max_rounds=25)
            items = await extract_products(page, sel)
            if not items:
                print("[info] no items after scroll")
                if stop_on_empty:
                    break
                else:
                    continue

            for it in items:
                total_seen += 1
                key = (it.get("url") or it.get("title")) or ""
                if not key or key in seen: 
                    continue
                seen.add(key)
                if is_excluded(it["title"], cfg):
                    continue
                ok, reason = passes_policy(it, cfg)
                if ok:
                    alerts += 1
                    title = (it["title"] or "")[:80]
                    price = it["price"]
                    orig = it["orig"]
                    msg = f"خصم ترينديول\n{title}\nالسعر الآن: {price} SAR" + (f" | كان: {orig}" if orig else "") + f"\n{it.get('url') or ''}\nسبب التنبيه: {reason}"
                    print("[alert]", msg.replace("\n"," | "))
                    tg_send(msg)

        print(f"[done] total seen: {total_seen}, alerts: {alerts}")
        save_seen(seen)
        await ctx.close()
        await browser.close()

def main_once():
    cfg = load_cfg()
    asyncio.run(collect_category(cfg))

if __name__ == "__main__":
    main_once()
