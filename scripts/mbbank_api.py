#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MB BANK · VIP Terminal Client
Repo gốc tham khảo: https://github.com/thedtvn/MBBank (mbbank-lib)
API host: https://apimbbankvip.vercel.app

Chạy 1 dòng:
  curl -fsSL https://raw.githubusercontent.com/ontopcommunity/nminhontop/main/scripts/mbbank_api.py | python3 -

  curl -fsSL ... | python3 - --once
  curl -fsSL ... | python3 - --poll --interval 30
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
from typing import Any, Dict, List, Optional, Tuple

# ═══════════════════════ CONFIG ═══════════════════════
API_BASE = os.getenv("MB_API_URL", "https://apimbbankvip.vercel.app").rstrip("/")
API_PATH = "/api/aduanhminh"
DEFAULT_ROWS = int(os.getenv("MB_ROWS", "15"))
DEFAULT_DAYS = int(os.getenv("MB_DAYS", "30"))
POLL_SEC = int(os.getenv("MB_POLL_SEC", "30"))
TIMEOUT = int(os.getenv("MB_TIMEOUT", "90"))

# ── Colors ──
class C:
    R = "\033[0m"
    B = "\033[1m"
    D = "\033[2m"
    # MB BANK brand — xanh dương đậm
    MB = "\033[38;5;20m"       # deep blue
    MB2 = "\033[38;5;27m"      # royal blue
    MB3 = "\033[1;38;5;21m"    # bold deep blue
    # rainbow border cycle
    RB = [
        "\033[38;5;196m",  # red
        "\033[38;5;208m",  # orange
        "\033[38;5;226m",  # yellow
        "\033[38;5;46m",   # green
        "\033[38;5;51m",   # cyan
        "\033[38;5;39m",   # blue
        "\033[38;5;129m",  # purple
        "\033[38;5;201m",  # magenta
    ]
    GRN = "\033[92m"
    RED = "\033[91m"
    YEL = "\033[93m"
    WHT = "\033[97m"
    GRAY = "\033[38;5;245m"
    LIME = "\033[38;5;118m"
    GOLD = "\033[38;5;220m"
    SKY = "\033[38;5;45m"
    TEAL = "\033[38;5;44m"
    ORNG = "\033[38;5;208m"
    PINK = "\033[38;5;213m"


def color_ok() -> bool:
    return sys.stdout.isatty() and os.getenv("NO_COLOR") is None


def t(code: str, s: str) -> str:
    return f"{code}{s}{C.R}" if color_ok() else s


def rb_char(i: int, ch: str) -> str:
    if not color_ok():
        return ch
    return f"{C.RB[i % len(C.RB)]}{ch}{C.R}"


def rainbow_str(s: str, start: int = 0) -> str:
    if not color_ok():
        return s
    return "".join(rb_char(start + i, ch) for i, ch in enumerate(s))


def rainbow_line(width: int, left: str, fill: str, right: str, offset: int = 0) -> str:
    """Build a full horizontal line with rainbow coloring."""
    inner = fill * width
    body = left + inner + right
    return rainbow_str(body, offset)


def box_rainbow(title: str, lines: List[str], width: int = 64) -> None:
    """Box with rainbow border; title in deep MB blue."""
    # top
    print(rainbow_line(width, "╔", "═", "╗", 0))
    # title row — deep blue text, rainbow corners already in line concept
    plain_title = title
    pad = max(0, width - len(plain_title))
    left, right = pad // 2, pad - pad // 2
    title_row = (
        rb_char(1, "║")
        + t(C.MB3, " " * left + plain_title + " " * right)
        + rb_char(3, "║")
    )
    print(title_row)
    print(rainbow_line(width, "╠", "═", "╣", 2))
    for line in lines:
        # visible length without ansi
        vis = _vis_len(line)
        space = max(0, width - vis)
        print(rb_char(4, "║") + line + " " * space + rb_char(6, "║"))
    print(rainbow_line(width, "╚", "═", "╝", 4))


def _vis_len(s: str) -> int:
    n, i = 0, 0
    while i < len(s):
        if s[i] == "\033":
            while i < len(s) and s[i] != "m":
                i += 1
            i += 1
            continue
        n += 1
        i += 1
    return n


def banner() -> None:
    w = 64
    print()
    # Big MB BANK in deep blue
    logo = [
        r"  ███╗   ███╗ ██████╗      ██████╗  █████╗ ███╗   ██╗██╗  ██╗",
        r"  ████╗ ████║ ██╔══██╗     ██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝",
        r"  ██╔████╔██║ ██████╔╝     ██████╔╝███████║██╔██╗ ██║█████╔╝ ",
        r"  ██║╚██╔╝██║ ██╔══██╗     ██╔══██╗██╔══██║██║╚██╗██║██╔═██╗ ",
        r"  ██║ ╚═╝ ██║ ██████╔╝     ██████╔╝██║  ██║██║ ╚████║██║  ██╗",
        r"  ╚═╝     ╚═╝ ╚═════╝      ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝",
    ]
    for row in logo:
        print(t(C.MB3, row))
    print()
    print(rainbow_str("  ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦"))
    print()
    box_rainbow(
        " MB BANK  ·  VIP CLIENT ",
        [
            t(C.GRAY, "  Nguồn lib: ")
            + t(C.SKY, "github.com/thedtvn/MBBank")
            + t(C.GRAY, "  (mbbank-lib)"),
            t(C.GRAY, "  API host:  ") + t(C.WHT, API_BASE + API_PATH),
            t(C.GRAY, "  Thời gian: ")
            + t(C.WHT, datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
            t(C.GRAY, "  Trạng thái:")
            + t(C.LIME + C.B, "  ● ONLINE")
            + t(C.GRAY, "  ·  history · balance · notify"),
        ],
        width=w,
    )
    print()


def money(n: Any) -> str:
    try:
        v = int(float(str(n).replace(",", "").replace("đ", "").strip() or 0))
        return f"{v:,}".replace(",", ".") + "đ"
    except Exception:
        return str(n)


def spinner(msg: str, sec: float = 0.35) -> None:
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    if not color_ok():
        print(f"  {msg}")
        return
    end = time.time() + sec
    i = 0
    while time.time() < end:
        sys.stdout.write(f"\r  {t(C.MB2, frames[i % len(frames)])} {t(C.WHT, msg)}   ")
        sys.stdout.flush()
        time.sleep(0.07)
        i += 1
    sys.stdout.write("\r" + " " * 72 + "\r")
    sys.stdout.flush()


def http_get(url: str, timeout: int = TIMEOUT) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "MBBank-VIP-Client/3.0",
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
    return http_get(f"{API_BASE}{API_PATH}?{urllib.parse.urlencode(q)}")


def print_wallet(data: Dict[str, Any], ms: int = 0) -> None:
    bal = data.get("balance")
    rng = data.get("range") or {}
    noti = data.get("notify") or {}
    box_rainbow(
        " SỐ DƯ  ·  WALLET ",
        [
            t(C.MB3, "  💰  Số dư hiện tại"),
            t(C.LIME + C.B, f"      {money(bal) if bal is not None else '—'}"),
            "",
            t(C.GRAY, "  📅  ")
            + t(C.WHT, f"{rng.get('from', '?')} → {rng.get('to', '?')}")
            + t(C.GRAY, f"   ({rng.get('days', '?')} ngày)"),
            t(C.GRAY, "  ⚡  ")
            + t(C.WHT, f"src={data.get('src')}  total={data.get('total')}")
            + (t(C.GRAY, f"  ·  {ms}ms") if ms else ""),
            t(C.GRAY, "  🔔  ")
            + t(
                C.WHT,
                f"Zalo notify={noti.get('notified', 0)}  new={noti.get('new_count', 0)}",
            ),
        ],
        width=64,
    )


def print_txs(data: Dict[str, Any]) -> None:
    txs: List[Dict[str, Any]] = data.get("transactions") or []
    print()
    # rainbow mini header
    print(rainbow_str("  ─────────────── LỊCH SỬ GIAO DỊCH ───────────────"))
    print()
    if not txs:
        print(t(C.YEL, "  (Không có giao dịch trong khoảng này)"))
        return
    for i, tx in enumerate(txs, 1):
        is_in = (tx.get("type") or "") == "IN"
        icon = "🟢  IN" if is_in else "🔴 OUT"
        col = C.LIME if is_in else C.ORNG
        line1 = tx.get("line1") or f"{tx.get('amount', '')} | {tx.get('transactionDate', '')}"
        line2 = (tx.get("line2") or tx.get("description") or "")[:78]
        line3 = tx.get("line3") or ""
        # left rainbow bar
        bar = rb_char(i, "▌")
        print(f"  {bar} {t(col + C.B, icon)}  {t(C.MB2, f'#{i}')}")
        print(f"  {bar}   {t(C.WHT, line1)}")
        if line2:
            print(f"  {bar}   {t(C.GRAY, line2)}")
        if line3:
            print(f"  {bar}   {t(C.TEAL, line3)}")
        if i < len(txs):
            print(t(C.D, "  · · · · · · · · · · · · · · · · · · · · · · · · · · · · · ·"))
    print()
    print(rainbow_str("  ─────────────────────────────────────────────────"))
    print()


def action_once(rows: int = DEFAULT_ROWS, days: int = DEFAULT_DAYS) -> Dict[str, Any]:
    spinner(f"Kết nối MB Bank API · rows={rows} · days={days}")
    t0 = time.time()
    try:
        data = fetch_history(rows=rows, days=days)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:220]
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
    print(t(C.LIME + C.B, "  ✔  SUCCESS") + t(C.GRAY, f"  ·  {ms} ms"))
    print()
    print_wallet(data, ms)
    print_txs(data)
    return data


def action_poll(interval: int = POLL_SEC, rows: int = 10, days: int = 14) -> None:
    print(t(C.MB3, "  ⟳  LIVE POLL"))
    print(t(C.GRAY, f"     mỗi {interval}s · Ctrl+C dừng · nên ≥ 15–30s/lần"))
    print()
    n = 0
    while True:
        n += 1
        stamp = datetime.now().strftime("%H:%M:%S")
        print(rainbow_str(f"  ─── #{n}  {stamp} ────────────────────────────"))
        data = action_once(rows=rows, days=days)
        noti = (data or {}).get("notify") or {}
        if noti.get("notified"):
            print(
                t(C.PINK + C.B, f"  🔔  Đã đẩy {noti.get('notified')} tin Zalo")
                + t(C.GRAY, f"  (new={noti.get('new_count')})")
            )
        try:
            for left in range(interval, 0, -1):
                sys.stdout.write(
                    f"\r  {t(C.GRAY, '⏳ next')} {t(C.MB2 + C.B, str(left).rjust(3))}s   "
                )
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write("\r" + " " * 36 + "\r")
        except KeyboardInterrupt:
            print(t(C.YEL, "\n  ⏹  Dừng poll."))
            break


def show_features() -> None:
    """Liệt kê chức năng theo thedtvn/MBBank + API hiện có."""
    box_rainbow(
        " CHỨC NĂNG  ·  thedtvn/MBBank + API ",
        [
            t(C.LIME, "  ✔  ") + t(C.WHT, "Lịch sử giao dịch (getTransactionAccountHistory)"),
            t(C.LIME, "  ✔  ") + t(C.WHT, "Số dư realtime (getBalance)"),
            t(C.LIME, "  ✔  ") + t(C.WHT, "Auto notify Zalo khi có GD mới"),
            t(C.LIME, "  ✔  ") + t(C.WHT, "Poll / session cache trên server"),
            t(C.GOLD, "  ▸  ") + t(C.GRAY, "userinfo / cardList / saving — qua mbbank-lib local"),
            t(C.GOLD, "  ▸  ") + t(C.GRAY, "Transfer / bulkTransfer — cần OTP app MB (mbbank-lib)"),
            "",
            t(C.GRAY, "  Cài local full:  pip install mbbank-lib"),
            t(C.GRAY, "  Docs:  https://github.com/thedtvn/MBBank"),
        ],
        width=64,
    )
    print()
    print(t(C.YEL, "  ⚠  Chuyển tiền (transfer) chỉ chạy local + OTP trên app MB."))
    print(t(C.YEL, "     API cloud hiện tại: chỉ đọc lịch sử + số dư + Zalo notify."))
    print()


def menu() -> None:
    banner()
    while True:
        box_rainbow(
            " MENU  ·  MB BANK ",
            [
                t(C.LIME + C.B, "  [1]") + t(C.WHT, "  Xem GD mới nhất + số dư"),
                t(C.SKY + C.B, "  [2]") + t(C.WHT, "  Xem 30 GD / 30 ngày"),
                t(C.PINK + C.B, "  [3]") + t(C.WHT, "  Live poll (Zalo auto)"),
                t(C.GOLD + C.B, "  [4]") + t(C.WHT, "  Tùy chỉnh rows / days"),
                t(C.MB2 + C.B, "  [5]") + t(C.WHT, "  Danh sách chức năng (lib gốc)"),
                t(C.GRAY + C.B, "  [0]") + t(C.GRAY, "  Thoát"),
            ],
            width=64,
        )
        print()
        try:
            choice = input(t(C.MB3, "  ❯ ") + t(C.WHT, "Chọn: ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        print()
        if choice == "0":
            print(t(C.MB2, "  MB BANK client closed."))
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
                print(t(C.YEL, "  ⚠  <10s dễ bị MB nghi."))
            action_poll(interval=interval)
        elif choice == "4":
            try:
                rows = int(input(t(C.D, "  rows [15]: ")).strip() or "15")
                days = int(input(t(C.D, "  days [14]: ")).strip() or "14")
            except ValueError:
                print(t(C.RED, "  Số không hợp lệ"))
                continue
            action_once(rows=rows, days=days)
        elif choice == "5":
            show_features()
        else:
            print(t(C.YEL, "  Chọn 0–5"))
        print()


def main(argv: List[str]) -> int:
    global API_BASE
    rows, days, interval, mode = DEFAULT_ROWS, DEFAULT_DAYS, POLL_SEC, "menu"
    i = 0
    while i < len(argv):
        a = argv[i]
        if a in ("-h", "--help"):
            print(__doc__)
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
