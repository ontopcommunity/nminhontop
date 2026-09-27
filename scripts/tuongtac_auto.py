#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║          TUONGTACCHEO AUTO WORKER - Cloud Shell Edition       ║
║     Tự động login • Lưu PHPSESSID • Bypass Cloudflare         ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import requests
from datetime import datetime
from pathlib import Path

# ======================== CẤU HÌNH ========================
BASE_URL = "https://tuongtaccheo.com"
ACCESS_TOKEN = "cfb194b9dbd24ab7789b762e9e65d0ef"
API_KEY = "8hu0eh0f4ijo7tpk8qh3vgdnq8aibcsk"          # vẫn giữ nếu sau này cần

# File lưu session (tự nhớ mỗi lần chạy)
SESSION_FILE = Path(__file__).parent / "phpsessid.txt"
FLARESOLVERR_URL = os.getenv("FLARESOLVERR_URL", "").rstrip("/")  # để trống nếu chưa có

# ======================== MÀU SẮC ========================
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
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
def log_time():    return datetime.now().strftime("%H:%M:%S")

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
    """Gửi request qua FlareSolverr để bypass Cloudflare"""
    if not FLARESOLVERR_URL:
        return None

    url = BASE_URL + path
    if method.upper() == "GET" and params:
        from urllib.parse import urlencode
        url += ("&" if "?" in url else "?") + urlencode(params)

    payload = {
        "cmd": "request.get" if method.upper() == "GET" else "request.post",
        "url": url,
        "maxTimeout": 60000,
    }
    if method.upper() == "POST" and params:
        from urllib.parse import urlencode
        payload["postData"] = urlencode(params)

    if cookies:
        payload["cookies"] = [
            {"name": k, "value": v, "domain": "tuongtaccheo.com"}
            for k, v in cookies.items()
        ]

    try:
        r = requests.post(FLARESOLVERR_URL + "/v1", json=payload, timeout=70)
        data = r.json()
        if data.get("status") != "ok":
            log_err(f"FlareSolverr: {data.get('message', data)}")
            return None
        sol = data.get("solution", {})
        # Giả lập response object
        class FakeResp:
            status_code = sol.get("status", 200)
            text = sol.get("response", "")
            def json(self):
                return json.loads(self.text)
        return FakeResp()
    except Exception as e:
        log_err(f"FlareSolverr lỗi: {e}")
        return None

def smart_request(method, path, params=None, cookies=None):
    """Tự động chọn FlareSolverr nếu có, không thì request thường"""
    if FLARESOLVERR_URL:
        log_info("Đi qua FlareSolverr (bypass CF)...")
        r = flare_request(method, path, params, cookies)
        if r:
            return r
        log_warn("FlareSolverr thất bại → thử request thường")
    return normal_request(method, path, params, cookies)

# ======================== API FUNCTIONS ========================
def login(force=False):
    """Login lấy PHPSESSID, tự lưu file"""
    if not force:
        old = load_session()
        if old:
            return old

    log_info("Đang login lấy PHPSESSID mới...")
    r = normal_request("POST", "/logintoken.php", {"access_token": ACCESS_TOKEN})
    if not r:
        return None

    # Lấy từ cookie
    phpsessid = r.cookies.get("PHPSESSID")
    if not phpsessid:
        # Thử parse header
        sc = r.headers.get("Set-Cookie", "")
        import re
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

def chon_nick(phpsessid, loai="1", nick="ontopmediamusic"):
    """Chọn / thêm nickchay"""
    log_info(f"Đang chọn nick: {nick} (loai={loai})...")
    cookies = {"PHPSESSID": phpsessid}
    paths = ["/chon_nick.php", "/api/chon_nick.php", "/api/profile-setup.php", "/profile-setup.php"]

    for path in paths:
        r = smart_request("GET", path, {"loai": loai, "id": nick, "nickchay": nick}, cookies)
        if not r:
            continue
        if "Just a moment" in r.text or "cf-browser-verification" in r.text:
            log_warn(f"{path} → vẫn bị Cloudflare")
            continue
        if r.status_code == 200:
            try:
                data = r.json()
                log_ok(f"Chọn nick thành công via {path}")
                print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
                return data
            except:
                log_info(f"{path} trả về: {r.text[:200]}")
                if "success" in r.text.lower() or "ok" in r.text.lower():
                    return {"raw": r.text[:300]}
    log_err("Không chọn được nick (tất cả path đều fail hoặc bị CF)")
    return None

def lay_nhiem_vu(phpsessid, type_="like", nickchay="ontopmediamusic", env_code="1"):
    """Lấy danh sách nhiệm vụ"""
    log_info(f"Đang lấy nhiệm vụ type={type_} nick={nickchay}...")
    cookies = {"PHPSESSID": phpsessid}
    paths = [
        f"/api/{env_code}/fetch-tasks.php",
        "/getpost.php",
        "/api/getpost.php",
        "/api/fetch-tasks.php",
    ]

    for path in paths:
        r = smart_request("GET", path, {"type": type_, "nickchay": nickchay}, cookies)
        if not r:
            continue
        if "Just a moment" in r.text:
            log_warn(f"{path} → Cloudflare")
            continue
        if r.status_code == 200:
            try:
                data = r.json()
                log_ok(f"Lấy nhiệm vụ thành công via {path}")
                if isinstance(data, list):
                    print(f"{C.MAGENTA}→ Có {len(data)} nhiệm vụ{C.RESET}")
                    for i, t in enumerate(data[:5], 1):
                        print(f"  {i}. ID={t.get('id')} | {t.get('link', '')[:60]}")
                    if len(data) > 5:
                        print(f"  ... và {len(data)-5} nhiệm vụ nữa")
                else:
                    print(json.dumps(data, ensure_ascii=False, indent=2)[:600])
                return data
            except:
                log_info(f"{path}: {r.text[:250]}")
    log_err("Không lấy được nhiệm vụ")
    return None

def claim(phpsessid, ids, type_="like", nickchay="ontopmediamusic", env_code="1"):
    """Báo cáo hoàn thành"""
    if isinstance(ids, list):
        ids = ",".join(str(x) for x in ids)
    log_info(f"Đang claim: {ids}")
    cookies = {"PHPSESSID": phpsessid}
    paths = [
        f"/api/{env_code}/report-completion.php",
        "/nhantien.php",
        "/api/nhantien.php",
    ]
    params = {"id": ids, "type": type_, "nickchay": nickchay}

    for path in paths:
        r = smart_request("POST", path, params, cookies)
        if not r:
            continue
        if "Just a moment" in r.text:
            continue
        try:
            data = r.json()
            log_ok(f"Claim thành công via {path}")
            print(json.dumps(data, ensure_ascii=False, indent=2)[:400])
            return data
        except:
            log_info(f"{path}: {r.text[:200]}")
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
    print(f"{C.GRAY}FlareSolverr : {FLARESOLVERR_URL or 'Chưa cấu hình (sẽ bị CF chặn task)'}{C.RESET}")
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
            log_info(f"{log_time()} Bắt đầu full auto...")
            phpsessid = login(force=False) or login(force=True)
            if not phpsessid:
                log_err("Không login được → dừng")
                continue
            chon_nick(phpsessid)
            time.sleep(1.5)
            tasks = lay_nhiem_vu(phpsessid)
            if tasks and isinstance(tasks, list) and len(tasks) > 0:
                # Tự claim thử nhiệm vụ đầu tiên (chỉ demo)
                # claim(phpsessid, tasks[0]["id"])
                log_ok("Full auto xong (chưa tự claim để tránh rủi ro)")
            else:
                log_warn("Không có nhiệm vụ để claim")

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
