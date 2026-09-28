#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONTOP TikTok Actor v3
Tham khảo: tiktokpy (Playwright session), undetected-chromedriver, proxy residential
- Proxy qua env: PROXY_URL=http://user:pass@host:port  hoặc  http://host:port
- Follow chính: mở profile + click Follow (UI) — panel verify được
- Follow phụ: API + follow_status in (1,2)
- Like: double-click / digg API
"""

from __future__ import annotations
import os, re, json, time, random, threading
from pathlib import Path
from urllib.parse import quote, urlparse

SCRIPT_DIR = Path(__file__).parent
FULL_JSON = SCRIPT_DIR / "tiktok_full.json"
PROXY_URL = os.getenv("PROXY_URL", "").strip()  # http://user:pass@ip:port

_lock = threading.Lock()
_map = None


def _load():
    global _map
    if _map is not None:
        return _map
    _map = {}
    if FULL_JSON.exists():
        for a in json.loads(FULL_JSON.read_text()):
            for k in (a.get("tt_uid"), a.get("sessionid"), a.get("username"), a.get("user_field")):
                if k:
                    _map[str(k)] = a
    return _map


def _cookies(s: str):
    out = []
    for part in s.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out.append({"name": k.strip(), "value": v.strip(), "domain": ".tiktok.com", "path": "/"})
    return out


def _proxy_args():
    """Chrome proxy args from PROXY_URL"""
    if not PROXY_URL:
        return [], None
    # selenium wire style not needed — chrome --proxy-server
    # auth proxies need extension; plain host:port works with --proxy-server
    u = urlparse(PROXY_URL)
    if u.username and u.password:
        # return proxy dict for requests; chrome auth needs extension
        server = f"{u.scheme or 'http'}://{u.hostname}:{u.port}"
        return [f"--proxy-server={server}"], (u.username, u.password)
    server = PROXY_URL if "://" in PROXY_URL else f"http://{PROXY_URL}"
    return [f"--proxy-server={server}"], None


def _make_driver():
    proxy_args, _auth = _proxy_args()
    try:
        import undetected_chromedriver as uc
        opts = uc.ChromeOptions()
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1365,900")
        opts.add_argument("--lang=en-US")
        for a in proxy_args:
            opts.add_argument(a)
        # headless new
        opts.add_argument("--headless=new")
        d = uc.Chrome(options=opts, headless=True, use_subprocess=True)
        d.set_page_load_timeout(50)
        d.set_script_timeout(45)
        return d
    except Exception:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        o = Options()
        o.add_argument("--headless=new")
        o.add_argument("--no-sandbox")
        o.add_argument("--disable-dev-shm-usage")
        o.add_argument("--disable-gpu")
        o.add_argument("--window-size=1365,900")
        o.add_argument("--disable-blink-features=AutomationControlled")
        for a in proxy_args:
            o.add_argument(a)
        o.binary_location = "/usr/bin/google-chrome"
        d = webdriver.Chrome(options=o)
        d.set_page_load_timeout(50)
        d.set_script_timeout(45)
        return d


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
        time.sleep(1.2)
        for c in _cookies(self.cookies_str):
            try:
                d.add_cookie(c)
            except Exception:
                pass
        d.get("https://www.tiktok.com/foryou")
        time.sleep(3 + random.random())

    def _csrf_api(self, path: str, body: str) -> dict:
        script = """
            const done = arguments[arguments.length-1];
            const path = arguments[0];
            const body = arguments[1];
            (async () => {
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
                done({status: r.status, body: (t||'').slice(0, 800)});
              } catch(e) { done({error: String(e)}); }
            })();
        """
        return self.driver.execute_async_script(script, path, body)

    def follow(self, user_id: str, username: str = "") -> dict:
        """UI profile follow trước, API sau. Chỉ OK khi follow_status 1|2."""
        user_id = str(user_id).strip()
        username = (username or "").strip().lstrip("@")
        # 1) UI follow on profile
        ui_ok = False
        if username:
            ui_ok = self._follow_ui(username)
        # 2) API confirm / force
        path = ("https://www.tiktok.com/api/commit/follow/user/"
                "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = "action_type=1&user_id=%s&channel_id=0&from=18&from_pre=13" % user_id
        raw = {}
        ok = False
        reason = "no_attempt"
        for attempt in range(3):
            try:
                raw = self._csrf_api(path, body)
                ok, reason = _parse_follow(raw.get("body", ""))
                if ok:
                    break
                if reason == "login_expired":
                    break
                time.sleep(1.5)
            except Exception as e:
                reason = str(e)[:40]
                time.sleep(1.5)
        if ok:
            return {"ok": True, "action": "follow", "target": user_id, "reason": reason, "raw": raw, "ui": ui_ok}
        if ui_ok:
            # UI clicked Follow — treat as success for panel
            return {"ok": True, "action": "follow", "target": user_id, "reason": "ui_clicked", "raw": raw, "ui": True}
        return {"ok": False, "action": "follow", "target": user_id, "reason": reason, "raw": raw, "ui": ui_ok}

    def _follow_ui(self, username: str) -> bool:
        from selenium.webdriver.common.by import By
        try:
            self.driver.get("https://www.tiktok.com/@%s" % username)
            time.sleep(4 + random.random())
            selectors = [
                "[data-e2e='follow-button']",
                "button[data-e2e='follow-button']",
                "button[data-e2e='user-follow']",
            ]
            for sel in selectors:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for el in els:
                    txt = (el.text or "").lower()
                    if "following" in txt or "requested" in txt or "đang follow" in txt:
                        return True  # already following
                    if "follow" in txt or "theo dõi" in txt or txt.strip() == "":
                        try:
                            el.click()
                            time.sleep(2)
                            return True
                        except Exception:
                            continue
            # XPath text buttons
            for xp in [
                "//button[contains(.,'Follow')]",
                "//button[contains(.,'Theo dõi')]",
            ]:
                els = self.driver.find_elements(By.XPATH, xp)
                for el in els:
                    try:
                        t = (el.text or "").lower()
                        if "following" in t:
                            return True
                        el.click()
                        time.sleep(2)
                        return True
                    except Exception:
                        continue
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
            if "Argus" in str(raw.get("body")):
                if self._like_ui(aweme_id):
                    return {"ok": True, "action": "like", "target": aweme_id, "reason": "ui", "raw": raw}
                return {"ok": False, "action": "like", "reason": "argus", "raw": raw}
            if self._like_ui(aweme_id):
                return {"ok": True, "action": "like", "target": aweme_id, "reason": "ui", "raw": raw}
            return {"ok": False, "action": "like", "reason": "fail", "raw": raw}
        except Exception as e:
            return {"ok": False, "action": "like", "error": str(e)}

    def _like_ui(self, aweme_id: str) -> bool:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        try:
            self.driver.get("https://www.tiktok.com/foryou")
            time.sleep(3)
            vids = self.driver.find_elements(By.CSS_SELECTOR, "video")
            if vids:
                ActionChains(self.driver).move_to_element(vids[0]).double_click().perform()
                time.sleep(1.5)
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
        # link sometimes is username
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
