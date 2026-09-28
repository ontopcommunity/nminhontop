#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONTOP TikTok Actor v2
Chrome + session cookie + secsdk CSRF
Follow/Like/Comment + UI fallback + login_expired detect
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


def _cookies(s):
    out = []
    for part in s.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out.append({"name": k.strip(), "value": v.strip(), "domain": ".tiktok.com", "path": "/"})
    return out


def _parse_ok(body: str):
    if not body:
        return False, "empty"
    if "Argus" in body or "blocked" in body.lower():
        return False, "argus_block"
    try:
        data = json.loads(body)
    except Exception:
        return False, "not_json"
    sc = data.get("status_code")
    msg = str(data.get("status_msg") or "")
    if sc in (0, "0"):
        return True, "ok"
    if sc in (8, "8") or "expired" in msg.lower():
        return False, "login_expired"
    if sc in (10402, "10402") or "csrf" in msg.lower():
        return False, "bad_csrf"
    if data.get("follow_status") in (1, 2):
        return True, "already_following"
    if data.get("is_digg") in (1, True):
        return True, "already_liked"
    return False, "code=%s:%s" % (sc, msg[:40])


def _driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    o = Options()
    o.add_argument("--headless=new")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--disable-gpu")
    o.add_argument("--window-size=1365,900")
    o.add_argument("--disable-blink-features=AutomationControlled")
    o.add_experimental_option("excludeSwitches", ["enable-automation"])
    o.add_experimental_option("useAutomationExtension", False)
    o.binary_location = "/usr/bin/google-chrome"
    d = webdriver.Chrome(options=o)
    d.set_page_load_timeout(50)
    try:
        d.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"
        })
    except Exception:
        pass
    return d


class TikTokActor:
    def __init__(self, cookies_str: str):
        self.cookies_str = cookies_str
        self.driver = None
        self.login_ok = None

    def start(self):
        with _lock:
            self.driver = _driver()
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
        time.sleep(1.0)
        for c in _cookies(self.cookies_str):
            try:
                d.add_cookie(c)
            except Exception:
                pass
        d.get("https://www.tiktok.com/foryou")
        time.sleep(3.5 + random.random())

    def _refresh(self):
        try:
            self.driver.get("https://www.tiktok.com/foryou")
            time.sleep(3)
        except Exception:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = _driver()
            self._boot()

    def _api(self, path_with_query: str, body: str) -> dict:
        script = """
            const done = arguments[arguments.length-1];
            const path = arguments[0];
            const body = arguments[1];
            (async () => {
              try {
                let ware = '';
                try {
                  const h = await fetch(path.split('?')[0] + '?aid=1988', {
                    method: 'HEAD', credentials: 'include',
                    headers: {
                      'x-secsdk-csrf-request': '1',
                      'x-secsdk-csrf-version': '1.2.5'
                    }
                  });
                  ware = h.headers.get('x-ware-csrf-token') || h.headers.get('X-Ware-Csrf-Token') || '';
                  if (ware.includes(',')) ware = ware.split(',')[1] || ware.split(',')[0];
                } catch(e) {}
                const csrf = (document.cookie.split(';').map(s=>s.trim())
                  .find(s=>s.startsWith('tt_csrf_token='))||'=').split('=').slice(1).join('=');
                const headers = {
                  'Content-Type': 'application/x-www-form-urlencoded',
                  'x-tt-csrf-token': csrf
                };
                if (ware) headers['x-secsdk-csrf-token'] = ware.trim();
                const r = await fetch(path, {
                  method: 'POST', credentials: 'include', headers, body
                });
                const t = await r.text();
                done({status: r.status, body: (t||'').slice(0, 700)});
              } catch(e) {
                done({error: String(e)});
              }
            })();
        """
        return self.driver.execute_async_script(script, path_with_query, body)

    def _retry_api(self, path, body, tries=4):
        last = {}
        for i in range(tries):
            try:
                last = self._api(path, body)
                if last.get("error"):
                    self._refresh()
                    time.sleep(1.5)
                    continue
                ok, reason = _parse_ok(last.get("body", ""))
                if ok:
                    return last, True, reason
                if reason == "login_expired":
                    self.login_ok = False
                    return last, False, reason
                if reason in ("bad_csrf", "argus_block"):
                    self._refresh()
                time.sleep(1.2 + i * 0.6)
            except Exception as e:
                last = {"error": str(e)}
                self._refresh()
                time.sleep(1.5)
        ok, reason = _parse_ok(last.get("body", ""))
        return last, ok, reason

    def follow(self, user_id: str) -> dict:
        user_id = str(user_id).strip()
        if not user_id.isdigit():
            return {"ok": False, "action": "follow", "error": "bad_uid"}
        path = ("https://www.tiktok.com/api/commit/follow/user/"
                "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = "action_type=1&user_id=%s&channel_id=0&from=18" % user_id
        raw, ok, reason = self._retry_api(path, body, tries=4)
        return {"ok": ok, "action": "follow", "target": user_id, "reason": reason, "raw": raw}

    def like(self, aweme_id: str) -> dict:
        aweme_id = str(aweme_id).strip()
        path = ("https://www.tiktok.com/api/commit/item/digg/"
                "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = "aweme_id=%s&type=1&channel_id=0" % aweme_id
        raw, ok, reason = self._retry_api(path, body, tries=3)
        if ok:
            return {"ok": True, "action": "like", "target": aweme_id, "reason": reason, "raw": raw}
        if self._like_ui(aweme_id):
            return {"ok": True, "action": "like", "target": aweme_id, "reason": "ui_dblclick", "raw": raw}
        return {"ok": False, "action": "like", "target": aweme_id, "reason": reason, "raw": raw}

    def _like_ui(self, aweme_id: str) -> bool:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains
        try:
            self.driver.get("https://www.tiktok.com/foryou")
            time.sleep(3)
            vids = self.driver.find_elements(By.CSS_SELECTOR, "video")
            if vids:
                ActionChains(self.driver).move_to_element(vids[0]).pause(0.2).double_click().perform()
                time.sleep(1.5)
                return True
            self.driver.get("https://www.tiktok.com/@x/video/%s" % aweme_id)
            time.sleep(3)
            for sel in ["[data-e2e='like-icon']", "[data-e2e='browse-like-icon']", "video"]:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if not els:
                    continue
                try:
                    if sel == "video":
                        ActionChains(self.driver).move_to_element(els[0]).double_click().perform()
                    else:
                        els[0].click()
                    time.sleep(1.2)
                    return True
                except Exception:
                    continue
        except Exception:
            pass
        return False

    def comment(self, aweme_id: str, text: str = "nice") -> dict:
        aweme_id = str(aweme_id).strip()
        text = (text or "nice")[:150]
        path = ("https://www.tiktok.com/api/comment/publish/"
                "?aid=1988&app_name=tiktok_web&device_platform=web&channel=tiktok_web")
        body = "aweme_id=%s&text=%s&text_extra=%%5B%%5D&channel_id=0" % (aweme_id, quote(text))
        raw, ok, reason = self._retry_api(path, body, tries=3)
        if ok:
            return {"ok": True, "action": "comment", "target": aweme_id, "reason": reason, "raw": raw}
        if self._comment_ui(aweme_id, text):
            return {"ok": True, "action": "comment", "target": aweme_id, "reason": "ui", "raw": raw}
        return {"ok": False, "action": "comment", "target": aweme_id, "reason": reason, "raw": raw}

    def _comment_ui(self, aweme_id: str, text: str) -> bool:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        try:
            self.driver.get("https://www.tiktok.com/@x/video/%s" % aweme_id)
            time.sleep(3.5)
            for sel in ["[data-e2e='comment-icon']", "[data-e2e='browse-comment-icon']"]:
                els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                if els:
                    try:
                        els[0].click()
                        time.sleep(1.2)
                    except Exception:
                        pass
            for sel in ["div[contenteditable='true']", "textarea", "[data-e2e='comment-input']"]:
                boxes = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for box in boxes:
                    try:
                        box.click()
                        box.send_keys(text)
                        time.sleep(0.4)
                        box.send_keys(Keys.ENTER)
                        time.sleep(1.2)
                        return True
                    except Exception:
                        continue
        except Exception:
            pass
        return False


def get_actor_for_account(acc: dict) -> TikTokActor:
    m = _load()
    data = None
    for k in (acc.get("id"), acc.get("username"), acc.get("sessionid"), acc.get("user_field")):
        if k and str(k) in m:
            data = m[str(k)]
            break
    if not data or not data.get("cookies"):
        raise RuntimeError("Thiếu cookies cho %s — cập nhật tiktok_full.json" % acc.get("username"))
    return TikTokActor(data["cookies"]).start()


def do_task_action(actor: TikTokActor, job_key: str, task: dict) -> dict:
    if job_key in ("sub", "vip"):
        uid = str(task.get("uid") or "").strip()
        if not uid.isdigit():
            return {"ok": False, "action": "follow", "error": "missing_uid"}
        return actor.follow(uid)
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
                    text = str(arr[0])[:150]
            except Exception:
                text = str(nd)[:150]
        if not aweme:
            return {"ok": False, "action": "comment", "error": "no_aweme"}
        return actor.comment(aweme, text)
    return {"ok": False, "error": "unknown_job"}
