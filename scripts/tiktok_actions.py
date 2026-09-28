#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONTOP TikTok Actor – Playwright (không proxy)
Follow / Like / Comment qua browser context + session cookie
"""

from __future__ import annotations
import os, re, json, time, random, threading
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).parent
FULL_JSON = SCRIPT_DIR / "tiktok_full.json"

# Không dùng proxy
PROXY_URL = ""
PROXY_FORCE = False

_lock = threading.Lock()
_map = None
_playwright = None
_browser = None


def _load():
    global _map
    if _map is not None:
        return _map
    _map = {}
    if FULL_JSON.exists():
        try:
            for a in json.loads(FULL_JSON.read_text()):
                for k in (a.get("tt_uid"), a.get("sessionid"), a.get("username"), a.get("user_field")):
                    if k:
                        _map[str(k)] = a
        except Exception as e:
            print("  [warn] load json:", e)
    return _map


def _cookies_list(cookies_str: str):
    out = []
    for part in (cookies_str or "").split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out.append({
            "name": k.strip(),
            "value": v.strip(),
            "domain": ".tiktok.com",
            "path": "/",
        })
    return out


def _ensure_browser():
    global _playwright, _browser
    with _lock:
        if _browser is not None:
            return _browser
        from playwright.sync_api import sync_playwright
        _playwright = sync_playwright().start()
        _browser = _playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"],
        )
        return _browser


def _parse_follow(body: str):
    if not body:
        return False, "empty"
    if "Argus" in body:
        return False, "argus"
    try:
        data = json.loads(body)
    except Exception:
        return False, "not_json"
    sc = data.get("status_code")
    msg = str(data.get("status_msg") or "")
    if sc in (8, "8") or "expired" in msg.lower():
        return False, "login_expired"
    if sc in (10402, "10402"):
        return False, "bad_csrf"
    fs = data.get("follow_status")
    if fs in (1, 2, "1", "2"):
        return True, "follow_status=%s" % fs
    if sc in (0, "0") and fs in (0, "0", None):
        return False, "soft_fail_fs0"
    return False, "code=%s" % sc


class TikTokActor:
    def __init__(self, cookies_str: str):
        self.cookies_str = cookies_str
        self.context = None
        self.page = None

    def start(self):
        browser = _ensure_browser()
        with _lock:
            self.context = browser.new_context(
                viewport={"width": 1365, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="en-US",
            )
            self.page = self.context.new_page()
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            """)
            # Playwright: vào domain trước rồi gắn cookie
            try:
                self.page.goto("https://www.tiktok.com/", wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                print("  [pw] seed warn:", str(e)[:80])
            try:
                self.context.add_cookies(_cookies_list(self.cookies_str))
            except Exception as e:
                print("  [pw] cookie warn:", str(e)[:80])
            try:
                self.page.goto("https://www.tiktok.com/foryou", wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                print("  [pw] foryou warn:", str(e)[:80])
            time.sleep(2 + random.random())
            # debug login cookie
            try:
                names = [c["name"] for c in self.context.cookies() if "session" in c["name"].lower() or c["name"] in ("sid_tt", "sessionid", "sessionid_ss")]
                print("  [pw] session cookies:", names[:6])
            except Exception:
                pass
        return self

    def close(self):
        try:
            if self.context:
                self.context.close()
        except Exception:
            pass
        self.context = None
        self.page = None

    def _csrf_api(self, path: str, body: str) -> dict:
        script = """
            async ([path, body]) => {
              try {
                let ware = '';
                try {
                  const h = await fetch('https://www.tiktok.com/api/commit/follow/user/?aid=1988', {
                    method: 'HEAD', credentials: 'include',
                    headers: {'x-secsdk-csrf-request':'1','x-secsdk-csrf-version':'1.2.5'}
                  });
                  const raw = h.headers.get('x-ware-csrf-token') || '';
                  ware = (raw.split(',')[1] || raw.split(',')[0] || '').trim();
                } catch(e) {}
                const csrf = (document.cookie.split(';').map(s=>s.trim())
                  .find(s=>s.startsWith('tt_csrf_token='))||'=').split('=').slice(1).join('=');
                const headers = {
                  'Content-Type': 'application/x-www-form-urlencoded',
                  'x-tt-csrf-token': csrf,
                  'tt-csrf-token': csrf
                };
                if (ware) headers['x-secsdk-csrf-token'] = ware;
                const r = await fetch(path, {method:'POST', credentials:'include', headers, body});
                const t = await r.text();
                return {status: r.status, body: (t||'').slice(0, 800)};
              } catch(e) { return {error: String(e)}; }
            }
        """
        return self.page.evaluate(script, [path, body])

    def follow(self, user_id: str, username: str = "") -> dict:
        user_id = str(user_id).strip()
        username = (username or "").strip().lstrip("@")
        ui_ok = False
        if username:
            ui_ok = self._follow_ui(username)
        path = ("https://www.tiktok.com/api/commit/follow/user/"
                "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = "action_type=1&user_id=%s&channel_id=0&from=18&from_pre=13" % user_id
        raw, ok, reason = {}, False, "no_attempt"
        for _ in range(3):
            try:
                raw = self._csrf_api(path, body)
                ok, reason = _parse_follow(raw.get("body", ""))
                if ok or reason == "login_expired":
                    break
                time.sleep(1.2)
            except Exception as e:
                reason = str(e)[:40]
                time.sleep(1.2)
        if ok:
            return {"ok": True, "action": "follow", "target": user_id, "reason": reason, "raw": raw, "ui": ui_ok}
        if ui_ok:
            return {"ok": True, "action": "follow", "target": user_id, "reason": "ui_clicked", "raw": raw, "ui": True}
        return {"ok": False, "action": "follow", "target": user_id, "reason": reason, "raw": raw, "ui": ui_ok}

    def _follow_ui(self, username: str) -> bool:
        try:
            self.page.goto("https://www.tiktok.com/@%s" % username, wait_until="domcontentloaded", timeout=40000)
            time.sleep(2.5 + random.random())
            selectors = [
                "[data-e2e='follow-button']",
                "button[data-e2e='follow-button']",
                "button[data-e2e='user-follow']",
            ]
            for sel in selectors:
                loc = self.page.locator(sel)
                if loc.count() == 0:
                    continue
                for i in range(min(loc.count(), 3)):
                    el = loc.nth(i)
                    try:
                        txt = (el.inner_text(timeout=2000) or "").lower()
                    except Exception:
                        txt = ""
                    if "following" in txt or "requested" in txt or "đang follow" in txt:
                        return True
                    if "follow" in txt or "theo dõi" in txt or not txt.strip():
                        try:
                            el.click(timeout=3000)
                            time.sleep(1.5)
                            return True
                        except Exception:
                            continue
            for text in ("Follow", "Theo dõi"):
                btn = self.page.get_by_role("button", name=re.compile(text, re.I))
                if btn.count():
                    try:
                        t = (btn.first.inner_text(timeout=1500) or "").lower()
                        if "following" in t:
                            return True
                        btn.first.click(timeout=3000)
                        time.sleep(1.5)
                        return True
                    except Exception:
                        pass
        except Exception:
            pass
        return False

    def like(self, aweme_id: str) -> dict:
        aweme_id = str(aweme_id).strip()
        path = ("https://www.tiktok.com/api/commit/item/digg/"
                "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = "aweme_id=%s&type=1&channel_id=0" % aweme_id
        try:
            raw = self._csrf_api(path, body)
            data = {}
            try:
                data = json.loads(raw.get("body") or "{}")
            except Exception:
                pass
            if data.get("status_code") in (0, "0") and data.get("is_digg") in (1, True, "1"):
                return {"ok": True, "action": "like", "target": aweme_id, "reason": "liked", "raw": raw}
            if self._like_ui():
                return {"ok": True, "action": "like", "target": aweme_id, "reason": "ui", "raw": raw}
            return {"ok": False, "action": "like", "reason": str(data.get("status_msg") or "fail")[:40], "raw": raw}
        except Exception as e:
            return {"ok": False, "action": "like", "error": str(e)}

    def _like_ui(self) -> bool:
        try:
            self.page.goto("https://www.tiktok.com/foryou", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            vid = self.page.locator("video").first
            if vid.count():
                box = vid.bounding_box()
                if box:
                    self.page.mouse.dblclick(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                    time.sleep(1)
                    return True
        except Exception:
            pass
        return False

    def comment(self, aweme_id: str, text: str = "nice") -> dict:
        aweme_id = str(aweme_id).strip()
        text = (text or "nice")[:120]
        path = ("https://www.tiktok.com/api/comment/publish/"
                "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = "aweme_id=%s&text=%s&text_extra=%%5B%%5D&channel_id=0" % (aweme_id, quote(text))
        try:
            raw = self._csrf_api(path, body)
            data = {}
            try:
                data = json.loads(raw.get("body") or "{}")
            except Exception:
                pass
            if data.get("status_code") in (0, "0"):
                return {"ok": True, "action": "comment", "target": aweme_id, "reason": "ok", "raw": raw}
            return {"ok": False, "action": "comment", "reason": str(data.get("status_msg") or "fail")[:40], "raw": raw}
        except Exception as e:
            return {"ok": False, "action": "comment", "error": str(e)}


def get_actor_for_account(acc: dict) -> TikTokActor:
    m = _load()
    data = None
    for k in (acc.get("id"), acc.get("username"), acc.get("sessionid"), acc.get("user_field")):
        if k and str(k) in m:
            data = m[str(k)]
            break
    if not data or not data.get("cookies"):
        raise RuntimeError("Thiếu cookies cho %s" % acc.get("username"))
    return TikTokActor(data["cookies"]).start()


def do_task_action(actor: TikTokActor, job_key: str, task: dict) -> dict:
    if job_key in ("sub", "vip"):
        uid = str(task.get("uid") or "").strip()
        uname = str(task.get("link") or task.get("username") or "").strip().lstrip("@")
        if "/" in uname:
            m = re.search(r"@([\w._]+)", uname)
            uname = m.group(1) if m else uname
        if not uid.isdigit() and not uname:
            return {"ok": False, "action": "follow", "error": "missing_uid"}
        return actor.follow(uid or "0", uname)

    if job_key == "tim":
        aweme = str(task.get("idpost") or "")
        if not aweme.isdigit():
            m = re.search(r"/video/(\d+)", str(task.get("link") or ""))
            aweme = m.group(1) if m else ""
        if not aweme:
            return {"ok": False, "action": "like", "error": "no_aweme"}
        return actor.like(aweme)

    if job_key == "cmt":
        aweme = str(task.get("idpost") or "")
        link = str(task.get("link") or "")
        if not aweme.isdigit():
            m = re.search(r"/video/(\d+)", link)
            aweme = m.group(1) if m else ""
        text = "nice"
        nd = task.get("nd")
        if nd:
            try:
                arr = json.loads(nd) if isinstance(nd, str) else nd
                if isinstance(arr, list) and arr:
                    text = str(arr[0])[:120]
            except Exception:
                text = str(nd)[:120]
        if not aweme:
            return {"ok": False, "action": "comment", "error": "no_aweme"}
        return actor.comment(aweme, text)

    return {"ok": False, "error": "unknown_job"}
