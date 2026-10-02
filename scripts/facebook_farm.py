#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONTOP — Facebook Job Farmer (TTC)
Dựa trên cơ chế tds-ttc-tool (cookie FB + GraphQL nội bộ + TTC panel)
"""
from __future__ import annotations

import os, re, sys, json, time, random, threading
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

import requests

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from FacebookAPI import FacebookAPI

# ═══════════════════════ CONFIG ═══════════════════════
BASE_URL     = os.getenv("TTC_BASE", "https://tuongtaccheo.com")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN", "cfb194b9dbd24ab7789b762e9e65d0ef")
SESSION_FILE = SCRIPT_DIR / "phpsessid.txt"
FB_ACC_FILE  = SCRIPT_DIR / "fb_accounts.json"

DELAY_MIN, DELAY_MAX = 15, 25   # nghỉ giữa job (repo gốc khuyến nghị >15s)
MAX_MISS     = 8
DEFAULT_TARGET = 100
WORKERS      = 2
CHANGE_ACC_AFTER = 8            # đổi acc sau N job thành công

# Nhiệm vụ Facebook trên TTC
JOBS = {
    "like":      {"name": "Like",      "path": "likepostvipcheo",  "group": "REACT"},
    "like2":     {"name": "Like2",     "path": "likepostvipre",    "group": "REACT"},
    "camxuc":    {"name": "CamXuc",    "path": "camxucvipcheo",    "group": "REACT"},
    "camxuc2":   {"name": "CamXuc2",   "path": "camxucvipre",      "group": "REACT"},
    "react_cmt": {"name": "ReactCMT",  "path": "camxuccheobinhluan","group": "REACT_CMT"},
    "cmt":       {"name": "Comment",   "path": "cmtcheo",          "group": "COMMENT"},
    "sub":       {"name": "Follow",    "path": "subcheo",          "group": "FOLLOW"},
    "subvip":    {"name": "FollowVIP", "path": "subcheofbvip",     "group": "FOLLOW"},
    "share":     {"name": "Share",     "path": "sharecheo",        "group": "SHARE"},
    "sharemsg":  {"name": "ShareMsg",  "path": "sharecheokemnoidung","group": "SHARE"},
    "likepage":  {"name": "LikePage",  "path": "likepagecheo",     "group": "LIKE_PAGE"},
    "join":      {"name": "JoinPage",  "path": "thamgianhomcheo",  "group": "JOIN_PAGE"},
    "rate":      {"name": "RatePage",  "path": "danhgiapage",      "group": "RATE_PAGE"},
}

# ═══════════════════════ COLORS ═══════════════════════
class C:
    R="\033[0m"; B="\033[1m"; G="\033[92m"; Y="\033[93m"
    E="\033[91m"; C="\033[96m"; M="\033[95m"; K="\033[90m"; W="\033[97m"

print_lock = threading.Lock()
states_lock = threading.Lock()
stop_all = False
global_done = 0
global_target = DEFAULT_TARGET

def log_ok(m):  print(f"  {C.G}✔{C.R}  {m}")
def log_info(m): print(f"  {C.C}●{C.R}  {m}")
def log_warn(m): print(f"  {C.Y}▲{C.R}  {m}")
def log_err(m):  print(f"  {C.E}✘{C.R}  {m}")

def banner():
    print(f"""{C.C}{C.B}
  ╔══════════════════════════════════════════════════════════╗
  ║   ██████╗ ███╗   ██╗████████╗ ██████╗ ██████╗            ║
  ║  ██╔═══██╗████╗  ██║╚══██╔══╝██╔═══██╗██╔══██╗           ║
  ║  ██║   ██║██╔██╗ ██║   ██║   ██║   ██║██████╔╝           ║
  ║  ██║   ██║██║╚██╗██║   ██║   ██║   ██║██╔═══╝            ║
  ║  ╚██████╔╝██║ ╚████║   ██║   ╚██████╔╝██║                ║
  ║   ╚═════╝ ╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝                ║
  ║          FACEBOOK JOB FARMER  •  TTC Panel               ║
  ╚══════════════════════════════════════════════════════════╝{C.R}
""")

# ═══════════════════════ TTC HTTP ═══════════════════════
def login_ttc(force=False) -> Optional[str]:
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

def ttc_headers():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{BASE_URL}/cauhinh/facebook.php",
    }

def ttc_get(sid, path, params=None):
    try:
        r = requests.get(f"{BASE_URL}{path}", params=params or {},
                         cookies={"PHPSESSID": sid}, headers=ttc_headers(), timeout=25)
        t = (r.text or "").strip()
        if t.isdigit():
            return {"_code": t}
        try:
            return r.json()
        except Exception:
            return {"_raw": t[:300]}
    except Exception as e:
        return {"_error": str(e)}

def ttc_post(sid, path, data=None):
    try:
        r = requests.post(f"{BASE_URL}{path}", data=data or {},
                          cookies={"PHPSESSID": sid}, headers=ttc_headers(), timeout=25)
        t = (r.text or "").strip()
        if t.isdigit():
            return {"_code": t}
        try:
            return r.json()
        except Exception:
            return {"_raw": t[:300]}
    except Exception as e:
        return {"_error": str(e)}

def datnick_fb(sid, uid: str, retries=5):
    for attempt in range(retries):
        # TTC Facebook dùng iddat[] + loai=fb
        r = ttc_post(sid, "/cauhinh/datnick.php", {"iddat[]": uid, "loai": "fb"})
        text = ""
        if isinstance(r, dict):
            text = str(r.get("_code") or r.get("_raw") or r.get("error") or r.get("mess") or "").strip()
        else:
            text = str(r or "").strip()
        low = text.lower()
        if any(k in low for k in ("chậm", "spam", "giây", "đợi")):
            time.sleep(3 + attempt * 2)
            continue
        # TTC: 1 = thành công (theo tds-ttc-tool)
        if text in ("1", "ok") or text == 1:
            return True, str(text)
        if text in ("2", "0") or text == 2:
            return False, f"datnick_code={text}"
        time.sleep(2)
    return False, text

def get_jobs(sid, job_key: str, nick_id: str):
    path = f"/kiemtien/{JOBS[job_key]['path']}/getpost.php"
    return ttc_get(sid, path, {"nickchay": nick_id})

def claim_job(sid, job_key: str, id_job: str, nick_id: str):
    path = f"/kiemtien/{JOBS[job_key]['path']}/nhantien.php"
    return ttc_post(sid, path, {"id": id_job, "nickchay": nick_id})

def parse_jobs(data) -> List[dict]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if data.get("_code") == "7":
            return []
        if isinstance(data.get("data"), list):
            return data["data"]
        if data.get("error"):
            return []
    return []

# ═══════════════════════ FB ACTION ═══════════════════════
def do_fb_job(fb: FacebookAPI, job_key: str, item: dict) -> dict:
    """Thực thi 1 nhiệm vụ Facebook — trả {ok, detail}."""
    group = JOBS[job_key]["group"]
    id_exec = str(item.get("idfb") or item.get("idpost") or item.get("id") or "")
    msg = str(item.get("msg") or item.get("nd") or item.get("message") or "Hay quá!")
    react = str(item.get("loaicx") or item.get("type") or "LIKE").upper()
    if react not in FacebookAPI.REACTION_IDS:
        react = "LIKE"

    try:
        if group == "REACT":
            ok = fb.reaction(id_exec, react)
            return {"ok": bool(ok), "detail": f"react:{react}"}
        if group == "REACT_CMT":
            ok = fb.reaction_comment(id_exec, react)
            return {"ok": bool(ok), "detail": f"react_cmt:{react}"}
        if group == "COMMENT":
            ok = fb.comment(id_exec, msg)
            return {"ok": bool(ok), "detail": "comment"}
        if group == "FOLLOW":
            ok = fb.follow(id_exec)
            return {"ok": bool(ok), "detail": "follow"}
        if group == "SHARE":
            if job_key == "sharemsg":
                ok = fb.share_with_message(id_exec, msg)
            else:
                ok = fb.share(id_exec)
            return {"ok": bool(ok), "detail": "share"}
        if group == "LIKE_PAGE":
            ok = fb.like_page(id_exec)
            return {"ok": bool(ok), "detail": "like_page"}
        if group == "JOIN_PAGE":
            ok = fb.join_page(id_exec)
            return {"ok": bool(ok), "detail": "join"}
        if group == "RATE_PAGE":
            ok = fb.rate_page(id_exec, msg, "POSITIVE")
            return {"ok": bool(ok), "detail": "rate"}
        return {"ok": False, "detail": "unknown_group"}
    except Exception as e:
        return {"ok": False, "detail": str(e)[:60]}

# ═══════════════════════ STATE ═══════════════════════
class AccState:
    def __init__(self, acc: dict):
        self.uid = acc["uid"]
        self.cookie = acc["cookie"]
        self.email = acc.get("email") or ""
        self.name = ""
        self.status = "idle"
        self.job = "-"
        self.target = "-"
        self.result = "-"
        self.done = 0
        self.miss = 0
        self.xu = 0
        self.msg = ""

states: Dict[str, AccState] = {}

def print_dashboard():
    with states_lock:
        rows = list(states.values())
        total_done = sum(s.done for s in rows)
        total_xu = sum(s.xu for s in rows)
        running = sum(1 for s in rows if s.status == "running")
        stopped = sum(1 for s in rows if s.status == "stopped")

    os.system("clear" if os.name != "nt" else "cls")
    banner()
    pct = min(100, int(total_done / global_target * 100)) if global_target else 0
    bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
    print(f"  Tiến độ [{C.G}{bar}{C.R}] {pct}%  {total_done}/{global_target}  Xu +{total_xu}")
    print(f"  {C.G}Running {running}{C.R}  {C.E}Stopped {stopped}{C.R}  {C.K}{datetime.now().strftime('%H:%M:%S')}  Delay {DELAY_MIN}-{DELAY_MAX}s{C.R}")
    print(f"  {C.B}{'UID':<16} {'TÊN':<14} {'STT':<10} {'JOB':<10} {'TARGET':<16} {'KQ':<10} {'DONE':>4} {'MISS':>4} {'XU':>5}{C.R}")
    print(f"  {C.K}{'─'*100}{C.R}")
    smap = {
        "running": (C.G, "ĐANG LÀM"), "stopped": (C.E, "DỪNG"),
        "done": (C.C, "XONG"), "idle": (C.K, "CHỜ"),
        "config": (C.M, "CẤU HÌNH"), "error": (C.E, "LỖI"), "wait": (C.Y, "CHỜ JOB"),
    }
    for s in rows:
        stc, stl = smap.get(s.status, (C.W, s.status[:8]))
        name = (s.name or s.email or s.uid)[:13]
        print(f"  {s.uid:<16} {name:<14} {stc}{stl:<10}{C.R} {s.job:<10} {str(s.target)[:15]:<16} {str(s.result)[:9]:<10} {s.done:>4} {s.miss:>4} {s.xu:>5}")
    print()

# ═══════════════════════ WORKER ═══════════════════════
def farm_one(sid: str, st: AccState, modes: List[str], worker_index: int = 0):
    global global_done, stop_all
    if worker_index:
        time.sleep(worker_index * 2)

    # Login FB
    with states_lock:
        st.status = "config"
        st.result = "login FB"
    try:
        fb = FacebookAPI(st.cookie)
        info = fb.info() or {}
        st.name = str(info.get("name") or info.get("id") or "")[:20]
        if not info.get("id") and not info.get("name"):
            with states_lock:
                st.status = "stopped"
                st.result = "FB die"
                st.msg = str(info)[:40]
            log_err(f"@{st.uid} cookie die / không login được")
            return
        log_ok(f"FB {st.uid} → {st.name}")
    except Exception as e:
        with states_lock:
            st.status = "stopped"
            st.result = "FB err"
            st.msg = str(e)[:40]
        log_err(f"@{st.uid} {e}")
        return

    # datnick panel
    ok, detail = datnick_fb(sid, st.uid)
    with states_lock:
        if not ok:
            st.status = "stopped"
            st.result = "datnick fail"
            st.msg = str(detail)[:40]
            log_err(f"datnick {st.uid}: {detail}")
            return
        st.status = "running"
        st.msg = f"datnick={detail}"
    log_ok(f"datnick {st.uid} OK ({detail})")

    mode_idx = 0
    while not stop_all and st.miss < MAX_MISS and global_done < global_target:
        job_key = modes[mode_idx % len(modes)]
        mode_idx += 1
        with states_lock:
            st.job = JOBS[job_key]["name"]
            st.result = "lấy job"
            st.target = "-"

        data = get_jobs(sid, job_key, st.uid)
        if isinstance(data, dict) and data.get("error"):
            err = str(data.get("error") or "")
            cd = int(data.get("countdown") or 0)
            with states_lock:
                st.status = "wait"
                st.result = f"chờ {min(cd,60)}s" if cd else "hết job"
                st.msg = err[:36]
            if cd > 0:
                time.sleep(min(cd, 40))
            else:
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            with states_lock:
                st.status = "running"
            continue

        jobs = parse_jobs(data)
        if not jobs:
            with states_lock:
                st.result = "hết job"
            time.sleep(random.uniform(5, 12))
            continue

        # Full batch từ 1 lần getpost
        for item in jobs:
            if stop_all or global_done >= global_target or st.miss >= MAX_MISS:
                break
            id_job = str(item.get("idpost") or item.get("id") or "")
            id_exec = str(item.get("idfb") or item.get("idpost") or "")
            with states_lock:
                st.target = id_exec[:15]
                st.result = "đang FB"

            res = do_fb_job(fb, job_key, item)
            if not res.get("ok"):
                with states_lock:
                    st.result = "FAIL"
                    st.msg = str(res.get("detail"))[:36]
                    st.miss += 1
                log_warn(f"{st.uid} FAIL {job_key} {id_exec}: {res.get('detail')}")
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                continue

            # claim
            time.sleep(1)
            claim = claim_job(sid, job_key, id_job, st.uid)
            gained = 0
            claim_ok = True
            if isinstance(claim, dict) and claim.get("error"):
                err = str(claim.get("error"))
                with states_lock:
                    st.msg = err[:36]
                    st.result = "chờ claim"
                if "nhiệm vụ" in err or "đợi" in err.lower():
                    claim_ok = True
                else:
                    claim_ok = False
                # parse xu
            if isinstance(claim, dict):
                for k in ("xu", "sodu"):
                    if k in claim and str(claim[k]).replace(".", "").isdigit():
                        if k == "xu":
                            gained = int(float(claim[k]))
                raw = str(claim.get("mess") or claim.get("_raw") or "")
                m = re.search(r"(\d+)\s*xu", raw, re.I)
                if m and not gained:
                    gained = int(m.group(1))
            if not gained:
                gained = 1

            with states_lock:
                if claim_ok:
                    st.done += 1
                    st.xu += gained
                    st.miss = 0
                    st.result = "OK"
                    st.msg = f"+{gained}xu"
                    global_done += 1
                else:
                    st.miss += 1
                    st.result = "claim fail"

            log_ok(f"{st.uid} {JOBS[job_key]['name']} {id_exec[:12]} → +{gained}xu (tổng {st.xu})")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

    with states_lock:
        st.status = "stopped" if st.miss >= MAX_MISS else "done"

# ═══════════════════════ LOAD ACC ═══════════════════════
def load_fb_accounts() -> List[dict]:
    if not FB_ACC_FILE.exists():
        return []
    data = json.loads(FB_ACC_FILE.read_text(encoding="utf-8"))
    return [a for a in data if a.get("cookie") and a.get("uid")]

# ═══════════════════════ MAIN ═══════════════════════
def main():
    global global_target, stop_all, global_done, states

    banner()
    sid = login_ttc(force=True)
    if not sid:
        log_err("Login TTC thất bại — kiểm tra ACCESS_TOKEN")
        return
    log_ok(f"TTC session {sid[:18]}...")

    accounts = load_fb_accounts()
    if not accounts:
        log_err(f"Không có acc — thêm vào {FB_ACC_FILE}")
        return
    log_info(f"Có {len(accounts)} acc Facebook")

    # Chọn nhiệm vụ
    print(f"\n  {C.B}Chọn nhiệm vụ:{C.R}")
    keys = list(JOBS.keys())
    for i, k in enumerate(keys, 1):
        print(f"    {C.C}{i:2}{C.R}. {JOBS[k]['name']:<12} ({k})")
    print(f"    {C.C}0{C.R}. Tổng hợp (like + follow + cmt)")

    auto_mode = os.getenv("AUTO_MODE", "").strip()
    auto_target = os.getenv("AUTO_TARGET", "").strip()
    auto_workers = os.getenv("AUTO_WORKERS", "").strip()

    if auto_mode:
        if auto_mode == "tonghop":
            modes = ["like", "sub", "cmt"]
        elif auto_mode in JOBS:
            modes = [auto_mode]
        else:
            modes = ["like"]
        log_info(f"AUTO_MODE={modes}")
    else:
        choice = input(f"\n  {C.Y}› Chọn [0] {C.R}").strip() or "0"
        if choice == "0":
            modes = ["like", "sub", "cmt"]
        else:
            idxs = [int(x) - 1 for x in choice.split() if x.isdigit()]
            modes = [keys[i] for i in idxs if 0 <= i < len(keys)] or ["like"]

    if auto_target.isdigit():
        global_target = int(auto_target)
    else:
        t = input(f"  {C.Y}› Mục tiêu job [{DEFAULT_TARGET}] {C.R}").strip()
        global_target = int(t) if t.isdigit() else DEFAULT_TARGET

    if auto_workers.isdigit():
        workers = int(auto_workers)
    else:
        w = input(f"  {C.Y}› Số acc song song [{min(WORKERS, len(accounts))}] {C.R}").strip()
        workers = int(w) if w.isdigit() else min(WORKERS, len(accounts))
    workers = max(1, min(workers, len(accounts)))

    states = {a["uid"]: AccState(a) for a in accounts}
    global_done = 0
    stop_all = False

    log_info(f"Mode={modes} Target={global_target} Workers={workers}")
    time.sleep(1)

    def ui_loop():
        while not stop_all and global_done < global_target:
            if not any(s.status == "running" for s in states.values()) and global_done > 0:
                time.sleep(2)
                if not any(s.status in ("running", "config", "wait") for s in states.values()):
                    break
            print_dashboard()
            time.sleep(3)
        print_dashboard()

    ui_t = threading.Thread(target=ui_loop, daemon=True)
    ui_t.start()

    try:
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(farm_one, sid, states[a["uid"]], modes, i)
                    for i, a in enumerate(accounts)]
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception as e:
                    log_err(f"Worker: {e}")
    except KeyboardInterrupt:
        stop_all = True
        log_warn("Đang dừng...")

    stop_all = True
    time.sleep(1)
    print_dashboard()
    print(f"\n  {C.B}KẾT THÚC{C.R}  done={global_done}/{global_target}\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {C.Y}Đã dừng.{C.R}\n")
