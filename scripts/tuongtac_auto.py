#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║              ████████╗████████╗ ██████╗                              ║
║              ╚══██╔══╝╚══██╔══╝██╔════╝                              ║
║                 ██║      ██║   ██║                                   ║
║                 ██║      ██║   ██║                                   ║
║                 ██║      ██║   ╚██████╗                              ║
║                 ╚═╝      ╚═╝    ╚═════╝                              ║
║                                                                      ║
║         TUONGTACCHEO AUTO WORKER  •  Cloud Shell Edition             ║
║         TikTok Job Engine  •  Auto Session  •  Smart Delay           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import re
import random
import requests
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

# ═══════════════════════════════════════════════════════════════
#  CẤU HÌNH
# ═══════════════════════════════════════════════════════════════
BASE_URL       = "https://tuongtaccheo.com"
ACCESS_TOKEN   = "cfb194b9dbd24ab7789b762e9e65d0ef"
DEFAULT_NICK   = "ontopmediamusic"

SESSION_FILE   = Path(__file__).parent / "phpsessid.txt"
NICKS_FILE     = Path(__file__).parent / "nicks.txt"
CONFIG_FILE    = Path(__file__).parent / "config.json"
FLARESOLVERR   = os.getenv("FLARESOLVERR_URL", "").rstrip("/")

# Delay giữa các request (giây) – tránh spam
DELAY_BETWEEN  = 5
# Delay mặc định khi API trả countdown
DEFAULT_WAIT   = 60

# Các loại nhiệm vụ (path đã test OK)
JOB_TYPES = {
    "1": {"name": "Sub Chéo",      "path": "subcheo"},
    "2": {"name": "Sub VIP",       "path": "subcheovip"},
    "3": {"name": "Tim (Like)",    "path": "timcheo"},
    "4": {"name": "Comment",       "path": "cmtcheo"},
    "5": {"name": "Tổng hợp",      "path": ""},  # getpost chung
}

# ═══════════════════════════════════════════════════════════════
#  MÀU SẮC & GIAO DIỆN
# ═══════════════════════════════════════════════════════════════
class UI:
    R  = "\033[0m"
    B  = "\033[1m"
    D  = "\033[2m"
    G  = "\033[92m"
    Y  = "\033[93m"
    E  = "\033[91m"
    C  = "\033[96m"
    M  = "\033[95m"
    W  = "\033[97m"
    K  = "\033[90m"
    BG = "\033[48;5;236m"

    @staticmethod
    def clear():
        os.system("clear" if os.name != "nt" else "cls")

    @staticmethod
    def line(char="─", n=62):
        return f"{UI.K}{char * n}{UI.R}"

    @staticmethod
    def box_top(title=""):
        t = f" {title} " if title else ""
        pad = 60 - len(title)
        left = pad // 2
        right = pad - left
        print(f"{UI.C}{UI.B}╭{'─'*left}{t}{'─'*right}╮{UI.R}")

    @staticmethod
    def box_mid(text, color=None):
        c = color or UI.W
        print(f"{UI.C}│{UI.R} {c}{text:<58}{UI.R} {UI.C}│{UI.R}")

    @staticmethod
    def box_bot():
        print(f"{UI.C}╰{'─'*60}╯{UI.R}")

    @staticmethod
    def ok(msg):   print(f"  {UI.G}✔{UI.R}  {msg}")
    @staticmethod
    def info(msg): print(f"  {UI.C}●{UI.R}  {msg}")
    @staticmethod
    def warn(msg): print(f"  {UI.Y}▲{UI.R}  {msg}")
    @staticmethod
    def err(msg):  print(f"  {UI.E}✘{UI.R}  {msg}")
    @staticmethod
    def wait(msg): print(f"  {UI.M}⏳{UI.R}  {msg}")

def banner():
    UI.clear()
    print(f"""{UI.C}{UI.B}
  ╔════════════════════════════════════════════════════════════╗
  ║                                                            ║
  ║          T U O N G T A C C H E O   W O R K E R             ║
  ║                                                            ║
  ║     TikTok Auto Job  •  Smart Session  •  Rate-Limit       ║
  ║                                                            ║
  ╚════════════════════════════════════════════════════════════╝{UI.R}
""")
    print(f"  {UI.K}Session : {SESSION_FILE}{UI.R}")
    flare = FLARESOLVERR or "Không dùng"
    print(f"  {UI.K}Flare   : {flare}{UI.R}")
    print(f"  {UI.K}Nick    : {DEFAULT_NICK}{UI.R}")
    print()

# ═══════════════════════════════════════════════════════════════
#  SESSION
# ═══════════════════════════════════════════════════════════════
def load_session():
    if SESSION_FILE.exists():
        sid = SESSION_FILE.read_text().strip()
        if sid:
            return sid
    return None

def save_session(sid: str):
    SESSION_FILE.write_text(sid)
    UI.ok(f"Đã lưu PHPSESSID → {SESSION_FILE.name}")

def load_config():
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text())
        except:
            pass
    return {}

def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))

# ═══════════════════════════════════════════════════════════════
#  REQUEST ENGINE
# ═══════════════════════════════════════════════════════════════
def _flare_endpoint():
    if not FLARESOLVERR:
        return None
    base = FLARESOLVERR.rstrip("/")
    return base if base.endswith("/v1") else base + "/v1"

def _request(method, path, params=None, cookies=None, use_token=False):
    """use_token=True chỉ dùng cho login. Job API bắt buộc Cookie PHPSESSID."""
    url = BASE_URL + path
    params = dict(params or {})
    # Chỉ gắn access_token khi được yêu cầu (login)
    if use_token and ACCESS_TOKEN and "access_token" not in params:
        params["access_token"] = ACCESS_TOKEN

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": BASE_URL + "/",
        "Origin": BASE_URL,
    }
    # Bắt buộc có cookie khi gọi job API
    if not use_token and (not cookies or not cookies.get("PHPSESSID")):
        UI.err("Thiếu PHPSESSID cookie – phải login trước")
        return None

    # Thử FlareSolverr trước
    ep = _flare_endpoint()
    if ep:
        try:
            full = url
            if method == "GET" and params:
                full += ("&" if "?" in full else "?") + urlencode(params)
            payload = {
                "cmd": "request.get" if method == "GET" else "request.post",
                "url": full,
                "maxTimeout": 60000,
            }
            if method == "POST" and params:
                payload["postData"] = urlencode(params)
            if cookies:
                payload["cookies"] = [{"name": k, "value": v, "domain": "tuongtaccheo.com"} for k, v in cookies.items()]
            r = requests.post(ep, json=payload, timeout=70)
            data = r.json()
            if data.get("status") == "ok":
                sol = data["solution"]
                class R:
                    status_code = sol.get("status", 200)
                    text = sol.get("response", "")
                    def json(self): return json.loads(self.text)
                return R()
        except Exception as e:
            UI.warn(f"FlareSolverr lỗi: {e}")

    # Request thường
    try:
        if method == "GET":
            return requests.get(url, params=params, headers=headers, cookies=cookies, timeout=25)
        return requests.post(url, data=params, headers=headers, cookies=cookies, timeout=25)
    except Exception as e:
        UI.err(f"Request lỗi: {e}")
        return None

def parse_response(r):
    """Đọc response thông minh – trả về dict chuẩn hóa"""
    if r is None:
        return {"ok": False, "error": "Không kết nối được", "countdown": 0, "raw": ""}
    text = r.text or ""
    if "Just a moment" in text or "cf-browser-verification" in text:
        return {"ok": False, "error": "Cloudflare chặn", "countdown": 0, "raw": text[:100]}

    # Số thuần (mã lỗi kiểu 7 = thiếu session/cookie)
    if text.strip().isdigit():
        code = text.strip()
        msg = {
            "7": "Mã 7 – thiếu PHPSESSID cookie hoặc session hết hạn (cần login lại)",
        }.get(code, f"Mã lỗi {code}")
        return {"ok": False, "error": msg, "countdown": 0, "raw": code, "need_relogin": code == "7"}

    try:
        data = r.json()
    except:
        return {"ok": False, "error": "Không phải JSON", "countdown": 0, "raw": text[:200]}

    # Chuẩn hóa các trường phổ biến từ API
    result = {
        "ok": True,
        "error": data.get("error") or data.get("mess") or data.get("message") or "",
        "countdown": int(data.get("countdown") or 0),
        "sodu": data.get("sodu") or data.get("balance") or 0,
        "data": data,
        "raw": data,
    }
    if result["error"]:
        result["ok"] = False
    return result

# ═══════════════════════════════════════════════════════════════
#  API FUNCTIONS
# ═══════════════════════════════════════════════════════════════
def api_login(force=False):
    if not force:
        sid = load_session()
        if sid:
            UI.ok(f"Dùng session cũ: {sid[:20]}...")
            return sid

    UI.info("Đang login...")
    r = _request("POST", "/logintoken.php", {"access_token": ACCESS_TOKEN}, use_token=True)
    if not r:
        UI.err("Login thất bại – không kết nối")
        return None

    sid = r.cookies.get("PHPSESSID")
    if not sid:
        m = re.search(r"PHPSESSID=([^;,\s]+)", r.headers.get("Set-Cookie", ""), re.I)
        if m:
            sid = m.group(1)

    if not sid:
        UI.err(f"Không lấy được PHPSESSID | {r.text[:150]}")
        return None

    save_session(sid)
    parsed = parse_response(r)
    if parsed.get("data", {}).get("status") == "success" or "success" in str(parsed.get("raw", "")):
        d = parsed.get("data", {}).get("data", {})
        UI.ok(f"Login OK | User: {d.get('user', '?')} | Số dư: {d.get('sodu', '?')}")
    else:
        UI.ok("Login OK (có PHPSESSID)")
    return sid



def api_list_nicks(sid):
    """
    Lấy nick đã cấu hình.
    Trả về: [{"id": "7342...", "username": "ontopmediamusic"}, ...]
    API bắt buộc nickchay = ID số.
    """
    accounts = []
    seen = set()
    cookies = {"PHPSESSID": sid}
    r = _request("GET", "/cauhinh/tiktok.php", {}, cookies)
    if r and getattr(r, "text", None) and "Just a moment" not in (r.text or ""):
        html = r.text
        # value="7342047969309328392" ... ontopmediamusic
        pat = r"value=[\'\"](\d{10,25})[\'\"][^>]*>.*?([A-Za-z0-9._]{2,40})"
        for m in re.finditer(pat, html, re.I | re.S):
            uid, uname = m.group(1), m.group(2)
            if uname.lower() in ("checkbox", "input", "label", "img", "span", "div", "li", "ul"):
                continue
            if uid not in seen:
                seen.add(uid)
                accounts.append({"id": uid, "username": uname})
        if not accounts:
            ids = re.findall(r"value=[\'\"](\d{10,25})[\'\"]", html)
            users = re.findall(r"@([A-Za-z0-9._]{2,40})", html)
            for i, uid in enumerate(ids):
                uname = users[i] if i < len(users) else uid
                if uid not in seen:
                    seen.add(uid)
                    accounts.append({"id": uid, "username": uname})

    if NICKS_FILE.exists():
        for line in NICKS_FILE.read_text().splitlines():
            line = line.strip().lstrip("@")
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                uid, uname = [x.strip() for x in line.split("|", 1)]
            elif line.isdigit() and len(line) >= 10:
                uid, uname = line, line
            else:
                found = next((x for x in accounts if x["username"] == line), None)
                if found:
                    continue
                uid, uname = line, line
            if uid not in seen:
                seen.add(uid)
                accounts.append({"id": uid, "username": uname})

    if not accounts and DEFAULT_NICK:
        accounts.append({"id": DEFAULT_NICK, "username": DEFAULT_NICK})
    return accounts


def pick_random_nick(sid):
    """Tự nhận 1 acc ngẫu nhiên – trả về ID số (nickchay)"""
    accounts = api_list_nicks(sid)
    if not accounts:
        UI.err("Không tìm thấy nick nào đã cấu hình")
        return None
    chosen = random.choice(accounts)
    UI.ok("Có %d acc: %s" % (len(accounts), ", ".join("%s(%s…)" % (a["username"], a["id"][:8]) for a in accounts[:5])))
    UI.ok("Random chọn: %s | nickchay=%s" % (chosen["username"], chosen["id"]))
    cfg = load_config()
    cfg["last_nick"] = chosen
    cfg["accounts"] = accounts
    save_config(cfg)
    return chosen["id"]


def api_get_tasks(sid, job_key="5", nick=DEFAULT_NICK):
    job = JOB_TYPES.get(job_key, JOB_TYPES["5"])
    path_suffix = job["path"]
    if path_suffix:
        path = f"/tiktok/kiemtien/{path_suffix}/getpost.php"
    else:
        path = "/tiktok/kiemtien/getpost.php"

    UI.info(f"Lấy nhiệm vụ [{job['name']}] → {path}")
    cookies = {"PHPSESSID": sid}
    r = _request("GET", path, {"nickchay": nick}, cookies)
    result = parse_response(r)
    # Tự relogin nếu bị mã 7
    if result.get("need_relogin") or result.get("raw") == "7":
        UI.warn("Gặp mã 7 → tự login lại session...")
        new_sid = api_login(force=True)
        if new_sid:
            sid = new_sid
            cookies = {"PHPSESSID": sid}
            r = _request("GET", path, {"nickchay": nick}, cookies)
            result = parse_response(r)

    if result["countdown"] > 0:
        UI.warn(f"{result['error']} (chờ {result['countdown']}s)")
    elif not result["ok"]:
        UI.err(result["error"] or "Lỗi không xác định")
        if result["raw"] and not isinstance(result["raw"], dict):
            print(f"      {UI.K}{str(result['raw'])[:120]}{UI.R}")
    else:
        data = result["data"]
        if isinstance(data, list):
            UI.ok(f"Có {len(data)} nhiệm vụ")
            for i, t in enumerate(data[:6], 1):
                # API trả idpost (không phải id)
                tid = t.get("idpost") or t.get("id") or "?"
                link = str(t.get("link") or t.get("url") or "")[:50]
                extra = ""
                if t.get("uid"):
                    extra = f" uid={t['uid']}"
                if t.get("nd"):
                    extra = f" cmt={str(t['nd'])[:40]}"
                print(f"      {UI.W}{i}. idpost={tid[:22]}…  {UI.K}{link}{extra}{UI.R}")
            if len(data) > 6:
                print(f"      {UI.K}... +{len(data)-6} nhiệm vụ nữa{UI.R}")
        else:
            UI.ok("Response:")
            print(f"      {json.dumps(data, ensure_ascii=False)[:200]}")
    return result


def api_claim(sid, ids, job_key="5", nick=DEFAULT_NICK):
    if isinstance(ids, list):
        ids = ",".join(str(x) for x in ids)
    job = JOB_TYPES.get(job_key, JOB_TYPES["5"])
    path_suffix = job["path"]
    if path_suffix:
        path = f"/tiktok/kiemtien/{path_suffix}/nhantien.php"
    else:
        path = "/tiktok/kiemtien/nhantien.php"

    UI.info(f"Claim [{job['name']}] idpost={ids}")
    cookies = {"PHPSESSID": sid}
    # API nhận field id = danh sách idpost
    r = _request("POST", path, {"id": ids, "idpost": ids, "nickchay": nick}, cookies)
    result = parse_response(r)
    if result.get("need_relogin") or result.get("raw") == "7":
        UI.warn("Gặp mã 7 → tự login lại session...")
        new_sid = api_login(force=True)
        if new_sid:
            sid = new_sid
            cookies = {"PHPSESSID": sid}
            r = _request("POST", path, {"id": ids, "nickchay": nick}, cookies)
            result = parse_response(r)

    if result["countdown"] > 0:
        UI.warn(f"{result['error']} (chờ {result['countdown']}s)")
    elif not result["ok"]:
        UI.err(result["error"] or "Claim lỗi")
    else:
        UI.ok(f"Claim thành công | Số dư: {result.get('sodu', '?')}")
        print(f"      {json.dumps(result['data'], ensure_ascii=False)[:200]}")
    return result


def smart_wait(seconds, label="Chờ"):
    """Đếm ngược đẹp"""
    seconds = max(1, int(seconds))
    for left in range(seconds, 0, -1):
        mins, secs = divmod(left, 60)
        bar_len = 30
        filled = int(bar_len * (seconds - left) / seconds)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  {UI.M}⏳{UI.R}  {label}: {mins:02d}:{secs:02d}  {UI.C}{bar}{UI.R}  ", end="", flush=True)
        time.sleep(1)
    print(f"\r  {UI.G}✔{UI.R}  {label}: xong{' ' * 40}")


# ═══════════════════════════════════════════════════════════════
#  FULL AUTO – đọc response để tự điều chỉnh
# ═══════════════════════════════════════════════════════════════
def full_auto(sid, nick=None):
    if not nick:
        nick = pick_random_nick(sid) or DEFAULT_NICK
    UI.box_top("FULL AUTO")
    UI.box_mid(f"Nick cày: {nick}")
    UI.box_mid(f"Bắt đầu: {datetime.now().strftime('%H:%M:%S')}")
    UI.box_bot()
    print()

    total_tasks = 0
    for key, job in JOB_TYPES.items():
        print(f"\n  {UI.B}{UI.C}▸ {job['name']}{UI.R}")
        print(f"  {UI.line('·')}")

        result = api_get_tasks(sid, key, nick)

        # Tự đọc countdown từ API và chờ
        if result["countdown"] > 0:
            wait_sec = min(result["countdown"] + 2, 180)  # tối đa 3 phút
            smart_wait(wait_sec, f"Rate-limit {job['name']}")
            # Thử lại 1 lần sau khi chờ
            result = api_get_tasks(sid, key, nick)

        if result["ok"] and isinstance(result.get("data"), list):
            tasks = result["data"]
            total_tasks += len(tasks)
            # Có nhiệm vụ → có thể claim (tùy chọn, hiện chỉ log)
            # ids = [t["id"] for t in tasks if "id" in t]
            # if ids:
            #     time.sleep(DELAY_BETWEEN)
            #     api_claim(sid, ids[:5], key, nick)

        # Delay giữa các loại job
        if key != list(JOB_TYPES.keys())[-1]:
            smart_wait(DELAY_BETWEEN, "Nghỉ giữa các job")

    print()
    UI.box_top("KẾT QUẢ")
    UI.box_mid(f"Tổng nhiệm vụ lấy được: {total_tasks}")
    UI.box_mid(f"Kết thúc: {datetime.now().strftime('%H:%M:%S')}")
    UI.box_bot()


# ═══════════════════════════════════════════════════════════════
#  MENU
# ═══════════════════════════════════════════════════════════════
def show_menu():
    print(f"""
  {UI.C}{UI.B}┌─────────────────────────────────────────┐
  │           M E N U   C H Í N H           │
  ├─────────────────────────────────────────┤
  │  1. Login / Làm mới session             │
  │  2. Lấy nhiệm vụ (chọn loại)            │
  │  3. Claim nhiệm vụ                      │
  │  4. Full Auto (random acc đã cấu hình)  │
  │  5. Xem session & danh sách nick        │
  │  6. Random chọn acc cày                 │
  │  0. Thoát                               │
  └─────────────────────────────────────────┘{UI.R}
""")

def choose_job():
    print(f"\n  {UI.B}Chọn loại nhiệm vụ:{UI.R}")
    for k, v in JOB_TYPES.items():
        print(f"    {UI.C}{k}.{UI.R} {v['name']}")
    c = input(f"\n  {UI.Y}› {UI.R}").strip()
    return c if c in JOB_TYPES else "5"


def main():
    banner()
    sid = load_session()
    if sid:
        UI.ok(f"Session sẵn có: {sid[:22]}...")
    else:
        UI.warn("Chưa có session – hãy login trước")

    while True:
        show_menu()
        choice = input(f"  {UI.Y}Chọn chức năng › {UI.R}").strip()

        if choice == "0":
            print(f"\n  {UI.C}Tạm biệt!{UI.R}\n")
            break

        elif choice == "1":
            print()
            sid = api_login(force=True)

        elif choice == "2":
            if not sid:
                sid = api_login()
            if sid:
                print()
                job = choose_job()
                print()
                api_get_tasks(sid, job)

        elif choice == "3":
            if not sid:
                sid = api_login()
            if sid:
                print()
                job = choose_job()
                ids = input(f"  {UI.Y}Nhập ID nhiệm vụ (cách nhau dấu phẩy) › {UI.R}").strip()
                if ids:
                    print()
                    api_claim(sid, ids, job)

        elif choice == "4":
            if not sid:
                sid = api_login()
            if sid:
                print()
                full_auto(sid)

        elif choice == "5":
            print()
            UI.box_top("THÔNG TIN")
            UI.box_mid(f"PHPSESSID : {(sid or 'Chưa có')[:40]}")
            UI.box_mid(f"File      : {SESSION_FILE}")
            UI.box_mid(f"Token     : {ACCESS_TOKEN[:16]}...")
            UI.box_bot()
            if sid:
                print()
                accounts = api_list_nicks(sid)
                UI.info(f"Nick đã cấu hình ({len(accounts)}):")
                for a in accounts:
                    if isinstance(a, dict):
                        print(f"      • {a.get('username')}  →  nickchay={a.get('id')}")
                    else:
                        print(f"      • {a}")
        elif choice == "6":
            if not sid:
                sid = api_login()
            if sid:
                print()
                pick_random_nick(sid)

        else:
            UI.warn("Lựa chọn không hợp lệ")

        print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {UI.Y}Đã dừng.{UI.R}\n")
