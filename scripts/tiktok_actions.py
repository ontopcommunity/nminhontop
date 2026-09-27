#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TikTok actions – Follow verified status_code=0 via Chrome+csrf"""

import re, json, time, threading
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FULL_JSON = SCRIPT_DIR / "tiktok_full.json"
_lock = threading.Lock()
_cookie_map = None

def _load_cookies():
    global _cookie_map
    if _cookie_map is not None:
        return _cookie_map
    _cookie_map = {}
    if FULL_JSON.exists():
        for a in json.loads(FULL_JSON.read_text()):
            for k in (a.get("tt_uid"), a.get("sessionid"), a.get("username"), a.get("user_field")):
                if k:
                    _cookie_map[k] = a
    return _cookie_map

def _parse_cookie_str(cookies_str):
    out = []
    for part in cookies_str.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out.append({"name": k.strip(), "value": v.strip(), "domain": ".tiktok.com", "path": "/"})
    return out

def _make_driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,720")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.binary_location = "/usr/bin/google-chrome"
    d = webdriver.Chrome(options=opts)
    d.set_page_load_timeout(45)
    return d

def _init_session(driver, cookies_str):
    driver.get("https://www.tiktok.com/")
    time.sleep(1.2)
    for c in _parse_cookie_str(cookies_str):
        try:
            driver.add_cookie(c)
        except Exception:
            pass
    driver.get("https://www.tiktok.com/foryou")
    time.sleep(2.5)

def _csrf_fetch(driver, url, body):
    script = """
        const done = arguments[arguments.length - 1];
        const url = arguments[0];
        const body = arguments[1];
        const csrf = (document.cookie.split(';').map(s => s.trim()).find(s => s.startsWith('tt_csrf_token=')) || '=').split('=').slice(1).join('=');
        fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'x-tt-csrf-token': csrf,
            'tt-csrf-token': csrf
          },
          body: body,
          credentials: 'include'
        }).then(r => r.text().then(t => done({status: r.status, body: t.slice(0, 500)})))
          .catch(e => done({error: String(e)}));
    """
    return driver.execute_async_script(script, url, body)

def _ok_status(body: str) -> bool:
    if not body or "Argus" in body:
        return False
    try:
        data = json.loads(body)
        if data.get("status_code") in (0, "0"):
            return True
        if data.get("follow_status") in (1, 2):
            return True
    except Exception:
        pass
    return False

class TikTokActor:
    def __init__(self, cookies_str: str):
        self.cookies_str = cookies_str
        self.driver = None

    def start(self):
        with _lock:
            self.driver = _make_driver()
            _init_session(self.driver, self.cookies_str)
        return self

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def follow(self, user_id: str) -> dict:
        url = "https://www.tiktok.com/api/commit/follow/user/?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web"
        body = f"action_type=1&user_id={user_id}&channel_id=0&from=18"
        try:
            r = _csrf_fetch(self.driver, url, body)
            return {"ok": _ok_status(r.get("body", "")), "action": "follow", "target": user_id, "raw": r}
        except Exception as e:
            return {"ok": False, "action": "follow", "error": str(e)}

    def like(self, aweme_id: str) -> dict:
        url = "https://www.tiktok.com/api/commit/item/digg/?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web"
        body = f"aweme_id={aweme_id}&type=1&channel_id=0"
        try:
            r = _csrf_fetch(self.driver, url, body)
            ok = _ok_status(r.get("body", ""))
            return {"ok": ok, "action": "like", "target": aweme_id, "raw": r}
        except Exception as e:
            return {"ok": False, "action": "like", "error": str(e)}

    def comment(self, aweme_id: str, text: str = "nice") -> dict:
        from urllib.parse import quote
        url = "https://www.tiktok.com/api/comment/publish/?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web"
        body = f"aweme_id={aweme_id}&text={quote(text)}&text_extra=%5B%5D&channel_id=0"
        try:
            r = _csrf_fetch(self.driver, url, body)
            ok = _ok_status(r.get("body", ""))
            return {"ok": ok, "action": "comment", "target": aweme_id, "raw": r}
        except Exception as e:
            return {"ok": False, "action": "comment", "error": str(e)}

    def share(self, aweme_id: str) -> dict:
        url = "https://www.tiktok.com/api/item/share/action/?aid=1988&app_name=tiktok_web&device_platform=web"
        body = f"item_id={aweme_id}&share_type=1"
        try:
            r = _csrf_fetch(self.driver, url, body)
            return {"ok": _ok_status(r.get("body", "")), "action": "share", "target": aweme_id, "raw": r}
        except Exception as e:
            return {"ok": False, "action": "share", "error": str(e)}

def get_actor_for_account(acc: dict) -> TikTokActor:
    m = _load_cookies()
    data = None
    for k in (acc.get("id"), acc.get("username"), acc.get("sessionid"), acc.get("user_field")):
        if k and k in m:
            data = m[k]
            break
    if not data or not data.get("cookies"):
        raise RuntimeError("Không có full cookies cho acc %s" % acc.get("username"))
    return TikTokActor(data["cookies"]).start()

def do_task_action(actor: TikTokActor, job_key: str, task: dict) -> dict:
    if job_key in ("sub", "vip"):
        uid = str(task.get("uid") or "")
        if not uid:
            return {"ok": False, "action": "follow", "error": "missing uid"}
        return actor.follow(uid)
    if job_key == "tim":
        aweme = str(task.get("idpost") or "")
        if not aweme.isdigit():
            m = re.search(r"/video/(\\d+)", str(task.get("link") or ""))
            if m:
                aweme = m.group(1)
        if not aweme:
            return {"ok": False, "action": "like", "error": "no aweme_id"}
        return actor.like(aweme)
    if job_key == "cmt":
        aweme = str(task.get("idpost") or "")
        link = str(task.get("link") or "")
        if not aweme.isdigit():
            m = re.search(r"/video/(\\d+)", link)
            if m:
                aweme = m.group(1)
        text = "nice"
        nd = task.get("nd")
        if nd:
            try:
                arr = json.loads(nd) if isinstance(nd, str) else nd
                if isinstance(arr, list) and arr:
                    text = str(arr[0])
            except Exception:
                text = str(nd)[:100]
        if not aweme:
            return {"ok": False, "action": "comment", "error": "no aweme_id"}
        return actor.comment(aweme, text)
    return {"ok": False, "error": "unknown job %s" % job_key}
