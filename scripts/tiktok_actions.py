#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONTOP TikTok Actor – tham khảo mysterecode/TikTok-Bot-Automation
- SeleniumBase UC (undetected) ưu tiên
- Login bằng cookie session
- Follow / Like / Comment qua UI (data-e2e) thay vì API headless dễ bị chặn
"""
from __future__ import annotations
import os, re, json, time, random, threading
from pathlib import Path
from urllib.parse import quote

SCRIPT_DIR = Path(__file__).parent
FULL_JSON = SCRIPT_DIR / "tiktok_full.json"

_map = None
_map_lock = threading.Lock()
PROXY_URL = ""  # tương thích farm cũ


def _load():
    global _map
    with _map_lock:
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


def _cookie_dicts(cookies_str: str):
    """Chuỗi cookie 'a=b; c=d' → list dict Selenium."""
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


def _make_driver(headless: bool = True):
    """Ưu tiên SeleniumBase UC (repo mysterecode), fallback selenium thường."""
    try:
        from seleniumbase import Driver
        # uc=True ≈ undetected-chromedriver
        drv = Driver(uc=True, headless=headless)
        try:
            drv.set_window_size(1280, 900)
        except Exception:
            pass
        return drv, "seleniumbase-uc"
    except Exception as e1:
        print("  [tt] seleniumbase fail:", str(e1)[:80])
    try:
        import undetected_chromedriver as uc
        opts = uc.ChromeOptions()
        if headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--window-size=1280,900")
        drv = uc.Chrome(options=opts)
        return drv, "uc"
    except Exception as e2:
        print("  [tt] uc fail:", str(e2)[:80])
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1280,900")
    drv = webdriver.Chrome(options=opts)
    return drv, "selenium"


class TikTokActor:
    def __init__(self, cookies_str: str):
        self.cookies_str = cookies_str
        self.driver = None
        self.engine = ""

    def start(self):
        headless = os.getenv("TT_HEADLESS", "1") != "0"
        self.driver, self.engine = _make_driver(headless=headless)
        d = self.driver
        d.get("https://www.tiktok.com/")
        time.sleep(2 + random.random())
        for c in _cookie_dicts(self.cookies_str):
            try:
                d.add_cookie(c)
            except Exception:
                pass
        d.get("https://www.tiktok.com/foryou")
        time.sleep(2 + random.random())
        print("  [tt] engine=%s cookies=%d" % (self.engine, len(_cookie_dicts(self.cookies_str))))
        return self

    def close(self):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        self.driver = None

    def _wait_css(self, css: str, timeout: float = 12):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css))
        )

    def _wait_xpath(self, xp: str, timeout: float = 12):
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, xp))
        )

    def _click_xpath(self, xp: str, timeout: float = 10) -> bool:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        try:
            el = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            try:
                el.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", el)
            return True
        except Exception:
            return False

    def follow(self, user_id: str, username: str = "") -> dict:
        """
        Theo mysterecode: mở @user → click //button[@data-e2e="follow-button"]
        """
        username = (username or "").strip().lstrip("@")
        user_id = str(user_id or "").strip()
        if not username and not user_id.isdigit():
            return {"ok": False, "action": "follow", "reason": "missing_target"}

        target = username or user_id
        url = "https://www.tiktok.com/@%s" % target if username else "https://www.tiktok.com/"
        try:
            self.driver.get(url)
            time.sleep(2.5 + random.random())
        except Exception as e:
            return {"ok": False, "action": "follow", "reason": "nav:" + str(e)[:40]}

        # Đã follow?
        try:
            from selenium.webdriver.common.by import By
            btns = self.driver.find_elements(By.XPATH, '//button[@data-e2e="follow-button"]')
            for b in btns[:3]:
                txt = (b.text or "").strip().lower()
                if any(x in txt for x in ("following", "requested", "đang follow", "đã follow", "friends")):
                    return {"ok": True, "action": "follow", "reason": "already", "ui": True, "engine": self.engine}
        except Exception:
            pass

        # Click follow – selectors từ repo + fallback
        xpaths = [
            '//button[@data-e2e="follow-button"]',
            '//button[@data-e2e="follow-button" and contains(., "Follow")]',
            '//button[@data-e2e="follow-button" and contains(., "Theo dõi")]',
            '//button[contains(@class,"follow") and contains(., "Follow")]',
        ]
        clicked = False
        for xp in xpaths:
            if self._click_xpath(xp, timeout=8):
                clicked = True
                time.sleep(1.5 + random.random())
                break

        if not clicked:
            return {"ok": False, "action": "follow", "reason": "no_follow_btn", "ui": False, "engine": self.engine}

        # Verify text sau click
        try:
            from selenium.webdriver.common.by import By
            btns = self.driver.find_elements(By.XPATH, '//button[@data-e2e="follow-button"]')
            for b in btns[:3]:
                txt = (b.text or "").strip().lower()
                if any(x in txt for x in ("following", "requested", "đang follow", "đã follow", "friends")):
                    return {"ok": True, "action": "follow", "reason": "ui_following", "ui": True, "engine": self.engine}
        except Exception:
            pass

        return {"ok": True, "action": "follow", "reason": "ui_clicked", "ui": True, "engine": self.engine}

    def like(self, aweme_id: str) -> dict:
        aweme_id = str(aweme_id).strip()
        if not aweme_id:
            return {"ok": False, "action": "like", "reason": "no_aweme"}
        try:
            self.driver.get("https://www.tiktok.com/@x/video/%s" % aweme_id)
            time.sleep(2.5 + random.random())
        except Exception as e:
            return {"ok": False, "action": "like", "reason": str(e)[:40]}

        # data-e2e like
        for xp in (
            '//*[@data-e2e="like-icon"]',
            '//*[@data-e2e="browse-like-icon"]',
            '//button[@data-e2e="like-button"]',
            '//span[@data-e2e="like-icon"]',
        ):
            if self._click_xpath(xp, timeout=6):
                time.sleep(1)
                return {"ok": True, "action": "like", "reason": "ui", "engine": self.engine}

        # double-click video
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.action_chains import ActionChains
            vid = self.driver.find_element(By.TAG_NAME, "video")
            ActionChains(self.driver).double_click(vid).perform()
            time.sleep(1)
            return {"ok": True, "action": "like", "reason": "dblclick", "engine": self.engine}
        except Exception:
            pass
        return {"ok": False, "action": "like", "reason": "no_like_btn", "engine": self.engine}

    def comment(self, aweme_id: str, text: str = "nice") -> dict:
        """Theo repo: //div[@role="textbox"] + gõ từng ký tự."""
        aweme_id = str(aweme_id).strip()
        text = (text or "nice")[:100]
        if not aweme_id:
            return {"ok": False, "action": "comment", "reason": "no_aweme"}
        try:
            self.driver.get("https://www.tiktok.com/@x/video/%s" % aweme_id)
            time.sleep(2.5 + random.random())
        except Exception as e:
            return {"ok": False, "action": "comment", "reason": str(e)[:40]}

        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            box = WebDriverWait(self.driver, 12).until(
                EC.presence_of_element_located((By.XPATH, '//div[@role="textbox"]'))
            )
            box.click()
            time.sleep(0.3)
            for ch in text:
                box.send_keys(ch)
                time.sleep(0.04 + random.random() * 0.03)
            box.send_keys(Keys.ENTER)
            time.sleep(1.2)
            # nút post nếu có
            self._click_xpath('//div[@data-e2e="comment-post"]', timeout=3)
            return {"ok": True, "action": "comment", "reason": "ui", "engine": self.engine}
        except Exception as e:
            return {"ok": False, "action": "comment", "reason": str(e)[:50], "engine": self.engine}


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
            return {"ok": False, "error": "missing_uid"}
        return actor.follow(uid or "0", uname)

    if job_key == "tim":
        aweme = str(task.get("idpost") or "")
        if not aweme.isdigit():
            m = re.search(r"/video/(\d+)", str(task.get("link") or ""))
            aweme = m.group(1) if m else ""
        if not aweme:
            return {"ok": False, "error": "no_aweme"}
        return actor.like(aweme)

    if job_key == "cmt":
        aweme = str(task.get("idpost") or "")
        if not aweme.isdigit():
            m = re.search(r"/video/(\d+)", str(task.get("link") or ""))
            aweme = m.group(1) if m else ""
        text = "nice"
        nd = task.get("nd")
        if nd:
            try:
                arr = json.loads(nd) if isinstance(nd, str) else nd
                if isinstance(arr, list) and arr:
                    text = str(arr[0])[:100]
            except Exception:
                text = str(nd)[:100]
        if not aweme:
            return {"ok": False, "error": "no_aweme"}
        return actor.comment(aweme, text)

    return {"ok": False, "error": "unknown_job"}
