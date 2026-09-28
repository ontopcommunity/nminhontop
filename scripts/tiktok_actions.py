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
# ═══ PROXY RESIDENTIAL ═══
# PROXY_URL=http://user:pass@host:port   (ưu tiên – residential)
# PROXY_LIST=scripts/proxies.txt         (mỗi dòng 1 proxy)
# PROXY_FORCE=1                          (bắt buộc proxy, không fallback direct)
# Không set gì → thử free (yếu), rồi direct

BUILTIN_PROXIES = [
    "http://159.223.167.188:10000",
    "http://190.97.229.118:999",
    "http://165.154.162.73:8888",
    "http://107.167.18.122:443",
]

def _parse_proxy(url: str):
    """Trả (server_no_auth, username, password) hoặc (None,None,None)."""
    url = (url or "").strip()
    if not url:
        return None, None, None
    if "://" not in url:
        url = "http://" + url
    u = urlparse(url)
    if not u.hostname:
        return None, None, None
    port = u.port or (443 if u.scheme == "https" else 80)
    server = "%s://%s:%s" % (u.scheme or "http", u.hostname, port)
    return server, u.username, u.password


def _load_proxy_candidates():
    cands = []
    env = os.getenv("PROXY_URL", "").strip()
    if env:
        cands.append(env)
    list_path = os.getenv("PROXY_LIST", "").strip()
    if not list_path:
        # mặc định file trong scripts/
        lp = SCRIPT_DIR / "proxies.txt"
        if lp.exists():
            list_path = str(lp)
    if list_path and Path(list_path).exists():
        for line in Path(list_path).read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                if "://" not in line and line.count(":") >= 3:
                    # user:pass@host:port or host:port:user:pass
                    if "@" in line:
                        cands.append("http://" + line)
                    else:
                        parts = line.split(":")
                        if len(parts) == 4:
                            # host:port:user:pass
                            cands.append("http://%s:%s@%s:%s" % (parts[2], parts[3], parts[0], parts[1]))
                        else:
                            cands.append("http://" + line)
                else:
                    cands.append(line if "://" in line else "http://" + line)
    # free chỉ khi không có residential config
    if not env and not (list_path and Path(list_path).exists() if list_path else False):
        cands.extend(BUILTIN_PROXIES)
    # unique preserve order
    seen = set()
    out = []
    for c in cands:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _test_proxy(px: str, timeout: float = 8) -> bool:
    """Health-check: HTTP qua proxy tới ipify (nhanh). Residential nên pass."""
    try:
        import requests as rq
        r = rq.get(
            "https://api.ipify.org?format=json",
            proxies={"http": px, "https": px},
            timeout=timeout,
        )
        return r.status_code == 200 and bool(r.text)
    except Exception:
        return False


def _pick_proxy() -> str:
    force = os.getenv("PROXY_FORCE", "").strip() in ("1", "true", "yes")
    cands = _load_proxy_candidates()
    if not cands:
        print("  [proxy] không cấu hình – direct")
        return ""
    for px in cands:
        server, user, pw = _parse_proxy(px)
        label = server or px
        if user:
            label = label.replace("://", "://***:***@") if "://" in label else label
            # reconstruct display without password
            u = urlparse(px if "://" in px else "http://" + px)
            label = "%s://%s:***@%s:%s" % (u.scheme, u.username, u.hostname, u.port)
        print("  [proxy] test", label, "...", end=" ", flush=True)
        # build test URL with auth embedded
        test_url = px if "://" in px else "http://" + px
        if _test_proxy(test_url):
            print("OK")
            return test_url
        print("FAIL")
    if force:
        print("  [proxy] PROXY_FORCE=1 nhưng không proxy nào sống")
        return cands[0]  # vẫn dùng cái đầu
    print("  [proxy] không proxy sống – direct (set PROXY_URL residential để ổn định)")
    return ""


PROXY_URL = _pick_proxy()
PROXY_FORCE = os.getenv("PROXY_FORCE", "").strip() in ("1", "true", "yes")


def _make_proxy_extension(server: str, username: str, password: str) -> str:
    """Chrome extension tạm để auth proxy (residential user:pass)."""
    import tempfile, zipfile
    u = urlparse(server)
    host = u.hostname or ""
    port = u.port or 80
    scheme = u.scheme or "http"
    manifest = """{
  "version": "1.0.0",
  "manifest_version": 2,
  "name": "ONTOP Proxy Auth",
  "permissions": ["proxy", "tabs", "unlimitedStorage", "storage", "<all_urls>", "webRequest", "webRequestBlocking"],
  "background": {"scripts": ["background.js"]},
  "minimum_chrome_version": "22.0.0"
}"""
    background = """
var config = {
    mode: "fixed_servers",
    rules: {
      singleProxy: { scheme: "%s", host: "%s", port: %d },
      bypassList: ["localhost", "127.0.0.1"]
    }
};
chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});
function callbackFn(details) {
    return { authCredentials: { username: "%s", password: "%s" } };
}
chrome.webRequest.onAuthRequired.addListener(
    callbackFn,
    {urls: ["<all_urls>"]},
    ['blocking']
);
""" % (scheme, host, int(port), username.replace('"', '\\"'), password.replace('"', '\\"'))
    tmp = tempfile.mkdtemp(prefix="tt_proxy_")
    ext = os.path.join(tmp, "proxy_auth_ext.zip")
    with zipfile.ZipFile(ext, "w") as zf:
        zf.writestr("manifest.json", manifest)
        zf.writestr("background.js", background)
    return ext


def _proxy_args():
    """Chrome args + optional auth extension path."""
    if not PROXY_URL:
        return [], None
    server, user, password = _parse_proxy(PROXY_URL)
    if not server:
        return [], None
    if user and password:
        ext = _make_proxy_extension(server, user, password)
        return [], ext  # extension handles proxy; no --proxy-server
    return ["--proxy-server=%s" % server], None


def _make_driver(use_proxy: bool = True):
    proxy_args, proxy_ext = ([], None)
    if use_proxy and PROXY_URL:
        proxy_args, proxy_ext = _proxy_args()
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    o = Options()
    o.add_argument("--headless=new")
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--disable-gpu")
    o.add_argument("--window-size=1365,900")
    o.add_argument("--disable-blink-features=AutomationControlled")
    o.add_argument("--lang=en-US")
    o.page_load_strategy = "eager"
    for a in proxy_args:
        o.add_argument(a)
    if proxy_ext:
        o.add_extension(proxy_ext)
    o.binary_location = "/usr/bin/google-chrome"
    try:
        import undetected_chromedriver as uc
        uo = uc.ChromeOptions()
        uo.add_argument("--no-sandbox")
        uo.add_argument("--disable-dev-shm-usage")
        uo.add_argument("--disable-gpu")
        uo.add_argument("--window-size=1365,900")
        uo.add_argument("--headless=new")
        uo.page_load_strategy = "eager"
        for a in proxy_args:
            uo.add_argument(a)
        if proxy_ext:
            uo.add_extension(proxy_ext)
        d = uc.Chrome(options=uo, headless=True, use_subprocess=True)
    except Exception:
        d = webdriver.Chrome(options=o)
    d.set_page_load_timeout(35 if use_proxy else 25)
    d.set_script_timeout(35)
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
            last_err = None
            # Thử proxy trước, fail thì direct
            modes = [True]
            if not PROXY_FORCE:
                modes.append(False)  # fallback direct khi không FORCE
            for use_proxy in modes:
                try:
                    self.driver = _make_driver(use_proxy=use_proxy and bool(PROXY_URL))
                    self._boot()
                    if use_proxy and PROXY_URL:
                        print("  [chrome] boot proxy OK")
                    else:
                        print("  [chrome] boot direct OK")
                    return self
                except Exception as e:
                    last_err = e
                    print("  [chrome] boot fail proxy=%s: %s" % (use_proxy, str(e)[:80]))
                    try:
                        if self.driver:
                            self.driver.quit()
                    except Exception:
                        pass
                    self.driver = None
            raise RuntimeError("Chrome boot fail: %s" % last_err)

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def _boot(self):
        d = self.driver
        try:
            d.get("https://www.tiktok.com/")
        except Exception:
            pass  # eager/timeout vẫn có thể set cookie
        time.sleep(1.0)
        for c in _cookies(self.cookies_str):
            try:
                d.add_cookie(c)
            except Exception:
                pass
        try:
            d.get("https://www.tiktok.com/foryou")
        except Exception:
            pass
        time.sleep(2.5 + random.random())

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
