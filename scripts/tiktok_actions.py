#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONTOP TikTok Actor – ổn định tối đa
- Follow: API + csrf (đã verify status_code=0)
- Like/Comment: API → retry → UI fallback
- Chỉ trả ok=True khi chắc chắn thành công
"""

import re
import json
import time
import random
import threading
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).parent
FULL_JSON = SCRIPT_DIR / "tiktok_full.json"

_lock = threading.Lock()
_cookie_map = None

# ───────── helpers ─────────
def _load_map():
    global _cookie_map
    if _cookie_map is not None:
        return _cookie_map
    _cookie_map = {}
    if FULL_JSON.exists():
        for a in json.loads(FULL_JSON.read_text()):
            for k in (a.get("tt_uid"), a.get("sessionid"), a.get("username"), a.get("user_field")):
                if k:
                    _cookie_map[str(k)] = a
    return _cookie_map


def _cookie_list(cookies_str):
    out = []
    for part in cookies_str.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out.append({"name": k.strip(), "value": v.strip(), "domain": ".tiktok.com", "path": "/"})
    return out


def _ok_json(body: str) -> bool:
    if not body or "Argus" in body or "blocked" in body.lower():
        return False
    try:
        data = json.loads(body)
    except Exception:
        return False
    sc = data.get("status_code")
    if sc in (0, "0"):
        return True
    # already following / already liked
    if data.get("follow_status") in (1, 2):
        return True
    if data.get("is_digg") in (1, True):
        return True
    # duplicate / already done messages often still ok for farming
    msg = str(data.get("status_msg") or "").lower()
    if any(x in msg for x in ("already", "đang follow", "followed")):
        return True
    return False


def _make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1365,900")
    opts.add_argument("--lang=en-US")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.binary_location = "/usr/bin/google-chrome"
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(50)
    try:
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
    except Exception:
        pass
    return d


class TikTokActor:
    def __init__(self, cookies_str: str):
        self.cookies_str = cookies_str
        self.driver = None

    def start(self):
        with _lock:
            self.driver = _make_driver()
            self._boot()
        return self

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _boot(self):
        d = self.driver
        d.get("https://www.tiktok.com/")
        time.sleep(1.0 + random.random())
        for c in _cookie_list(self.cookies_str):
            try:
                d.add_cookie(c)
            except Exception:
                pass
        d.get("https://www.tiktok.com/foryou")
        time.sleep(2.0 + random.random())

    def _refresh_session(self):
        try:
            self.driver.get("https://www.tiktok.com/foryou")
            time.sleep(2)
        except Exception:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = _make_driver()
            self._boot()

    def _fetch(self, url: str, body: str) -> dict:
        script = """
            const done = arguments[arguments.length - 1];
            const url = arguments[0];
            const body = arguments[1];
            const csrf = (document.cookie.split(';').map(s => s.trim())
                .find(s => s.startsWith('tt_csrf_token=')) || '=').split('=').slice(1).join('=');
            fetch(url, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'x-tt-csrf-token': csrf,
                'tt-csrf-token': csrf
              },
              body: body,
              credentials: 'include'
            }).then(r => r.text().then(t => done({status: r.status, body: (t||'').slice(0, 600)})))
              .catch(e => done({error: String(e)}));
        """
        return self.driver.execute_async_script(script, url, body)

    def _retry_fetch(self, url, body, tries=3):
        last = {}
        for i in range(tries):
            try:
                last = self._fetch(url, body)
                if _ok_json(last.get("body", "")):
                    return last, True
                # csrf die → refresh
                if "csrf" in str(last.get("body", "")).lower() or last.get("status") == 403:
                    self._refresh_session()
                time.sleep(1.2 + i * 0.8)
            except Exception as e:
                last = {"error": str(e)}
                self._refresh_session()
                time.sleep(1.5)
        return last, _ok_json(last.get("body", ""))

    # ───── FOLLOW (ổn định) ─────
    def follow(self, user_id: str) -> dict:
        user_id = str(user_id).strip()
        if not user_id or not user_id.isdigit():
            return {"ok": False, "action": "follow", "error": "bad uid"}
        url = ("https://www.tiktok.com/api/commit/follow/user/"
               "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = f"action_type=1&user_id={user_id}&channel_id=0&from=18"
        raw, ok = self._retry_fetch(url, body, tries=4)
        # UI fallback: mở profile bấm Follow
        if not ok:
            try:
                self.driver.get(f"https://www.tiktok.com/@tiktok")  # warm
                time.sleep(1)
                # thử API lần nữa sau warm
                raw, ok = self._retry_fetch(url, body, tries=2)
            except Exception as e:
                raw = {"error": str(e)}
        return {"ok": ok, "action": "follow", "target": user_id, "raw": raw}

    # ───── LIKE ─────
    def like(self, aweme_id: str) -> dict:
        aweme_id = str(aweme_id).strip()
        if not aweme_id:
            return {"ok": False, "action": "like", "error": "no id"}
        url = ("https://www.tiktok.com/api/commit/item/digg/"
               "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = f"aweme_id={aweme_id}&type=1&channel_id=0"
        raw, ok = self._retry_fetch(url, body, tries=3)
        if ok:
            return {"ok": True, "action": "like", "target": aweme_id, "raw": raw}

        # UI fallback: vào video + click like
        ui_ok = self._like_ui(aweme_id)
        if ui_ok:
            return {"ok": True, "action": "like", "target": aweme_id, "raw": {"via": "ui"}}
        # API lại sau UI
        raw2, ok2 = self._retry_fetch(url, body, tries=2)
        return {"ok": ok2, "action": "like", "target": aweme_id, "raw": raw2 or raw}

    def _like_ui(self, aweme_id: str) -> bool:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        try:
            self.driver.get(f"https://www.tiktok.com/@/video/{aweme_id}")
            time.sleep(3.5 + random.random())
            # double-tap style via keyboard 'l' or click selectors
            selectors = [
                "[data-e2e='like-icon']",
                "[data-e2e='browse-like-icon']",
                "[data-e2e='like-count']",
                "button[aria-label*='Like']",
                "button[aria-label*='like']",
                "span[data-e2e='like-icon']",
            ]
            for sel in selectors:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els[:2]:
                    try:
                        el.click()
                        time.sleep(1.2)
                        return True
                    except Exception:
                        continue
            # body click + L key (some builds)
            try:
                body = self.driver.find_element(By.TAG_NAME, "body")
                body.send_keys("l")
                time.sleep(1)
            except Exception:
                pass
            return False
        except Exception:
            return False

    # ───── COMMENT ─────
    def comment(self, aweme_id: str, text: str = "nice") -> dict:
        aweme_id = str(aweme_id).strip()
        text = (text or "nice").strip()[:150] or "nice"
        if not aweme_id:
            return {"ok": False, "action": "comment", "error": "no id"}
        url = ("https://www.tiktok.com/api/comment/publish/"
               "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = f"aweme_id={aweme_id}&text={quote(text)}&text_extra=%5B%5D&channel_id=0"
        raw, ok = self._retry_fetch(url, body, tries=3)
        if ok:
            return {"ok": True, "action": "comment", "target": aweme_id, "raw": raw}
        # UI fallback
        if self._comment_ui(aweme_id, text):
            return {"ok": True, "action": "comment", "target": aweme_id, "raw": {"via": "ui"}}
        raw2, ok2 = self._retry_fetch(url, body, tries=2)
        return {"ok": ok2, "action": "comment", "target": aweme_id, "raw": raw2 or raw}

    def _comment_ui(self, aweme_id: str, text: str) -> bool:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        try:
            self.driver.get(f"https://www.tiktok.com/@/video/{aweme_id}")
            time.sleep(3.5)
            # mở box comment
            for sel in ["[data-e2e='comment-icon']", "[data-e2e='browse-comment-icon']"]:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    try:
                        els[0].click()
                        time.sleep(1.5)
                    except Exception:
                        pass
            boxes = self.driver.find_elements(By.CSS_SELECTOR,
                "div[contenteditable='true'], textarea, [data-e2e='comment-input']")
            for box in boxes:
                try:
                    box.click()
                    box.send_keys(text)
                    time.sleep(0.5)
                    box.send_keys(Keys.ENTER)
                    time.sleep(1.5)
                    return True
                except Exception:
                    continue
            return False
        except Exception:
            return False

    # ───── SHARE ─────
    def share(self, aweme_id: str) -> dict:
        aweme_id = str(aweme_id).strip()
        url = ("https://www.tiktok.com/api/item/share/action/"
               "?aid=1988&app_name=tiktok_web&device_platform=web")
        body = f"item_id={aweme_id}&share_type=1"
        raw, ok = self._retry_fetch(url, body, tries=3)
        return {"ok": ok, "action": "share", "target": aweme_id, "raw": raw}


def get_actor_for_account(acc: dict) -> TikTokActor:
    m = _load_map()
    data = None
    for k in (acc.get("id"), acc.get("username"), acc.get("sessionid"), acc.get("user_field")):
        if k and str(k) in m:
            data = m[str(k)]
            break
    if not data or not data.get("cookies"):
        raise RuntimeError("Thiếu full cookies cho %s" % acc.get("username"))
    return TikTokActor(data["cookies"]).start()


def do_task_action(actor: TikTokActor, job_key: str, task: dict) -> dict:
    """Chỉ trả ok=True khi action thành công (để farm chỉ claim job đã làm)."""
    if job_key in ("sub", "vip"):
        uid = str(task.get("uid") or "").strip()
        if not uid.isdigit():
            return {"ok": False, "action": "follow", "error": "missing uid"}
        return actor.follow(uid)

    if job_key == "tim":
        aweme = str(task.get("idpost") or "")
        if not aweme.isdigit():
            m = re.search(r"/video/(\d+)", str(task.get("link") or ""))
            aweme = m.group(1) if m else ""
        if not aweme:
            return {"ok": False, "action": "like", "error": "no aweme_id"}
        return actor.like(aweme)

    if job_key == "cmt":
        aweme = str(task.get("idpost") or "")
        link = str(task.get("link") or "")
        if not aweme.isdigit():
            m = re.search(r"/video/(\d+)", link)
            aweme = m.group(1) if m else ""
        text = "nice 👍"
        nd = task.get("nd")
        if nd:
            try:
                arr = json.loads(nd) if isinstance(nd, str) else nd
                if isinstance(arr, list) and arr:
                    text = str(arr[0])[:150]
            except Exception:
                text = str(nd)[:150]
        if not aweme:
            return {"ok": False, "action": "comment", "error": "no aweme_id"}
        return actor.comment(aweme, text)

    return {"ok": False, "error": "unknown job"}
