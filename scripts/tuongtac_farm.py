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
except Exception as _e:
    HAS_TT = False
    print('tiktok_actions import fail', _e)

# ═══════════════════════ CONFIG ═══════════════════════
BASE_URL      = "https://tuongtaccheo.com"
ACCESS_TOKEN  = os.getenv("ACCESS_TOKEN", "cfb194b9dbd24ab7789b762e9e65d0ef")
SCRIPT_DIR    = Path(__file__).parent
SESSION_FILE  = SCRIPT_DIR / "phpsessid.txt"
NICKS_FILE    = SCRIPT_DIR / "nicks.txt"
SESSIONS_FILE = SCRIPT_DIR / "tiktok_sessions.txt"

MAX_MISS      = 10
DEFAULT_TARGET = 10000
DELAY_MIN, DELAY_MAX = 5, 10  # mỗi nhiệm vụ 5–10 giây
WORKERS       = 5  # đa luồng đa acc (gồm VIP)

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


def check_tt_session_alive(cookies_str: str) -> bool:
    """Passport check – True nếu session còn sống"""
    if not cookies_str:
        return False
    try:
        import requests as rq
        ck = {}
        for p in cookies_str.split(";"):
            p = p.strip()
            if "=" in p:
                k, v = p.split("=", 1)
                ck[k.strip()] = v.strip()
        s = rq.Session()
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.tiktok.com/",
        })
        for k, v in ck.items():
            s.cookies.set(k, v, domain=".tiktok.com")
        r = s.get(
            "https://www.tiktok.com/passport/web/account/info/",
            params={"aid": "1459"},
            timeout=15,
        )
        d = r.json()
        return d.get("message") == "success" and bool(d.get("data", {}).get("user_id"))
    except Exception:
        return False


def filter_alive_accounts(accounts):
    """Chỉ giữ acc session còn sống – cấm dead"""
    from tiktok_actions import _load
    m = _load()
    alive = []
    for a in accounts:
        data = None
        for k in (a.get("id"), a.get("username"), a.get("sessionid"), a.get("user_field")):
            if k and str(k) in m:
                data = m[str(k)]
                break
        cookies = (data or {}).get("cookies") or ""
        if not cookies:
            log_warn(f"Skip @{a.get('username')} – không có cookies")
            continue
        if check_tt_session_alive(cookies):
            alive.append(a)
            log_ok(f"Session OK @{a.get('username')}")
        else:
            log_err(f"DEAD drop @{a.get('username')} – session_expired")
    return alive


def set_active_nick(sid, nick_id, retries=5):
    """Cấu hình nick trên panel trước khi cày. Retry khi rate-limit."""
    last = None
    for attempt in range(retries):
        last = api_post(sid, "/cauhinh/datnick.php", {"iddat": nick_id, "loai": "tt"})
        text = ""
        if isinstance(last, dict):
            text = str(
                last.get("_code")
                or last.get("_raw")
                or last.get("error")
                or last.get("mess")
                or last.get("_error")
                or ""
            ).strip()
        else:
            text = str(last or "").strip()

        low = text.lower()
        # rate-limit → chờ rồi thử lại
        if any(k in low for k in ("chậm", "spam", "giây", "đợi", "nhanh")):
            time.sleep(3 + attempt * 2)
            continue
        # success
        if text in ("0", "1", "2", "ok", "success", ""):
            return True, (text or "ok"), last
        if "thành công" in low or "success" in low:
            return True, text[:40], last
        # mã số thuần
        if text.isdigit() and int(text) <= 5:
            return True, text, last
        time.sleep(2 + attempt)
    return False, str(last)[:80] if last is not None else "fail", last


def configure_account(sid, st: "AccState"):
    """Gọi trước khi farm_one cày — cập nhật dashboard."""
    with states_lock:
        st.status = "config"
        st.result = "đang cấu hình"
        st.msg = "datnick..."
    ok, detail, raw = set_active_nick(sid, st.id)
    with states_lock:
        if ok:
            st.result = "config OK"
            st.msg = f"datnick={detail}"
            st.status = "running"
        else:
            st.result = "config FAIL"
            st.msg = str(detail)[:36]
            st.status = "error"
    return ok

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
    hdr = f"  {'USER':<12} {'XU':<8} {'TRẠNG THÁI':<9} {'JOB':<7} {'TARGET':<18} {'KẾT QUẢ':<12} {'DONE':>4} {'MISS':>3}  GHI CHÚ"
    print(f"{C.B}{hdr}{C.R}")
    print(f"  {C.K}{'─' * 100}{C.R}")

    status_map = {
        "running": (C.G, "ĐANG LÀM"),
        "stopped": (C.E, "DỪNG"),
        "done": (C.C, "XONG"),
        "idle": (C.K, "CHỜ"),
        "wait": (C.Y, "CHỜ JOB"),
        "claim": (C.M, "NHẬN XU"),
        "error": (C.E, "LỖI"),
        "config": (C.M, "CẤU HÌNH"),
    }
    for s in rows:
        stc, stlabel = status_map.get(s.status, (C.W, s.status[:8]))
        # USER + xu ngay sau tên:  @user (+123 xu)
        xu_tag = f"{C.Y}+{s.xu}xu{C.R}" if s.xu else f"{C.K}+0xu{C.R}"
        user_col = f"{s.username[:12]}"
        uid_short = (s.id[:12] + "…") if len(s.id) > 12 else s.id
        tgt = str(s.target)[:18]
        kq = str(s.result)[:12]
        msg = str(s.msg)[:18] if s.msg else ""
        print(
            f"  {C.B}{user_col:<12}{C.R} {xu_tag:<14} "
            f"{stc}{stlabel:<9}{C.R} {s.job:<7} {tgt:<18} "
            f"{kq:<12} {s.done:>4} {s.miss:>3}  {msg}"
        )
    print(f"  {C.K}{'─' * 100}{C.R}")
    print(f"  {C.K}Delay/job {DELAY_MIN}-{DELAY_MAX}s  •  Workers đa luồng (sub/tim/cmt/vip){C.R}\n")

# ═══════════════════════ WORKER ═══════════════════════
def farm_one(sid, st: AccState, mode: str, worker_index: int = 0):
    global global_done, stop_all
    nick_id = st.id
    cycle = ["sub", "tim", "cmt", "vip"] if mode == "tonghop" else [mode]
    idx = 0

    # Stagger đa luồng — tránh rate-limit datnick
    if worker_index > 0:
        time.sleep(worker_index * 2.5)

    if not configure_account(sid, st):
        # thử lại 1 lần sau nghỉ
        time.sleep(5)
        if not configure_account(sid, st):
            with states_lock:
                st.status = "stopped"
                st.msg = "không cấu hình được nick"
            return

    while not stop_all and st.miss < MAX_MISS and global_done < global_target:
        job_key = cycle[idx % len(cycle)]
        idx += 1
        job = JOBS[job_key]

        with states_lock:
            st.job = job["name"]
            st.result = "lấy job"
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
                with states_lock:
                    st.status = "wait"
                    st.result = "chờ %ds" % min(cd, 60)
                    st.msg = "rate-limit panel"
                time.sleep(min(cd, 25) if mode == "tonghop" else min(cd, 45))
                with states_lock:
                    st.status = "running"
                continue
            # lỗi khác không phải countdown
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        if not tasks:
            with states_lock:
                st.result = "hết job"
                # không +miss — chỉ chuyển loại job / chờ
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        # Đã nhận nhiệm vụ → quyết hoàn thành, không miss oan
        batch = list(tasks)  # full getpost, xong hết mới get tiếp
        ok_ids = []
        done_tt = 0
        actor = None
        if HAS_TT:
            for boot in range(3):
                try:
                    actor = get_actor_for_account({
                        "id": st.id, "username": st.username,
                        "sessionid": st.sessionid, "user_field": st.user_field,
                    })
                    break
                except Exception as e:
                    with states_lock:
                        st.msg = ("TT boot: " + str(e))[:40]
                    time.sleep(2 + boot)

        for t in batch:
            idp = str(t.get("idpost") or t.get("id") or "")
            if not idp:
                continue
            with states_lock:
                st.target = str(t.get("link") or t.get("uid") or idp)[:22]
                st.result = "đang TT"

            success = False
            # Nhận job rồi: thử tới 6 lần trước khi bỏ
            for attempt in range(6):
                if not actor and HAS_TT:
                    try:
                        actor = get_actor_for_account({
                            "id": st.id, "username": st.username,
                            "sessionid": st.sessionid, "user_field": st.user_field,
                        })
                    except Exception:
                        time.sleep(2)
                        continue
                if not actor:
                    with states_lock:
                        st.result = "no TT sess"
                    break
                try:
                    ar = do_task_action(actor, job_key, t)
                    if ar.get("ok"):
                        success = True
                        done_tt += 1
                        with states_lock:
                            st.result = "TT:" + str(ar.get("action", "ok"))
                        break
                    reason = str(ar.get("reason") or "")
                    if reason == "login_expired":
                        with states_lock:
                            st.status = "stopped"
                            st.result = "SESSION DIE"
                            st.msg = "login_expired"
                            st.miss = MAX_MISS  # ép dừng acc
                        success = False
                        break
                    with states_lock:
                        st.result = "TT retry %d" % (attempt + 1)
                        st.msg = str(ar.get("error") or ar.get("raw", ""))[:36]
                except Exception as e:
                    with states_lock:
                        st.result = "TT err"
                        st.msg = str(e)[:36]
                    try:
                        actor.close()
                    except Exception:
                        pass
                    actor = None
                time.sleep(1.5 + attempt * 0.5)

            # --- Verify theo mode ---
            verified = success
            vdetail = ""
            if success and actor and HAS_TT:
                try:
                    if job_key in ("sub", "vip"):
                        uname = str(t.get("link") or t.get("username") or "").strip().lstrip("@")
                        if "/" in uname:
                            import re as _re
                            mm = _re.search(r"@([\w._]+)", uname)
                            uname = mm.group(1) if mm else uname
                        vr = actor.verify_follow(uname)
                        verified = bool(vr.get("followed"))
                        vdetail = str(vr.get("detail") or "")
                        with states_lock:
                            st.result = "ĐÃ FL" if verified else "CHƯA FL"
                            st.msg = vdetail[:28]
                    elif job_key == "tim":
                        vr = actor.verify_like(str(t.get("idpost") or ""))
                        verified = bool(vr.get("liked"))
                        vdetail = str(vr.get("detail") or "")
                        with states_lock:
                            st.result = "ĐÃ TIM" if verified else "CHƯA TIM"
                            st.msg = vdetail[:28]
                    elif job_key == "cmt":
                        with states_lock:
                            st.result = "ĐÃ CMT"
                            st.msg = "posted"
                        verified = True
                except Exception as ve:
                    with states_lock:
                        st.result = "check lỗi"
                        st.msg = str(ve)[:28]
                    verified = False

            if verified:
                ok_ids.append(idp)
                done_tt += 1
            else:
                with states_lock:
                    if st.result in ("đang TT", "TT retry"):
                        st.result = "CHƯA FL" if job_key in ("sub","vip") else "fail"
                    st.miss += 0  # không miss oan từng cái — đếm batch sau
            # nghỉ 5–10s mỗi nhiệm vụ
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        # xong FULL batch mới đóng actor + claim + getpost vòng sau
        with states_lock:
            st.msg = "xong batch %d/%d" % (len(ok_ids), len(batch))
            st.result = "batch xong"

        if actor:
            try:
                actor.close()
            except Exception:
                pass

        if not ok_ids:
            # Không +miss nếu chỉ là hết job/rate-limit tạm — chỉ +miss khi có task mà TT fail hết
            with states_lock:
                st.miss += 1
                st.result = "fail batch"
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            continue

        # Claim đúng id đã TT OK — retry claim nếu panel lỗi tạm
        claim_ok = False
        for ctry in range(3):
            claim = claim_tasks(sid, job_key, nick_id, ok_ids)
            if isinstance(claim, dict) and claim.get("error"):
                err = str(claim.get("error"))
                with states_lock:
                    st.msg = err[:36]
                    st.result = "cho claim"
                # điều kiện "làm trên N nhiệm vụ" không phải miss oan
                if "nhiệm vụ" in err or "nhan xu" in err.lower() or "đợi" in err.lower():
                    claim_ok = True  # đã làm TT, panel tự chặn nhận — không tính miss
                    break
                time.sleep(3)
                continue
            claim_ok = True
            break

        # Ước lượng / parse xu từ claim response
        gained = 0
        try:
            claim_data = claim if isinstance(claim, dict) else {}
            for k in ("xu", "sodu", "coin", "money", "gold"):
                if k in claim_data and str(claim_data[k]).replace(".","").isdigit():
                    # sodu là số dư — chỉ cộng xu nếu field xu
                    if k == "xu":
                        gained = int(float(claim_data[k]))
            raw = str(claim_data.get("_raw") or claim_data.get("mess") or claim_data.get("error") or "")
            m_xu = re.search(r"(\+|\b)(\d+)\s*xu", raw, re.I)
            if m_xu and not gained:
                gained = int(m_xu.group(2))
            if not gained and ok_ids:
                gained = len(ok_ids)  # fallback: +1 xu / job nếu panel không trả
        except Exception:
            gained = len(ok_ids)

        with states_lock:
            st.done += len(ok_ids)
            st.xu += gained
            st.status = "running"
            st.result = "OK %d job" % len(ok_ids)
            st.msg = "+%dxu (tổng %d)" % (gained, st.xu)
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
    if HAS_TT:
        log_info("TikTok engine: UC/SeleniumBase UI (delay %d–%ds/job)" % (DELAY_MIN, DELAY_MAX))
    else:
        log_warn("tiktok_actions không load — chỉ nhận job/claim panel")

    accounts = load_accounts()
    if not accounts:
        log_err("Không có acc – kiểm tra scripts/nicks.txt")
        return

    log_info("Kiểm tra session TikTok (passport) – cấm acc die...")
    accounts = filter_alive_accounts(accounts)
    if not accounts:
        log_err("Không còn acc nào sống – cập nhật cookie")
        return

    lines = [f"{C.G}✔{C.R}  {C.B}{len(accounts)}{C.R} acc SỐNG (đã lọc die)"]
    for a in accounts[:12]:
        lines.append(f"    {C.W}{a['username']:<16}{C.R} {C.K}{a['id'][:18]}{C.R}")
    if len(accounts) > 12:
        lines.append(f"    {C.K}... +{len(accounts)-12}{C.R}")
    box("ACC SẴN SÀNG", lines, width=60, color=C.C)
    print()

    box("CHỌN CHẾ ĐỘ", [
        f"  {C.C}1{C.R}. Sub          {C.C}2{C.R}. Tim (Like)",
        f"  {C.C}3{C.R}. Comment      {C.C}4{C.R}. Sub VIP",
        f"  {C.C}5{C.R}. {C.B}Tổng hợp{C.R} (sub → tim → cmt → vip)",
    ], width=60, color=C.M)

    # AUTO_* env để test không cần nhập
    auto_mode = os.getenv("AUTO_MODE", "").strip()
    auto_target = os.getenv("AUTO_TARGET", "").strip()
    auto_workers = os.getenv("AUTO_WORKERS", "").strip()

    if auto_mode:
        mode = auto_mode if auto_mode in ("sub", "tim", "cmt", "vip", "tonghop") else "sub"
        log_info(f"AUTO_MODE={mode}")
    else:
        choice = input(f"\n  {C.Y}› Chế độ [5] {C.R}").strip() or "5"
        mode_map = {"1": "sub", "2": "tim", "3": "cmt", "4": "vip", "5": "tonghop"}
        mode = mode_map.get(choice, "tonghop")

    if auto_target.isdigit():
        global_target = int(auto_target)
    else:
        t = input(f"  {C.Y}› Mục tiêu nhiệm vụ [{DEFAULT_TARGET}] {C.R}").strip()
        global_target = int(t) if t.isdigit() else DEFAULT_TARGET

    if auto_workers.isdigit():
        workers = int(auto_workers)
    else:
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
            futs = []
            for i, a in enumerate(accounts):
                futs.append(ex.submit(farm_one, sid, states[a["id"]], mode, i))
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
