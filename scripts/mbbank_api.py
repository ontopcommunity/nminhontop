#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ONTOP · MB Bank VIP Client
Chạy: curl -fsSL https://raw.githubusercontent.com/ontopcommunity/nminhontop/main/scripts/mbbank_api.py | python3 -
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
POLL_SEC = int(os.getenv("MB_POLL_SEC", "30"))
TIMEOUT = int(os.getenv("MB_TIMEOUT", "90"))

# ── ANSI palette ──
class C:
    R = "\033[0m"
    B = "\033[1m"
    D = "\033[2m"
    I = "\033[3m"
    U = "\033[4m"
    # fg
    BLK = "\033[30m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YEL = "\033[93m"
    BLU = "\033[94m"
    MAG = "\033[95m"
    CYN = "\033[96m"
    WHT = "\033[97m"
    # bright / 256
    GOLD = "\033[38;5;220m"
    ORNG = "\033[38;5;208m"
    PINK = "\033[38;5;213m"
    LIME = "\033[38;5;118m"
    SKY = "\033[38;5;39m"
    PURP = "\033[38;5;141m"
    TEAL = "\033[38;5;44m"
    GRAY = "\033[38;5;245m"
    # bg
    BG_D = "\033[48;5;234m"
    BG_P = "\033[48;5;54m"
    BG_G = "\033[48;5;22m"
    BG_R = "\033[48;5;52m"


def use_color() -> bool:
    return sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def t(code: str, s: str) -> str:
    if not use_color():
        return s
    return f"{code}{s}{C.R}"


def gradient_line(text: str, colors: List[str]) -> str:
    if not use_color() or not colors:
        return text
    out = []
    n = max(len(colors), 1)
    for i, ch in enumerate(text):
        out.append(f"{colors[i % n]}{ch}")
    return "".join(out) + C.R


def box(title: str, lines: List[str], color: str = C.CYN, width: int = 62) -> None:
    top = "╔" + "═" * width + "╗"
    mid = "╠" + "═" * width + "╣"
    bot = "╚" + "═" * width + "╝"
    print(t(color + C.B, top))
    # title centered
    pad = max(0, width - len(title))
    left = pad // 2
    right = pad - left
    print(t(color + C.B, "║") + t(C.GOLD + C.B, " " * left + title + " " * right) + t(color + C.B, "║"))
    print(t(color + C.B, mid))
    for line in lines:
        # strip ansi for length calc
        plain = line
        for code in (C.R, C.B, C.D, C.I, C.GOLD, C.ORNG, C.PINK, C.LIME, C.SKY, C.PURP, C.TEAL, C.GRAY, C.RED, C.GRN, C.YEL, C.BLU, C.MAG, C.CYN, C.WHT, C.BG_D, C.BG_P, C.BG_G, C.BG_R):
            plain = plain.replace(code, "")
        plain = plain.replace("\033[0m", "")
        # rough visible len
        vis = 0
        i = 0
        while i < len(line):
            if line[i] == "\033":
                while i < len(line) and line[i] != "m":
                    i += 1
                i += 1
                continue
            vis += 1
            i += 1
        space = max(0, width - vis)
        print(t(color, "║") + line + " " * space + t(color, "║"))
    print(t(color + C.B, bot))


def banner() -> None:
    w = 62
    print()
    colors = [C.GOLD, C.ORNG, C.PINK, C.PURP, C.SKY, C.TEAL]
    print(gradient_line("  ████████╗ ███╗   ██╗ ████████╗  ██████╗  ██████╗ ", colors))
    print(gradient_line("  ██╔═══██║ ████╗  ██║ ╚══██╔══╝ ██╔═══██╗ ██╔══██╗", colors))
    print(gradient_line("  ██║   ██║ ██╔██╗ ██║    ██║    ██║   ██║ ██████╔╝", colors))
    print(gradient_line("  ██║   ██║ ██║╚██╗██║    ██║    ██║   ██║ ██╔═══╝ ", colors))
    print(gradient_line("  ████████║ ██║ ╚████║    ██║    ╚██████╔╝ ██║     ", colors))
    print(gradient_line("  ╚═══════╝ ╚═╝  ╚═══╝    ╚═╝     ╚═════╝  ╚═╝     ", colors))
    print()
    box(
        "✦ MB BANK VIP CLIENT ✦",
        [
            t(C.D, "  Realtime history · Balance · Zalo auto-notify"),
            t(C.TEAL, f"  API  ") + t(C.WHT, API_BASE + API_PATH),
            t(C.TEAL, f"  Time ") + t(C.WHT, datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
            t(C.GOLD, "  Status ") + t(C.LIME + C.B, "● ONLINE"),
        ],
        color=C.PURP,
        width=w,
    )
    print()


def money(n: Any) -> str:
    try:
        v = int(float(str(n).replace(",", "").replace("đ", "").strip() or 0))
        return f"{v:,}".replace(",", ".") + "đ"
    except Exception:
        return str(n)


def spinner_wait(msg: str, seconds: float = 0.0) -> None:
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    if not use_color():
        print(f"  {msg}")
        return
    end = time.time() + max(seconds, 0.15)
    i = 0
    while time.time() < end:
        sys.stdout.write(f"\r  {t(C.CYN, frames[i % len(frames)])} {t(C.WHT, msg)}   ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * 70 + "\r")
    sys.stdout.flush()


def http_get(url: str, timeout: int = TIMEOUT) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ONTOP-MBBank-VIP/2.0",
            "Cache-Control": "no-store",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return json.loads(res.read().decode("utf-8", errors="replace"))


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


def print_balance_card(data: Dict[str, Any], ms: int = 0) -> None:
    bal = data.get("balance")
    rng = data.get("range") or {}
    noti = data.get("notify") or {}
    lines = [
        t(C.GOLD + C.B, "  💰  SỐ DƯ HIỆN TẠI"),
        t(C.LIME + C.B, f"      {money(bal) if bal is not None else '—'}"),
        "",
        t(C.SKY, "  📅  ")
        + t(C.WHT, f"{rng.get('from', '?')} → {rng.get('to', '?')}")
        + t(C.GRAY, f"  ·  {rng.get('days', '?')} ngày"),
        t(C.SKY, "  ⚡  ")
        + t(C.WHT, f"src={data.get('src')}  total={data.get('total')}")
        + (t(C.GRAY, f"  ·  {ms}ms") if ms else ""),
        t(C.PINK, "  🔔  ")
        + t(
            C.WHT,
            f"notify={noti.get('notified', 0)}  new={noti.get('new_count', noti.get('notified', 0))}",
        ),
    ]
    box("◆ WALLET ◆", lines, color=C.GOLD, width=62)


def print_txs(data: Dict[str, Any]) -> None:
    txs: List[Dict[str, Any]] = data.get("transactions") or []
    print()
    print(t(C.PURP + C.B, "  ┌─ GIAO DỊCH ─────────────────────────────────────────┐"))
    if not txs:
        print(t(C.YEL, "  │  (Trống — không có giao dịch trong khoảng này)      │"))
        print(t(C.PURP + C.B, "  └──────────────────────────────────────────────────────┘"))
        return
    for i, tx in enumerate(txs, 1):
        typ = tx.get("type") or ""
        is_in = typ == "IN"
        icon = "🟢 IN " if is_in else "🔴 OUT"
        col = C.LIME if is_in else C.ORNG
        bar = C.BG_G if is_in else C.BG_R
        line1 = tx.get("line1") or f"{tx.get('amount', '')} | {tx.get('transactionDate', '')}"
        line2 = (tx.get("line2") or tx.get("description") or "")[:72]
        line3 = tx.get("line3") or ""
        print(t(col + C.B, f"  │ {icon}  #{i}"))
        print(t(C.WHT, f"  │   {line1}"))
        if line2:
            print(t(C.GRAY, f"  │   {line2}"))
        if line3:
            print(t(C.TEAL, f"  │   {line3}"))
        if i < len(txs):
            print(t(C.D + C.PURP, "  │ · · · · · · · · · · · · · · · · · · · · · · · · · · · ·"))
    print(t(C.PURP + C.B, "  └──────────────────────────────────────────────────────┘"))
    print()


def action_once(rows: int = DEFAULT_ROWS, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
    spinner_wait(f"Đang kết nối MB API · rows={rows} days={days}", 0.4)
    t0 = time.time()
    try:
        data = fetch_history(rows=rows, days=days)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        print(t(C.RED + C.B, f"  ✖ HTTP {e.code}"))
        print(t(C.GRAY, f"    {body}"))
        return {"status": "error", "msg": str(e)}
    except Exception as e:
        print(t(C.RED + C.B, f"  ✖ Lỗi: {e}"))
        return {"status": "error", "msg": str(e)}
    ms = int((time.time() - t0) * 1000)
    if data.get("status") != "success":
        print(t(C.RED + C.B, f"  ✖ {data.get('msg', 'fail')}"))
        return data
    print(t(C.LIME + C.B, f"  ✔  SUCCESS") + t(C.GRAY, f"  ·  {ms} ms"))
    print()
    print_balance_card(data, ms)
    print_txs(data)
    return data


def action_poll(interval: int = POLL_SEC, rows: int = 10, days: int = 14) -> None:
    print(t(C.YEL + C.B, f"  ⟳  LIVE POLL"))
    print(t(C.GRAY, f"     mỗi {interval}s · Ctrl+C để dừng · khuyến nghị ≥15–30s"))
    print()
    n = 0
    while True:
        n += 1
        stamp = datetime.now().strftime("%H:%M:%S")
        print(t(C.SKY + C.B, f"  ─── #{n}  {stamp} ───────────────────────────"))
        data = action_once(rows=rows, days=days)
        noti = (data or {}).get("notify") or {}
        if noti.get("notified"):
            print(
                t(C.PINK + C.B, f"  🔔  Đã đẩy {noti.get('notified')} tin Zalo")
                + t(C.GRAY, f"  (new={noti.get('new_count')})")
            )
        try:
            # countdown
            for left in range(interval, 0, -1):
                sys.stdout.write(
                    f"\r  {t(C.D, '⏳ next in')} {t(C.CYN + C.B, str(left).rjust(3))}s   "
                )
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write("\r" + " " * 40 + "\r")
        except KeyboardInterrupt:
            print(t(C.YEL, "\n  ⏹  Dừng poll. Hẹn gặp lại."))
            break


def menu() -> None:
    banner()
    while True:
        box(
            "◆ MENU VIP ◆",
            [
                t(C.LIME + C.B, "  [1]") + t(C.WHT, "  Xem GD mới nhất + số dư"),
                t(C.SKY + C.B, "  [2]") + t(C.WHT, "  Xem 30 GD / 30 ngày"),
                t(C.PINK + C.B, "  [3]") + t(C.WHT, "  Live poll (auto Zalo notify)"),
                t(C.GOLD + C.B, "  [4]") + t(C.WHT, "  Tùy chỉnh rows / days"),
                t(C.GRAY + C.B, "  [0]") + t(C.GRAY, "  Thoát"),
            ],
            color=C.TEAL,
            width=62,
        )
        print()
        try:
            choice = input(t(C.GOLD + C.B, "  ❯ ") + t(C.WHT, "Chọn lệnh: ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            print(t(C.GRAY, "  Bye 👋"))
            break
        print()
        if choice == "0":
            print(t(C.PURP, "  ✨ ONTOP out. Good luck."))
            break
        if choice == "1":
            action_once(rows=15, days=14)
        elif choice == "2":
            action_once(rows=30, days=30)
        elif choice == "3":
            try:
                sec = input(t(C.D, f"  Interval giây [{POLL_SEC}]: ")).strip()
                interval = int(sec) if sec else POLL_SEC
            except ValueError:
                interval = POLL_SEC
            if interval < 10:
                print(t(C.YEL, "  ⚠  <10s dễ bị MB nghi — vẫn chạy theo bạn."))
            action_poll(interval=interval)
        elif choice == "4":
            try:
                rows = int(input(t(C.D, "  rows [15]: ")).strip() or "15")
                days = int(input(t(C.D, "  days [14]: ")).strip() or "14")
            except ValueError:
                print(t(C.RED, "  Số không hợp lệ"))
                continue
            action_once(rows=rows, days=days)
        else:
            print(t(C.YEL, "  Lệnh không hợp lệ — chọn 0–4"))
        print()


def main(argv: List[str]) -> int:
    global API_BASE
    rows = DEFAULT_ROWS
    days = DEFAULT_DAYS
    interval = POLL_SEC
    mode = "menu"
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(__doc__)
            print("  --once | --poll | --rows N | --days N | --interval N | --url URL")
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
