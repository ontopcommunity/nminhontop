#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║                         O N T O P                            ║
║              MB Bank API Client (History + Balance)          ║
║         Nguồn: apimbbankvip.vercel.app / nminhontop          ║
╚══════════════════════════════════════════════════════════════╝

Chạy 1 dòng (không cần clone repo):
  python3 <(curl -fsSL https://raw.githubusercontent.com/ontopcommunity/nminhontop/main/scripts/mbbank_api.py)

Chỉ stdlib — không cần pip install.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

# ═══════════════════════ CONFIG ═══════════════════════
API_BASE = os.getenv("MB_API_URL", "https://apimbbankvip.vercel.app").rstrip("/")
API_PATH = "/api/aduanhminh"
DEFAULT_ROWS = int(os.getenv("MB_ROWS", "15"))
DEFAULT_DAYS = int(os.getenv("MB_DAYS", "30"))
POLL_SEC = int(os.getenv("MB_POLL_SEC", "30"))  # khuyến nghị ≥15–30s
TIMEOUT = int(os.getenv("MB_TIMEOUT", "90"))

# ANSI
R = "\033[0m"
B = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
GRN = "\033[92m"
YEL = "\033[93m"
BLU = "\033[94m"
CYN = "\033[96m"
WHT = "\033[97m"
MAG = "\033[95m"


def c(color: str, text: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{color}{text}{R}"


def banner() -> None:
    print(
        c(
            CYN,
            """
╔══════════════════════════════════════════════════════════════╗
║                         O N T O P                            ║
║              MB Bank API — Lịch sử & Số dư                   ║
╚══════════════════════════════════════════════════════════════╝
""",
        )
    )
    print(c(DIM, f"  API: {API_BASE}{API_PATH}"))
    print(c(DIM, f"  Time: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"))
    print()


def money(n: Any) -> str:
    try:
        v = int(float(str(n).replace(",", "").replace("đ", "").strip() or 0))
        return f"{v:,}".replace(",", ".") + "đ"
    except Exception:
        return str(n)


def http_get(url: str, timeout: int = TIMEOUT) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ONTOP-MBBank/1.0",
            "Cache-Control": "no-store",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        raw = res.read().decode("utf-8", errors="replace")
        return json.loads(raw)


def fetch_history(
    rows: int = DEFAULT_ROWS,
    days: int = DEFAULT_DAYS,
    account: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict[str, Any]:
    q: Dict[str, str] = {"rows": str(rows), "days": str(days)}
    if account:
        q["account"] = account
    if from_date:
        q["from"] = from_date
    if to_date:
        q["to"] = to_date
    url = f"{API_BASE}{API_PATH}?{urllib.parse.urlencode(q)}"
    return http_get(url)


def print_balance(data: Dict[str, Any]) -> None:
    bal = data.get("balance")
    print(c(B + WHT, "════════════════════"))
    print(c(B + GRN, f"  💰 Số dư hiện tại: {money(bal) if bal is not None else '—'}"))
    rng = data.get("range") or {}
    if rng:
        print(c(DIM, f"  📅 {rng.get('from', '?')} → {rng.get('to', '?')}  (days={rng.get('days', '?')})"))
    print(c(DIM, f"  src={data.get('src')}  total={data.get('total')}  notify={data.get('notify')}"))
    print(c(B + WHT, "════════════════════"))
    print()


def print_txs(data: Dict[str, Any]) -> None:
    txs: List[Dict[str, Any]] = data.get("transactions") or []
    if not txs:
        print(c(YEL, "  (Không có giao dịch)"))
        return
    for i, tx in enumerate(txs, 1):
        t = tx.get("type") or ""
        icon = "🟢" if t == "IN" else "🔴"
        col = GRN if t == "IN" else RED
        line1 = tx.get("line1") or f"{tx.get('amount', '')} | {tx.get('transactionDate', '')}"
        line2 = tx.get("line2") or tx.get("description") or ""
        line3 = tx.get("line3") or ""
        print(c(col, f"  {icon} {i}. {line1}"))
        if line2:
            print(c(DIM, f"     {line2[:100]}"))
        if line3:
            print(c(DIM, f"     {line3}"))
        print()


def action_once(rows: int = DEFAULT_ROWS, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
    print(c(CYN, f"  ⏳ Đang gọi API (rows={rows}, days={days})..."))
    t0 = time.time()
    try:
        data = fetch_history(rows=rows, days=days)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        print(c(RED, f"  ✖ HTTP {e.code}: {body}"))
        return {"status": "error", "msg": str(e)}
    except Exception as e:
        print(c(RED, f"  ✖ Lỗi: {e}"))
        return {"status": "error", "msg": str(e)}
    ms = int((time.time() - t0) * 1000)
    if data.get("status") != "success":
        print(c(RED, f"  ✖ {data.get('msg', 'fail')}"))
        return data
    print(c(GRN, f"  ✅ OK — {ms}ms"))
    print()
    print_balance(data)
    print_txs(data)
    return data


def action_poll(interval: int = POLL_SEC, rows: int = 10, days: int = 14) -> None:
    print(c(YEL, f"  🔁 Poll mỗi {interval}s (Ctrl+C dừng). Khuyến nghị ≥15–30s/lần."))
    print()
    n = 0
    while True:
        n += 1
        print(c(BLU, f"─── Lần #{n} · {datetime.now().strftime('%H:%M:%S')} ───"))
        data = action_once(rows=rows, days=days)
        noti = (data or {}).get("notify") or {}
        if noti.get("notified"):
            print(c(MAG, f"  🔔 Đã đẩy {noti.get('notified')} tin Zalo (new={noti.get('new_count')})"))
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            print(c(YEL, "\n  ⏹ Dừng poll."))
            break


def menu() -> None:
    banner()
    while True:
        print(c(B + CYN, "  MENU"))
        print("  1) Xem giao dịch mới nhất + số dư")
        print("  2) Xem 30 GD / 30 ngày")
        print("  3) Poll tự động (báo Zalo khi có GD mới)")
        print("  4) Tùy chỉnh rows / days")
        print("  0) Thoát")
        print()
        try:
            choice = input(c(WHT, "  Chọn > ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if choice == "0":
            print(c(DIM, "  Bye."))
            break
        if choice == "1":
            action_once(rows=15, days=14)
        elif choice == "2":
            action_once(rows=30, days=30)
        elif choice == "3":
            try:
                sec = input(c(DIM, f"  Interval giây [{POLL_SEC}]: ")).strip()
                interval = int(sec) if sec else POLL_SEC
            except ValueError:
                interval = POLL_SEC
            if interval < 10:
                print(c(YEL, "  ⚠ Interval < 10s dễ bị MB nghi — vẫn chạy theo yêu cầu."))
            action_poll(interval=interval)
        elif choice == "4":
            try:
                rows = int(input("  rows [15]: ").strip() or "15")
                days = int(input("  days [14]: ").strip() or "14")
            except ValueError:
                print(c(RED, "  Số không hợp lệ"))
                continue
            action_once(rows=rows, days=days)
        else:
            print(c(YEL, "  Không hợp lệ"))
        print()


def main(argv: List[str]) -> int:
    # CLI flags: --once --poll --rows N --days N --interval N
    rows = DEFAULT_ROWS
    days = DEFAULT_DAYS
    interval = POLL_SEC
    mode = "menu"
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(__doc__)
            print("Flags: --once | --poll | --rows N | --days N | --interval N | --url URL")
            return 0
        if a == "--once":
            mode = "once"
        elif a == "--poll":
            mode = "poll"
        elif a == "--rows" and i + 1 < len(argv):
            i += 1
            rows = int(argv[i])
        elif a == "--days" and i + 1 < len(argv):
            i += 1
            days = int(argv[i])
        elif a == "--interval" and i + 1 < len(argv):
            i += 1
            interval = int(argv[i])
        elif a == "--url" and i + 1 < len(argv):
            i += 1
            global API_BASE
            API_BASE = argv[i].rstrip("/")
        i += 1

    if mode == "once":
        banner()
        action_once(rows=rows, days=days)
        return 0
    if mode == "poll":
        banner()
        action_poll(interval=interval, rows=rows, days=days)
        return 0
    menu()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
