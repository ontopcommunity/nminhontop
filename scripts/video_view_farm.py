#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONTOP – Xem video đa luồng (TTC API cải tiến)
API: https://video-api-pied.vercel.app/api/video?url={secret}&limit={n}
Response: [{"id":1,"url":"..."}, ...]
"""

from __future__ import annotations
import os, sys, time, json, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote, urlencode
import threading

try:
    import requests
except ImportError:
    os.system(f"{sys.executable} -m pip install requests -q")
    import requests

VIDEO_API = os.getenv("VIDEO_API", "https://video-api-pied.vercel.app/api/video")
TTC_BASE = os.getenv("TTC_BASE", "https://tuongtaccheo.com")
TTC_TOKEN = os.getenv("TTC_TOKEN", "cfb194b9dbd24ab7789b762e9e65d0ef")

# Tốc độ bàn thờ
DEFAULT_WORKERS = int(os.getenv("VIEW_WORKERS", "50"))
DEFAULT_TIMEOUT = float(os.getenv("VIEW_TIMEOUT", "8"))

_print_lock = threading.Lock()
_stats = {"ok": 0, "fail": 0, "done": 0}


def cprint(msg: str):
    with _print_lock:
        print(msg, flush=True)


def fetch_tasks(secret_url: str, limit: int) -> list:
    """Lấy mảng nhiệm vụ [{id, url}, ...] từ API."""
    r = requests.get(
        VIDEO_API,
        params={"url": secret_url, "limit": int(limit)},
        headers={"User-Agent": "ONTOP-VideoFarm/1.0", "Accept": "application/json"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list):
        raise RuntimeError(f"API không trả list: {str(data)[:200]}")
    return data


def view_one(item: dict, session: requests.Session) -> dict:
    """
    Xem 1 video theo id.
    - GET url (và thử kèm id nếu server hỗ trợ)
    - Ghi nhận status
    """
    vid = item.get("id")
    url = (item.get("url") or "").strip()
    if not url:
        _stats["fail"] += 1
        _stats["done"] += 1
        return {"id": vid, "ok": False, "error": "empty_url"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "*/*",
        "Referer": TTC_BASE + "/",
    }
    # Ưu tiên gọi url kèm query id (nhiều panel dùng ?id=)
    candidates = []
    if "id=" not in url and str(vid) not in url:
        sep = "&" if "?" in url else "?"
        candidates.append(f"{url}{sep}id={vid}")
        candidates.append(f"{url}{sep}idpost={vid}")
    candidates.append(url)

    last_err = None
    for target in candidates:
        try:
            resp = session.get(target, headers=headers, timeout=DEFAULT_TIMEOUT, allow_redirects=True)
            ok = resp.status_code < 500
            _stats["done"] += 1
            if ok:
                _stats["ok"] += 1
                return {
                    "id": vid,
                    "ok": True,
                    "status": resp.status_code,
                    "len": len(resp.content or b""),
                    "url": target[:80],
                }
            last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = str(e)[:60]

    _stats["fail"] += 1
    _stats["done"] += 1
    return {"id": vid, "ok": False, "error": last_err}


def run_views(tasks: list, workers: int = DEFAULT_WORKERS) -> list:
    """Đa luồng xem toàn bộ id – tốc độ cao."""
    workers = max(1, min(int(workers), 200))
    results = []
    total = len(tasks)
    t0 = time.time()
    cprint(f"  ▶ Bắt đầu xem {total} video | workers={workers}")

    with requests.Session() as session:
        # mỗi thread dùng session riêng an toàn hơn
        def _job(item):
            s = requests.Session()
            return view_one(item, s)

        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_job, it): it for it in tasks}
            for i, fut in enumerate(as_completed(futs), 1):
                try:
                    res = fut.result()
                except Exception as e:
                    res = {"ok": False, "error": str(e)[:60]}
                    _stats["fail"] += 1
                    _stats["done"] += 1
                results.append(res)
                if i % 10 == 0 or i == total:
                    elapsed = time.time() - t0
                    speed = i / elapsed if elapsed > 0 else 0
                    cprint(
                        f"  … {i}/{total}  OK={_stats['ok']} FAIL={_stats['fail']}  "
                        f"{speed:.1f} req/s  {elapsed:.1f}s"
                    )
    elapsed = time.time() - t0
    cprint(f"  ✔ Xong xem: OK={_stats['ok']} FAIL={_stats['fail']} trong {elapsed:.1f}s")
    return results


def ttc_login(token: str = TTC_TOKEN) -> str | None:
    try:
        r = requests.post(
            f"{TTC_BASE}/logintoken.php",
            data={"access_token": token},
            headers={"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"},
            timeout=20,
        )
        return r.cookies.get("PHPSESSID")
    except Exception:
        return None


def ttc_claim_video(sid: str, ids: list, nick_id: str = "") -> str:
    """Thử nhận xu sau khi xem (các path phổ biến TTC)."""
    if not sid or not ids:
        return "skip"
    cookies = {"PHPSESSID": sid}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": TTC_BASE + "/",
    }
    id_str = ",".join(str(x) for x in ids[:100])  # batch
    paths = [
        "/tiktok/kiemtien/xemvideo/nhantien.php",
        "/tiktok/kiemtien/nhantien.php",
        "/tiktok/kiemtien/nhantatca.php",
    ]
    for path in paths:
        try:
            data = {"id": id_str, "idpost": id_str}
            if nick_id:
                data["nickchay"] = nick_id
            r = requests.post(
                TTC_BASE + path,
                data=data,
                headers=headers,
                cookies=cookies,
                timeout=20,
            )
            if r.status_code == 200 and r.text and "404" not in r.text[:80]:
                return f"{path} → {r.text[:180]}"
        except Exception as e:
            continue
    return "claim: no endpoint matched"


def main():
    ap = argparse.ArgumentParser(description="ONTOP Video View Farm – đa luồng")
    ap.add_argument("--url", required=True, help="URL bí mật truyền vào API video")
    ap.add_argument("--limit", type=int, default=100, help="Số lượng nhiệm vụ")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Số luồng song song")
    ap.add_argument("--claim", action="store_true", help="Thử nhận xu TTC sau khi xem")
    ap.add_argument("--nick", default="", help="nickchay ID (nếu claim)")
    ap.add_argument("--token", default=TTC_TOKEN, help="TTC access_token")
    args = ap.parse_args()

    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║   ONTOP VIDEO VIEW  ·  MULTI-THREAD  ║")
    print("  ╚══════════════════════════════════════╝")
    print(f"  API   : {VIDEO_API}")
    print(f"  limit : {args.limit}  workers: {args.workers}")
    print()

    # 1) Lấy list nhiệm vụ
    print("  [1] Gọi API lấy danh sách id...")
    tasks = fetch_tasks(args.url, args.limit)
    print(f"  ✔ Nhận {len(tasks)} item  (mẫu: {tasks[0] if tasks else '—'})")

    if not tasks:
        print("  Không có nhiệm vụ.")
        return

    # 2) Xem đa luồng
    print("  [2] Xem video đa luồng...")
    results = run_views(tasks, workers=args.workers)
    ok_ids = [r["id"] for r in results if r.get("ok") and r.get("id") is not None]

    # 3) Claim (tuỳ chọn)
    if args.claim and ok_ids:
        print("  [3] Nhận xu TTC...")
        sid = ttc_login(args.token)
        if sid:
            print(f"  Session OK  {sid[:18]}...")
            msg = ttc_claim_video(sid, ok_ids, nick_id=args.nick)
            print(f"  Claim: {msg}")
        else:
            print("  Login TTC thất bại – bỏ claim")

    print()
    print(f"  KẾT QUẢ: xem OK {len(ok_ids)}/{len(tasks)}")
    print()


if __name__ == "__main__":
    main()
