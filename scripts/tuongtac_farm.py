#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║                         O N T O P                            ║
║              Multi-Acc TikTok Job Farmer                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, re, sys, json, time, random, threading, requests
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from tiktok_actions import get_actor_for_account, do_task_action
    HAS_TT = True
except Exception:
    HAS_TT = False

# ═══════════════════════ CONFIG ═══════════════════════
BASE_URL      = "https://tuongtaccheo.com"
ACCESS_TOKEN  = os.getenv("ACCESS_TOKEN", "cfb194b9dbd24ab7789b762e9e65d0ef")
SCRIPT_DIR    = Path(__file__).parent
SESSION_FILE  = SCRIPT_DIR / "phpsessid.txt"
NICKS_FILE    = SCRIPT_DIR / "nicks.txt"
SESSIONS_FILE = SCRIPT_DIR / "tiktok_sessions.txt"

MAX_MISS      = 10
DEFAULT_TARGET = 10000
DELAY_MIN, DELAY_MAX = 3, 8
WORKERS       = 4

JOBS = {
    "sub": {"name": "Sub",    "path": "subcheo"},
    "vip": {"name": "SubVIP", "path": "subcheovip"},
    "tim": {"name": "Tim",    "path": "timcheo"},
    "cmt": {"name": "CMT",    "path": "cmtcheo"},
}

# ═══════════════════════ COLORS ═══════════════════════
class C:
    R = "\033[0m"; B = "\033[1m"; D = "\033[2m"
    G = "\033[92m"; Y = "\033[93m"; E = "\033[91m"
    C = "\033[96m"; M = "\033[95m"; K = "\033[90m"
    W = "\033[97m"; P = "\033[95m"
    BG = "\033[48;5;17m"

# ═══════════════════════ UI ENGINE ═══════════════════════
def clear():
    os.system("clear" if os.name != "nt" else "cls")

def term_w():
    try:
        return max(80, os.get_terminal_size().columns)
    except Exception:
        return 100

def box(title, lines, width=None, color=C.C):
    """Khung bo góc tròn"""
    w = width or min(term_w() - 2, 100)
    inner = w - 2
    top = f"{color}╭{'─' * inner}╮{C.R}"
    if title:
        t = f" {title} "
        pad = inner - len(t)
        left = pad // 2
        right = pad - left
        top = f"{color}╭{'─' * left}{C.B}{C.W}{t}{C.R}{color}{'─' * right}╮{C.R}"
    print(top)
    for line in lines:
        # strip ansi for length
        plain = re.sub(r"\033\[[0-9;]*m", "", line)
        pad = max(0, inner - len(plain) - 1)
        print(f"{color}│{C.R} {line}{' ' * pad}{color}│{C.R}")
    print(f"{color}╰{'─' * inner}╯{C.R}")

def banner():
    clear()
    art = f"""{C.C}{C.B}
     ██████╗  ███╗   ██╗ ████████╗  ██████╗  ██████╗ 
    ██╔═══██╗ ████╗  ██║ ╚══██╔══╝ ██╔═══██╗ ██╔══██╗
    ██║   ██║ ██╔██╗ ██║    ██║    ██║   ██║ ██████╔╝
    ██║   ██║ ██║╚██╗██║    ██║    ██║   ██║ ██╔═══╝ 
    ╚██████╔╝ ██║ ╚████║    ██║    ╚██████╔╝ ██║     
     ╚═════╝  ╚═╝  ╚═══╝    ╚═╝     ╚═════╝  ╚═╝     
{C.R}{C.M}{C.B}          ⚡  MULTI-ACC TIKTOK JOB FARMER  ⚡{C.R}
{C.K}          Tuongtaccheo • Session • Parallel • Smart{C.R}
"""
    print(art)

def log_ok(m):  print(f"  {C.G}✔{C.R}  {m}")
def log_info(m): print(f"  {C.C}●{C.R}  {m}")
def log_warn(m): print(f"  {C.Y}▲{C.R}  {m}")
def log_err(m):  print(f"  {C.E}✘{C.R}  {m}")

print_lock = threading.Lock()
states_lock = threading.Lock()

# ═══════════════════════ HTTP ═══════════════════════
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

def hdrs():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/",
        "Origin": BASE_URL,
    }

def api_get(sid, path, params=None):
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params or {},
                         cookies={"PHPSESSID": sid}, headers=hdrs(), timeout=25)
        t = r.text or ""
        if t.strip().isdigit():
            return {"_code": t.strip()}
        try:
            return r.json()
        except Exception:
            return {"_raw": t[:300]}
    except Exception as e:
        return {"_error": str(e)}

def api_post(sid, path, data=None):
    try:
        r = requests.post(f"{BASE_URL}{path}", data=data or {},
                          cookies={"PHPSESSID": sid}, headers=hdrs(), timeout=25)
        t = r.text or ""
        if t.strip().isdigit():
            return {"_code": t.strip()}
        try:
            return r.json()
        except Exception:
            return {"_raw": t[:300]}
    except Exception as e:
        return {"_error": str(e)}

# ═══════════════════════ ACCOUNTS ═══════════════════════
def load_accounts():
    """Đọc nicks.txt + tiktok_sessions.txt"""
    accs = {}
    # nicks: id|username|user_field|sessionid
    if NICKS_FILE.exists():
        for line in NICKS_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if not parts[0]:
                continue
            aid = parts[0]
            uname = parts[1] if len(parts) > 1 else aid
            ufield = parts[2] if len(parts) > 2 else ""
            sess = parts[3] if len(parts) > 3 else ""
            accs[aid] = {"id": aid, "username": uname, "user_field": ufield, "sessionid": sess}

    # sessions: tt_uid|username|sessionid|email|user_field
    if SESSIONS_FILE.exists():
        for line in SESSIONS_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            aid, uname, sess = parts[0], parts[1], parts[2]
            ufield = parts[4] if len(parts) > 4 else (parts[3] if len(parts) > 3 else "")
            if aid in accs:
                accs[aid]["sessionid"] = sess or accs[aid].get("sessionid", "")
                if ufield:
                    accs[aid]["user_field"] = ufield
            else:
                accs[aid] = {"id": aid, "username": uname, "user_field": ufield, "sessionid": sess}
    return list(accs.values())

def set_active_nick(sid, nick_id):
    return api_post(sid, "/cauhinh/datnick.php", {"iddat": nick_id, "loai": "tt"})

# ═══════════════════════ JOBS ═══════════════════════
def get_tasks(sid, job_key, nick_id):
    path = f"/tiktok/kiemtien/{JOBS[job_key]['path']}/getpost.php"
    return api_get(sid, path, {"nickchay": nick_id})

def claim_tasks(sid, job_key, nick_id, idposts):
    path = f"/tiktok/kiemtien/{JOBS[job_key]['path']}/nhantien.php"
    ids = ",".join(idposts) if isinstance(idposts, list) else str(idposts)
    return api_post(sid, path, {"id": ids, "idpost": ids, "nickchay": nick_id})

def parse_tasks(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if data.get("_code") == "7":
            return {"error": "session_die", "countdown": 0}
        if "error" in data:
            return data
        if isinstance(data.get("data"), list):
            return data["data"]
    return {"error": str(data)[:100], "countdown": 0}

# ═══════════════════════ STATE ═══════════════════════
class AccState:
    def __init__(self, acc):
        self.id = acc["id"]
        self.username = acc.get("username") or acc["id"][:12]
        self.user_field = acc.get("user_field") or ""
        self.sessionid = acc.get("sessionid") or ""
        self.status = "idle"
        self.job = "-"
        self.target = "-"
        self.result = "-"
        self.done = 0
        self.miss = 0
        self.xu = 0
        self.msg = ""

states = {}
global_done = 0
global_target = DEFAULT_TARGET
stop_all = False

def print_dashboard():
    with states_lock:
        rows = list(states.values())
        total_done = sum(s.done for s in rows)
        total_xu = sum(s.xu for s in rows)
        running = sum(1 for s in rows if s.status == "running")
        stopped = sum(1 for s in rows if s.status == "stopped")
        idle = sum(1 for s in rows if s.status in ("idle", "done"))

    clear()
    # mini banner
    print(f"""{C.C}{C.B}
  ╭──────────────────────────────────────────────────────────────╮
  │   ██████╗ ███╗   ██╗████████╗ ██████╗ ██████╗                │
  │  ██╔═══██╗████╗  ██║╚══██╔══╝██╔═══██╗██╔══██╗               │
  │  ██║   ██║██╔██╗ ██║   ██║   ██║   ██║██████╔╝               │
  │  ██║   ██║██║╚██╗██║   ██║   ██║   ██║██╔═══╝                │
  │  ╚██████╔╝██║ ╚████║   ██║   ╚██████╔╝██║                    │
  │   ╚═════╝ ╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝                    │
  ╰──────────────────────────────────────────────────────────────╯{C.R}""")

    pct = min(100, int(total_done / global_target * 100)) if global_target else 0
    bar_len = 30
    filled = int(bar_len * pct / 100)
    bar = f"{C.G}{'█' * filled}{C.K}{'░' * (bar_len - filled)}{C.R}"

    stats = [
        f"{C.B}Tiến độ{C.R}  {bar}  {C.W}{pct}%{C.R}  {total_done}/{global_target}",
        f"{C.G}● Running {running}{C.R}   {C.E}● Stopped {stopped}{C.R}   {C.K}● Other {idle}{C.R}   {C.Y}Xu +{total_xu}{C.R}",
        f"{C.K}{datetime.now().strftime('%H:%M:%S')}  •  Miss limit {MAX_MISS}/acc  •  Ctrl+C dừng{C.R}",
    ]
    box("TỔNG QUAN", stats, width=78, color=C.C)

    # table header
    print()
    hdr = f"  {'USER':<16} {'ID':<16} {'STT':<9} {'JOB':<7} {'TARGET':<22} {'KQ':<10} {'DONE':>5} {'MISS':>4} {'XU':>5}"
    print(f"{C.B}{hdr}{C.R}")
    print(f"  {C.K}{'─' * 100}{C.R}")

    for s in rows:
        stc = {"running": C.G, "stopped": C.E, "done": C.C, "idle": C.K}.get(s.status, C.W)
        uid_short = s.id[:14] + "…" if len(s.id) > 14 else s.id
        tgt = str(s.target)[:20]
        print(
            f"  {s.username:<16} {uid_short:<16} {stc}{s.status:<9}{C.R} "
            f"{s.job:<7} {tgt:<22} {s.result:<10} {s.done:>5} {s.miss:>4} {s.xu:>5}"
        )
    print(f"  {C.K}{'─' * 100}{C.R}\n")

# ═══════════════════════ WORKER ═══════════════════════
def farm_one(sid, st: AccState, mode: str):
    global global_done, stop_all
    nick_id = st.id
    cycle = ["sub", "tim", "cmt", "vip"] if mode == "tonghop" else [mode]
    idx = 0
    set_active_nick(sid, nick_id)

    with states_lock:
        st.status = "running"

    while not stop_all and st.miss < MAX_MISS and global_done < global_target:
        job_key = cycle[idx % len(cycle)]
        idx += 1
        job = JOBS[job_key]

        with states_lock:
            st.job = job["name"]
            st.result = "đang lấy"
            st.target = "-"
            st.msg = ""

        data = get_tasks(sid, job_key, nick_id)
        tasks = parse_tasks(data)

        if isinstance(tasks, dict):
            err = str(tasks.get("error") or tasks.get("_error") or "")
            cd = int(tasks.get("countdown") or 0)
            with states_lock:
                st.result = "chờ" if cd else "lỗi"
                st.msg = err[:40]
            if tasks.get("error") == "session_die" or tasks.get("_code") == "7":
                ns = login(force=True)
                if ns:
                    sid = ns
                st.miss += 1
                time.sleep(4)
                continue
            if cd > 0:
                time.sleep(min(cd, 25) if mode == "tonghop" else min(cd, 50))
                continue
            st.miss += 1
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        if not tasks:
            with states_lock:
                st.result = "hết job"
                st.miss += 1
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        batch = tasks[:3]
        ok_ids = []   # chỉ claim job đã làm TT thành công
        done_tt = 0
        actor = None
        if HAS_TT:
            try:
                actor = get_actor_for_account({
                    "id": st.id, "username": st.username,
                    "sessionid": st.sessionid, "user_field": st.user_field,
                })
            except Exception as e:
                with states_lock:
                    st.msg = ("TT sess: " + str(e))[:40]

        for t in batch:
            idp = str(t.get("idpost") or t.get("id") or "")
            if not idp:
                continue
            with states_lock:
                st.target = str(t.get("link") or t.get("uid") or idp)[:22]
                st.result = "dang TT"

            success = False
            if actor:
                # tối đa 2 vòng / task
                for attempt in range(2):
                    try:
                        ar = do_task_action(actor, job_key, t)
                        if ar.get("ok"):
                            success = True
                            done_tt += 1
                            with states_lock:
                                st.result = "TT:" + str(ar.get("action", "ok"))
                            break
                        else:
                            with states_lock:
                                st.result = "TT retry" if attempt == 0 else "TT fail"
                                st.msg = str(ar.get("error") or ar.get("raw", ""))[:36]
                    except Exception as e:
                        with states_lock:
                            st.result = "TT err"
                            st.msg = str(e)[:36]
                    time.sleep(1.5)
            else:
                with states_lock:
                    st.result = "no TT sess"

            if success:
                ok_ids.append(idp)
            time.sleep(random.uniform(1.2, 2.5))

        if actor:
            try:
                actor.close()
            except Exception:
                pass

        if not ok_ids:
            with states_lock:
                st.miss += 1
                st.result = "0 ok"
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        # Claim CHỈ những id đã làm TT thành công
        time.sleep(random.uniform(1.0, 2.0))
        claim = claim_tasks(sid, job_key, nick_id, ok_ids)
        result_txt = "OK %d/%d" % (done_tt, len(batch))
        if isinstance(claim, dict) and claim.get("error"):
            result_txt = "cho claim"
            st.msg = str(claim.get("error"))[:36]

        with states_lock:
            st.done += len(ok_ids)
            st.result = result_txt
            st.miss = 0
            global_done += len(ok_ids)

        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    with states_lock:
        if st.miss >= MAX_MISS:
            st.status = "stopped"
            st.msg = f"miss>={MAX_MISS}"
        elif global_done >= global_target:
            st.status = "done"
        else:
            st.status = "stopped"

# ═══════════════════════ MAIN ═══════════════════════
def main():
    global global_target, stop_all, global_done, states

    banner()
    box("KHỞI ĐỘNG", [
        f"{C.C}●{C.R} Đang login tuongtaccheo...",
    ], width=60)

    sid = login(force=True)
    if not sid:
        log_err("Login thất bại – kiểm tra ACCESS_TOKEN")
        return
    log_ok(f"Session OK  {sid[:22]}...")

    accounts = load_accounts()
    if not accounts:
        log_err("Không có acc – kiểm tra scripts/nicks.txt")
        return

    lines = [f"{C.G}✔{C.R}  Load {C.B}{len(accounts)}{C.R} acc từ nicks.txt / sessions"]
    for a in accounts[:8]:
        lines.append(f"    {C.W}{a['username']:<16}{C.R} {C.K}{a['id'][:18]}{C.R}")
    if len(accounts) > 8:
        lines.append(f"    {C.K}... +{len(accounts)-8} acc nữa{C.R}")
    box("DANH SÁCH ACC", lines, width=60, color=C.C)
    print()

    box("CHỌN CHẾ ĐỘ", [
        f"  {C.C}1{C.R}. Sub          {C.C}2{C.R}. Tim (Like)",
        f"  {C.C}3{C.R}. Comment      {C.C}4{C.R}. Sub VIP",
        f"  {C.C}5{C.R}. {C.B}Tổng hợp{C.R} (sub → tim → cmt → vip)",
    ], width=60, color=C.M)

    choice = input(f"\n  {C.Y}› Chế độ [5] {C.R}").strip() or "5"
    mode_map = {"1": "sub", "2": "tim", "3": "cmt", "4": "vip", "5": "tonghop"}
    mode = mode_map.get(choice, "tonghop")

    t = input(f"  {C.Y}› Mục tiêu nhiệm vụ [{DEFAULT_TARGET}] {C.R}").strip()
    global_target = int(t) if t.isdigit() else DEFAULT_TARGET

    w = input(f"  {C.Y}› Số acc song song [{min(WORKERS, len(accounts))}] {C.R}").strip()
    workers = int(w) if w.isdigit() else min(WORKERS, len(accounts))
    workers = max(1, min(workers, len(accounts)))

    states = {a["id"]: AccState(a) for a in accounts}
    global_done = 0
    stop_all = False

    print()
    box("BẮT ĐẦU", [
        f"Mode     : {C.B}{mode}{C.R}",
        f"Target   : {C.B}{global_target}{C.R}",
        f"Workers  : {C.B}{workers}{C.R}",
        f"Accounts : {C.B}{len(accounts)}{C.R}",
    ], width=50, color=C.G)
    time.sleep(1.5)

    def ui_loop():
        while not stop_all and global_done < global_target:
            if not any(s.status == "running" for s in states.values()) and global_done > 0:
                # wait a bit for stragglers
                time.sleep(2)
                if not any(s.status == "running" for s in states.values()):
                    break
            print_dashboard()
            time.sleep(2)
        print_dashboard()

    ui_t = threading.Thread(target=ui_loop, daemon=True)
    ui_t.start()

    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(farm_one, sid, states[a["id"]], mode) for a in accounts]
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:
                    with print_lock:
                        log_err(f"Worker: {e}")
    except KeyboardInterrupt:
        stop_all = True
        log_warn("Đang dừng toàn bộ...")

    stop_all = True
    time.sleep(2)
    print_dashboard()
    box("KẾT THÚC", [
        f"Tổng done : {C.B}{global_done}{C.R} / {global_target}",
        f"Thời gian : {datetime.now().strftime('%H:%M:%S')}",
    ], width=50, color=C.M)
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {C.Y}Đã dừng.{C.R}\n")
