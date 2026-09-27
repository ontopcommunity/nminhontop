#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TUONGTACCHEO MULTI-ACC FARMER
- Đọc acc từ nicks.txt / accounts.txt
- Chạy song song nhiều nick
- Bảng trạng thái realtime
- Mode: sub / tim / cmt / tonghop
- Miss >= 10 → dừng acc đó
- Mục tiêu tổng số nhiệm vụ (vd 10000)
"""

import os
import re
import sys
import json
import time
import random
import threading
import requests
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══════════════════ CONFIG ═══════════════════
BASE_URL     = "https://tuongtaccheo.com"
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "cfb194b9dbd24ab7789b762e9e65d0ef")
SCRIPT_DIR   = Path(__file__).parent
SESSION_FILE = SCRIPT_DIR / "phpsessid.txt"
NICKS_FILE   = SCRIPT_DIR / "nicks.txt"
ACCOUNTS_FILE = SCRIPT_DIR / "accounts.txt"
STATE_FILE   = SCRIPT_DIR / "farm_state.json"

MAX_MISS     = 10          # miss liên tiếp thì dừng acc
DEFAULT_TARGET = 10000     # tổng nhiệm vụ mục tiêu
DELAY_MIN    = 3
DELAY_MAX    = 8
WORKERS      = 4           # số acc chạy song song

JOBS = {
    "sub":  {"name": "Sub",  "path": "subcheo"},
    "vip":  {"name": "SubVIP", "path": "subcheovip"},
    "tim":  {"name": "Tim",  "path": "timcheo"},
    "cmt":  {"name": "CMT",  "path": "cmtcheo"},
}

# ═══════════════════ UI ═══════════════════
class C:
    R="\033[0m"; B="\033[1m"; G="\033[92m"; Y="\033[93m"
    E="\033[91m"; C="\033[96m"; M="\033[95m"; K="\033[90m"; W="\033[97m"

def clear():
    os.system("clear" if os.name != "nt" else "cls")

lock = threading.Lock()
print_lock = threading.Lock()

def log(msg, color=C.W):
    with print_lock:
        print(f"{color}{msg}{C.R}")

# ═══════════════════ HTTP ═══════════════════
def login(force=False):
    if not force and SESSION_FILE.exists():
        sid = SESSION_FILE.read_text().strip()
        if sid:
            return sid
    r = requests.post(
        f"{BASE_URL}/logintoken.php",
        data={"access_token": ACCESS_TOKEN},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20,
    )
    sid = r.cookies.get("PHPSESSID")
    if not sid:
        m = re.search(r"PHPSESSID=([^;,\s]+)", r.headers.get("Set-Cookie", ""), re.I)
        sid = m.group(1) if m else None
    if sid:
        SESSION_FILE.write_text(sid)
    return sid

def headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/",
        "Origin": BASE_URL,
    }

def api_get(sid, path, params=None):
    try:
        r = requests.get(
            f"{BASE_URL}{path}",
            params=params or {},
            cookies={"PHPSESSID": sid},
            headers=headers(),
            timeout=25,
        )
        text = r.text or ""
        if text.strip().isdigit():
            return {"_code": text.strip(), "_raw": text}
        try:
            return r.json()
        except Exception:
            return {"_raw": text[:300]}
    except Exception as e:
        return {"_error": str(e)}

def api_post(sid, path, data=None):
    try:
        r = requests.post(
            f"{BASE_URL}{path}",
            data=data or {},
            cookies={"PHPSESSID": sid},
            headers=headers(),
            timeout=25,
        )
        text = r.text or ""
        if text.strip().isdigit():
            return {"_code": text.strip(), "_raw": text}
        try:
            return r.json()
        except Exception:
            return {"_raw": text[:300]}
    except Exception as e:
        return {"_error": str(e)}

# ═══════════════════ ACCOUNTS ═══════════════════
def load_accounts_from_files():
    """Đọc accounts.txt / nicks.txt – mỗi dòng: id|username hoặc username hoặc id"""
    rows = []
    for f in (ACCOUNTS_FILE, NICKS_FILE):
        if not f.exists():
            continue
        for line in f.read_text().splitlines():
            line = line.strip().lstrip("@")
            if not line or line.startswith("#"):
                continue
            if "|" in line:
                a, b = [x.strip() for x in line.split("|", 1)]
                if a.isdigit():
                    rows.append({"id": a, "username": b})
                else:
                    rows.append({"id": b if b.isdigit() else a, "username": a})
            elif line.isdigit() and len(line) >= 10:
                rows.append({"id": line, "username": line})
            else:
                rows.append({"id": "", "username": line})
    # unique by id or username
    seen = set()
    out = []
    for r in rows:
        key = r["id"] or r["username"]
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def fetch_configured_accounts(sid):
    """Scrape /cauhinh/tiktok.php lấy id + username đã cấu hình"""
    accounts = []
    r = requests.get(
        f"{BASE_URL}/cauhinh/tiktok.php",
        cookies={"PHPSESSID": sid},
        headers=headers(),
        timeout=25,
    )
    html = r.text or ""
    pat = re.compile(r"value=['\"](\d{10,25})['\"][^>]*>.*?([A-Za-z0-9._]{2,40})", re.I | re.S)
    seen = set()
    for m in pat.finditer(html):
        uid, uname = m.group(1), m.group(2)
        if uname.lower() in ("checkbox", "input", "label", "img", "span", "div", "li", "ul"):
            continue
        if uid not in seen:
            seen.add(uid)
            accounts.append({"id": uid, "username": uname})
    if not accounts:
        ids = re.findall(r"value=['\"](\d{10,25})['\"]", html)
        users = re.findall(r"@([A-Za-z0-9._]{2,40})", html)
        for i, uid in enumerate(ids):
            uname = users[i] if i < len(users) else uid
            if uid not in seen:
                seen.add(uid)
                accounts.append({"id": uid, "username": uname})
    return accounts

def resolve_accounts(sid):
    """Gộp file local + đã cấu hình trên web; ưu tiên ID số"""
    file_accs = load_accounts_from_files()
    web_accs = fetch_configured_accounts(sid)
    web_by_user = {a["username"].lower(): a for a in web_accs}
    web_by_id = {a["id"]: a for a in web_accs}

    resolved = []
    seen = set()

    for a in file_accs:
        uid, uname = a.get("id") or "", a.get("username") or ""
        if not uid and uname.lower() in web_by_user:
            uid = web_by_user[uname.lower()]["id"]
        if uid and uid in web_by_id:
            uname = web_by_id[uid]["username"]
        if not uid:
            # chưa có trên web – bỏ qua (cần captcha để thêm)
            continue
        if uid in seen:
            continue
        seen.add(uid)
        resolved.append({"id": uid, "username": uname or uid})

    # thêm toàn bộ acc web chưa có trong file
    for a in web_accs:
        if a["id"] not in seen:
            seen.add(a["id"])
            resolved.append(a)

    return resolved

def set_active_nick(sid, nick_id):
    """Đặt nick chạy – datnick.php"""
    return api_post(sid, "/cauhinh/datnick.php", {"iddat": nick_id, "loai": "tt"})

# ═══════════════════ JOB ENGINE ═══════════════════
def get_tasks(sid, job_key, nick_id):
    job = JOBS[job_key]
    path = f"/tiktok/kiemtien/{job['path']}/getpost.php"
    data = api_get(sid, path, {"nickchay": nick_id})
    return data

def claim_tasks(sid, job_key, nick_id, idposts):
    job = JOBS[job_key]
    path = f"/tiktok/kiemtien/{job['path']}/nhantien.php"
    ids = ",".join(idposts) if isinstance(idposts, list) else str(idposts)
    return api_post(sid, path, {"id": ids, "idpost": ids, "nickchay": nick_id})

def parse_tasks(data):
    """Chuẩn hóa list task từ API"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if data.get("_code") == "7":
            return {"error": "session_die", "countdown": 0}
        if "error" in data:
            return data
        if "data" in data and isinstance(data["data"], list):
            return data["data"]
    return {"error": str(data)[:120], "countdown": 0}

# ═══════════════════ ACCOUNT STATE ═══════════════════
class AccState:
    def __init__(self, acc):
        self.id = acc["id"]
        self.username = acc["username"]
        self.status = "idle"          # idle / running / stopped / done
        self.job = "-"
        self.target = "-"             # link hoặc username mục tiêu
        self.last_result = "-"        # chưa làm / đã làm / lỗi
        self.done = 0
        self.miss = 0
        self.xu = 0
        self.message = ""

    def row(self):
        return {
            "username": self.username,
            "id": self.id[:12] + "…",
            "status": self.status,
            "job": self.job,
            "target": str(self.target)[:28],
            "result": self.last_result,
            "done": self.done,
            "miss": self.miss,
            "xu": self.xu,
            "msg": self.message[:24],
        }

# global states
states = {}
states_lock = threading.Lock()
global_done = 0
global_target = DEFAULT_TARGET
stop_all = False

def print_table():
    with states_lock:
        rows = [s.row() for s in states.values()]
        total_done = sum(s.done for s in states.values())
        total_xu = sum(s.xu for s in states.values())
        running = sum(1 for s in states.values() if s.status == "running")
        stopped = sum(1 for s in states.values() if s.status == "stopped")

    clear()
    print(f"""{C.C}{C.B}
╔══════════════════════════════════════════════════════════════════════════════╗
║              TUONGTACCHEO MULTI-ACC FARMER                                   ║
║  Done: {total_done}/{global_target}   Running: {running}   Stopped: {stopped}   Xu: {total_xu}            ║
╚══════════════════════════════════════════════════════════════════════════════╝{C.R}
""")
    hdr = f"{'USER':<16} {'ID':<14} {'STT':<9} {'JOB':<7} {'TARGET':<28} {'KQ':<10} {'DONE':>5} {'MISS':>5} {'XU':>6}"
    print(f"{C.B}{hdr}{C.R}")
    print(f"{C.K}{'-'*110}{C.R}")
    for r in rows:
        st_color = C.G if r["status"]=="running" else (C.E if r["status"]=="stopped" else C.K)
        print(
            f"{r['username']:<16} {r['id']:<14} {st_color}{r['status']:<9}{C.R} "
            f"{r['job']:<7} {r['target']:<28} {r['result']:<10} {r['done']:>5} {r['miss']:>5} {r['xu']:>6}"
        )
    print(f"{C.K}{'-'*110}{C.R}")
    print(f"  {C.K}{datetime.now().strftime('%H:%M:%S')}  Ctrl+C để dừng{C.R}\n")

# ═══════════════════ WORKER ═══════════════════
def farm_one(sid, acc_state: AccState, mode: str):
    """mode: sub|tim|cmt|vip|tonghop"""
    global global_done, stop_all
    nick_id = acc_state.id
    cycle = ["sub", "tim", "cmt", "vip"] if mode == "tonghop" else [mode]
    idx = 0

    # đặt nick active (best effort)
    set_active_nick(sid, nick_id)

    with states_lock:
        acc_state.status = "running"

    while not stop_all and acc_state.miss < MAX_MISS and global_done < global_target:
        job_key = cycle[idx % len(cycle)]
        idx += 1
        job = JOBS[job_key]

        with states_lock:
            acc_state.job = job["name"]
            acc_state.last_result = "đang lấy"
            acc_state.target = "-"
            acc_state.message = ""

        data = get_tasks(sid, job_key, nick_id)
        tasks = parse_tasks(data)

        # rate limit / error
        if isinstance(tasks, dict):
            err = tasks.get("error") or tasks.get("_error") or ""
            cd = int(tasks.get("countdown") or 0)
            with states_lock:
                acc_state.last_result = "chờ" if cd else "lỗi"
                acc_state.message = str(err)[:40]
            if tasks.get("error") == "session_die" or tasks.get("_code") == "7":
                new_sid = login(force=True)
                if new_sid:
                    sid = new_sid
                acc_state.miss += 1
                time.sleep(5)
                continue
            if cd > 0:
                # hết job / spam → chuyển loại khác trong mode tonghop
                time.sleep(min(cd, 30) if mode == "tonghop" else min(cd, 60))
                continue
            # không có job
            acc_state.miss += 1
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        if not tasks:
            with states_lock:
                acc_state.last_result = "hết job"
                acc_state.miss += 1
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        # có nhiệm vụ – lấy tối đa vài cái rồi claim
        batch = tasks[:5]
        idposts = []
        for t in batch:
            idp = str(t.get("idpost") or t.get("id") or "")
            if not idp:
                continue
            idposts.append(idp)
            target = t.get("link") or t.get("uid") or idp
            with states_lock:
                acc_state.target = target
                acc_state.last_result = "đã lấy"

        if not idposts:
            acc_state.miss += 1
            time.sleep(2)
            continue

        # Claim (panel yêu cầu làm đủ số lượng – vẫn gọi để lấy response xu)
        time.sleep(random.uniform(1.5, 3.5))
        claim = claim_tasks(sid, job_key, nick_id, idposts)

        xu_gain = 0
        result_txt = "đã làm"
        if isinstance(claim, dict):
            if claim.get("error"):
                result_txt = "chưa đủ đk"
                acc_state.message = str(claim.get("error"))[:40]
            else:
                # cố đọc xu
                for k in ("sodu", "xu", "coin", "money", "nhan"):
                    if k in claim and str(claim[k]).replace(".", "").isdigit():
                        break
                if "sodu" in claim:
                    try:
                        # không biết xu trước – chỉ log message
                        result_txt = "claim ok"
                    except Exception:
                        pass
                acc_state.message = json.dumps(claim, ensure_ascii=False)[:40]

        with states_lock:
            acc_state.done += len(idposts)
            acc_state.last_result = result_txt
            acc_state.miss = 0  # reset miss khi có job thành công
            global_done += len(idposts)

        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    with states_lock:
        if acc_state.miss >= MAX_MISS:
            acc_state.status = "stopped"
            acc_state.message = f"miss>={MAX_MISS}"
        elif global_done >= global_target:
            acc_state.status = "done"
        else:
            acc_state.status = "stopped"

# ═══════════════════ MAIN ═══════════════════
def banner():
    clear()
    print(f"""{C.C}{C.B}
╔════════════════════════════════════════════════════════════╗
║         TUONGTACCHEO MULTI-ACC FARMER                      ║
║   Song song • Bảng trạng thái • Sub/Tim/CMT/Tổng hợp       ║
╚════════════════════════════════════════════════════════════╝{C.R}
""")

def main():
    global global_target, stop_all, global_done, states

    banner()
    log("[•] Login...", C.C)
    sid = login(force=True)
    if not sid:
        log("[✘] Login thất bại", C.E)
        return
    log(f"[✔] Session OK: {sid[:20]}...", C.G)

    log("[•] Đọc acc đã cấu hình + file txt...", C.C)
    accounts = resolve_accounts(sid)
    if not accounts:
        log("[✘] Không có acc nào. Thêm vào scripts/nicks.txt (id|username)", C.E)
        log("    Ví dụ: 7342047969309328392|ontopmediamusic", C.K)
        return

    log(f"[✔] Có {len(accounts)} acc:", C.G)
    for a in accounts:
        log(f"    • {a['username']}  →  {a['id']}", C.W)

    print(f"""
  {C.B}Chọn chế độ cày:{C.R}
    1. Sub
    2. Tim (Like)
    3. Comment
    4. Sub VIP
    5. Tổng hợp (sub→tim→cmt→vip xoay vòng)
""")
    choice = input(f"  {C.Y}› {C.R}").strip()
    mode_map = {"1": "sub", "2": "tim", "3": "cmt", "4": "vip", "5": "tonghop"}
    mode = mode_map.get(choice, "tonghop")

    t = input(f"  {C.Y}Mục tiêu tổng nhiệm vụ [{DEFAULT_TARGET}] › {C.R}").strip()
    global_target = int(t) if t.isdigit() else DEFAULT_TARGET

    w = input(f"  {C.Y}Số acc chạy song song [{min(WORKERS, len(accounts))}] › {C.R}").strip()
    workers = int(w) if w.isdigit() else min(WORKERS, len(accounts))
    workers = max(1, min(workers, len(accounts)))

    states = {a["id"]: AccState(a) for a in accounts}
    global_done = 0
    stop_all = False

    log(f"\n[▶] Bắt đầu | mode={mode} | target={global_target} | workers={workers}\n", C.G)
    time.sleep(1)

    # UI refresh thread
    def ui_loop():
        while not stop_all and global_done < global_target:
            alive = any(s.status == "running" for s in states.values())
            if not alive and global_done > 0:
                break
            print_table()
            time.sleep(2)
        print_table()

    ui_t = threading.Thread(target=ui_loop, daemon=True)
    ui_t.start()

    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(farm_one, sid, states[a["id"]], mode) for a in accounts]
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:
                    log(f"Worker lỗi: {e}", C.E)
    except KeyboardInterrupt:
        stop_all = True
        log("\n[!] Đang dừng...", C.Y)

    stop_all = True
    time.sleep(2)
    print_table()
    log(f"[✔] Xong. Tổng done={global_done} / target={global_target}", C.G)

if __name__ == "__main__":
    main()
