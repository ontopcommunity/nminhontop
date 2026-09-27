#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║          TUONGTACCHEO AUTO WORKER - Cloud Shell Edition       ║
║     Tự động login • Lưu PHPSESSID • Bypass Cloudflare         ║
║     Path đúng theo tài liệu chính thức                        ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import re
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

# ======================== CẤU HÌNH ========================
BASE_URL = "https://tuongtaccheo.com"
ACCESS_TOKEN = "cfb194b9dbd24ab7789b762e9e65d0ef"

SESSION_FILE = Path(__file__).parent / "phpsessid.txt"
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "").rstrip("/")

# ======================== MÀU SẮC ========================
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"

def banner():
    print(f"""{C.CYAN}{C.BOLD}
╔══════════════════════════════════════════════════════════════╗
║     ⚡  TUONGTACCHEO AUTO WORKER  ⚡                           ║
║     Login • Chọn Nick • Lấy Nhiệm Vụ • Claim                 ║
║     Tự động lưu PHPSESSID • Bypass Cloudflare                ║
╚══════════════════════════════════════════════════════════════╝{C.RESET}
""")

def log_ok(msg):   print(f"{C.GREEN}[✓]{C.RESET} {msg}")
def log_info(msg): print(f"{C.CYAN}[•]{C.RESET} {msg}")
def log_warn(msg): print(f"{C.YELLOW}[!]{C.RESET} {msg}")
def log_err(msg):  print(f"{C.RED}[✗]{C.RESET} {msg}")

# ======================== SESSION ========================
def load_session():
    if SESSION_FILE.exists():
        sid = SESSION_FILE.read_text().strip()
        if sid:
            log_ok(f"Đã load PHPSESSID từ file: {sid[:18]}...")
            return sid
    return None

def save_session(phpsessid: str):
    SESSION_FILE.write_text(phpsessid)
    log_ok(f"Đã lưu PHPSESSID → {SESSION_FILE}")

# ======================== REQUEST ENGINE ========================
def get_flare_endpoint():
    """Tránh bị /v1/v1"""
    if not FLARESOLVERR_URL:
        return None
    base = FLARESOLVERR_URL.rstrip("/")
    if base.endswith("/v1"):
        return base
    return base + "/v1"

def normal_request(method, path, params=None, cookies=None):
    url = BASE_URL + path
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BASE_URL + "/",
        "Origin": BASE_URL,
    }
    try:
        if method.upper() == "GET":
            r = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=30)
        else:
            r = requests.post(url, data=params, headers=headers, cookies=cookies, timeout=30)
        return r
    except Exception as e:
        log_err(f"Request lỗi: {e}")
        return None

def flare_request(method, path, params=None, cookies=None):
    endpoint = get_flare_endpoint()
    if not endpoint:
        return None

    url = BASE_URL + path
    if method.upper() == "GET" and params:
        url += ("&" if "?" in url else "?") + urlencode(params)

    payload = {
        "cmd": "request.get" if method.upper() == "GET" else "request.post",
        "url": url,
        "maxTimeout": 60000,
    }
    if method.upper() == "POST" and params:
        payload["postData"] = urlencode(params)

    if cookies:
        payload["cookies"] = [
            {"name": k, "value": v, "domain": "tuongtaccheo.com"}
            for k, v in cookies.items()
        ]

    try:
        r = requests.post(endpoint, json=payload, timeout=70)
        data = r.json()
        if data.get("status") != "ok":
            log_err(f"FlareSolverr: {data.get('message') or data}")
            return None

        sol = data.get("solution", {})

        class FakeResp:
            status_code = sol.get("status", 200)
            text = sol.get("response", "")
            def json(self_inner):
                return json.loads(self_inner.text)
        return FakeResp()
    except Exception as e:
        log_err(f"FlareSolverr lỗi: {e}")
        return None

def smart_request(method, path, params=None, cookies=None):
    if FLARESOLVERR_URL:
        log_info("Đi qua FlareSolverr (bypass CF)...")
        r = flare_request(method, path, params, cookies)
        if r and "Just a moment" not in (r.text or ""):
            return r
        log_warn("FlareSolverr thất bại hoặc vẫn bị CF → thử request thường")
    return normal_request(method, path, params, cookies)

# ======================== API FUNCTIONS ========================
def login(force=False):
    if not force:
        old = load_session()
        if old:
            return old

    log_info("Đang login lấy PHPSESSID mới...")
    r = normal_request("POST", "/logintoken.php", {"access_token": ACCESS_TOKEN})
    if not r:
        return None

    phpsessid = r.cookies.get("PHPSESSID")
    if not phpsessid:
        sc = r.headers.get("Set-Cookie", "")
        m = re.search(r"PHPSESSID=([^;,\s]+)", sc, re.I)
        if m:
            phpsessid = m.group(1)

    if phpsessid:
        save_session(phpsessid)
        try:
            data = r.json()
            if data.get("status") == "success":
                u = data.get("data", {})
                log_ok(f"Login thành công | User: {u.get('user')} | Số dư: {u.get('sodu')}")
        except:
            log_ok("Login thành công (có PHPSESSID)")
        return phpsessid
    else:
        log_err(f"Login thất bại. Status={r.status_code} Body={r.text[:200]}")
        return None

def chon_nick(phpsessid, nick="ontopmediamusic"):
    """Đặt / chọn nickchay theo tài liệu"""
    log_info(f"Đang chọn nick: {nick}...")
    cookies = {"PHPSESSID": phpsessid}

    # Các path có thể (theo tài liệu + thực tế)
    paths = [
        "/tiktok/kiemtien/chon_nick.php",
        "/tiktok/kiemtien/datnick.php",
        "/chon_nick.php",
        "/api/chon_nick.php",
    ]

    for path in paths:
        # Thử cả GET và POST
        for method in ["GET", "POST"]:
            params = {"nickchay": nick, "id": nick, "username": nick, "loai": "1"}
            r = smart_request(method, path, params, cookies)
            if not r:
                continue
            if "Just a moment" in r.text or "cf-browser-verification" in r.text:
                log_warn(f"{method} {path} → Cloudflare")
                continue
            if r.status_code == 200:
                try:
                    data = r.json()
                    log_ok(f"Chọn nick thành công via {method} {path}")
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
                    return data
                except:
                    if len(r.text) < 500 and ("success" in r.text.lower() or "ok" in r.text.lower() or "thành công" in r.text.lower()):
                        log_ok(f"Chọn nick OK via {method} {path}")
                        print(r.text[:300])
                        return {"raw": r.text[:300]}
                    log_info(f"{method} {path} → {r.text[:150]}")
    log_err("Không chọn được nick")
    return None

def lay_nhiem_vu(phpsessid, nickchay="ontopmediamusic"):
    """
    Lấy nhiệm vụ - Path đúng theo tài liệu:
    https://tuongtaccheo.com/tiktok/kiemtien/getpost.php?nickchay=...
    """
    log_info(f"Đang lấy nhiệm vụ nickchay={nickchay}...")
    cookies = {"PHPSESSID": phpsessid}

    # Path chính theo tài liệu ảnh
    paths = [
        "/tiktok/kiemtien/getpost.php",
        "/tiktok/getpost.php",
        "/getpost.php",
        "/api/getpost.php",
    ]

    for path in paths:
        r = smart_request("GET", path, {"nickchay": nickchay}, cookies)
        if not r:
            continue
        if "Just a moment" in r.text or "cf-browser-verification" in r.text:
            log_warn(f"{path} → Cloudflare")
            continue
        if r.status_code == 200:
            try:
                data = r.json()
                log_ok(f"Lấy nhiệm vụ thành công via {path}")
                if isinstance(data, list):
                    print(f"{C.MAGENTA}→ Có {len(data)} nhiệm vụ{C.RESET}")
                    for i, t in enumerate(data[:8], 1):
                        print(f"  {i}. ID={t.get('id')} | {str(t.get('link', t.get('url', '')))[:70]}")
                    if len(data) > 8:
                        print(f"  ... và {len(data)-8} nhiệm vụ nữa")
                else:
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:700])
                return data
            except:
                log_info(f"{path}: {r.text[:300]}")
                if r.text.strip().startswith("[") or r.text.strip().startswith("{"):
                    print(r.text[:400])
    log_err("Không lấy được nhiệm vụ")
    return None

def claim(phpsessid, ids, nickchay="ontopmediamusic"):
    """
    Nhận xu / claim - theo tài liệu:
    thêm trường nickchay vào body
    ví dụ: id=123,345,456&nickchay=67462381249
    """
    if isinstance(ids, list):
        ids = ",".join(str(x) for x in ids)
    log_info(f"Đang claim id={ids} nickchay={nickchay}...")
    cookies = {"PHPSESSID": phpsessid}

    paths = [
        "/tiktok/kiemtien/nhantien.php",
        "/tiktok/kiemtien/claim.php",
        "/nhantien.php",
        "/api/nhantien.php",
    ]
    params = {"id": ids, "nickchay": nickchay}

    for path in paths:
        r = smart_request("POST", path, params, cookies)
        if not r:
            continue
        if "Just a moment" in r.text:
            continue
        try:
            data = r.json()
            log_ok(f"Claim thành công via {path}")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
            return data
        except:
            log_info(f"{path}: {r.text[:250]}")
    log_err("Claim thất bại")
    return None

# ======================== MENU ========================
def menu():
    print(f"""
{C.BOLD}┌─────────── MENU ───────────┐
│  1. Login / Làm mới session │
│  2. Chọn nick (ontopmediamusic) │
│  3. Lấy nhiệm vụ            │
│  4. Chạy full auto (1→2→3)  │
│  5. Xem PHPSESSID hiện tại  │
│  0. Thoát                   │
└─────────────────────────────┘{C.RESET}
""")

def main():
    banner()
    print(f"{C.GRAY}Session file : {SESSION_FILE}{C.RESET}")
    flare_ep = get_flare_endpoint()
    print(f"{C.GRAY}FlareSolverr : {flare_ep or 'Chưa cấu hình'}{C.RESET}")
    print()

    phpsessid = load_session()

    while True:
        menu()
        choice = input(f"{C.YELLOW}Chọn chức năng › {C.RESET}").strip()

        if choice == "0":
            log_info("Bye!")
            break
        elif choice == "1":
            phpsessid = login(force=True)
        elif choice == "2":
            if not phpsessid:
                phpsessid = login()
            if phpsessid:
                chon_nick(phpsessid)
        elif choice == "3":
            if not phpsessid:
                phpsessid = login()
            if phpsessid:
                lay_nhiem_vu(phpsessid)
        elif choice == "4":
            log_info(f"{datetime.now().strftime('%H:%M:%S')} Bắt đầu full auto...")
            phpsessid = login(force=False) or login(force=True)
            if not phpsessid:
                log_err("Không login được → dừng")
                continue
            chon_nick(phpsessid)
            time.sleep(1.2)
            tasks = lay_nhiem_vu(phpsessid)
            if tasks and isinstance(tasks, list) and len(tasks) > 0:
                log_ok(f"Full auto xong – có {len(tasks)} nhiệm vụ")
            else:
                log_warn("Không có nhiệm vụ")
        elif choice == "5":
            print(f"PHPSESSID = {phpsessid or 'Chưa có'}")
            if SESSION_FILE.exists():
                print(f"File     = {SESSION_FILE.read_text().strip()}")
        else:
            log_warn("Lựa chọn không hợp lệ")
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{C.YELLOW}Đã dừng bởi người dùng.{C.RESET}")
