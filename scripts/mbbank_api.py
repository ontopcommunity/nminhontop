#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MB BANK Client — by Ontop
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

API_BASE = os.getenv("MB_API_URL", "https://apimbbankvip.vercel.app").rstrip("/")
API_PATH = "/api/aduanhminh"
TIMEOUT = int(os.getenv("MB_TIMEOUT", "90"))

# ── màu nổi trên nền đen ──
class C:
    R = "\033[0m"
    B = "\033[1m"
    MB = "\033[1;38;5;27m"       # xanh dương đậm — logo
    CYN = "\033[1;96m"           # khung / số menu (như ảnh)
    GRN = "\033[1;92m"
    W = "\033[1;97m"
    GRAY = "\033[38;5;245m"
    YEL = "\033[1;93m"
    RED = "\033[1;91m"
    MAG = "\033[1;95m"
    PINK = "\033[1;38;5;213m"


def use_color() -> bool:
    return sys.stdout.isatty() and not os.getenv("NO_COLOR")


def t(c: str, s: str) -> str:
    return f"{c}{s}{C.R}" if use_color() else s


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def tty_input(prompt: str = "") -> str:
    if sys.stdin.isatty():
        return input(prompt)
    try:
        with open("/dev/tty", "r") as tty:
            sys.stdout.write(prompt)
            sys.stdout.flush()
            return tty.readline().rstrip("\n\r")
    except Exception:
        return input(prompt)


def pause(msg: str = "Nhấn Enter để quay lại Menu...") -> None:
    try:
        tty_input(t(C.GRAY, f"\n  {msg} "))
    except EOFError:
        pass


def money(n: Any) -> str:
    try:
        v = int(float(str(n).replace(",", "").replace("đ", "").strip() or 0))
        return f"{v:,}".replace(",", ".") + "đ"
    except Exception:
        return str(n) if n is not None else "—"


# ── logo MB BANK (giữ nguyên) ──
def logo() -> None:
    print()
    for row in [
        r"  ███╗   ███╗ ██████╗      ██████╗  █████╗ ███╗   ██╗██╗  ██╗",
        r"  ████╗ ████║ ██╔══██╗     ██╔══██╗██╔══██╗████╗  ██║██║ ██╔╝",
        r"  ██╔████╔██║ ██████╔╝     ██████╔╝███████║██╔██╗ ██║█████╔╝ ",
        r"  ██║╚██╔╝██║ ██╔══██╗     ██╔══██╗██╔══██║██║╚██╗██║██╔═██╗ ",
        r"  ██║ ╚═╝ ██║ ██████╔╝     ██████╔╝██║  ██║██║ ╚████║██║  ██╗",
        r"  ╚═╝     ╚═╝ ╚═════╝      ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝",
    ]:
        print(t(C.MB, row))
    print()
    print(t(C.PINK + C.B, "  MB BANK CLIENT") + t(C.GRAY, "  v1.0"))
    print(t(C.GRN, "  TRỰC TUYẾN: ") + t(C.W, "by Ontop"))
    print()


# ── khung menu 2 cột (style ảnh) ──
def draw_menu_box(title: str, left: List[tuple], right: List[tuple]) -> None:
    """left/right: list of (num_str, label)"""
    w = 62
    top = "╔" + "═" * w + "╗"
    mid = "╠" + "═" * (w // 2 - 1) + "╦" + "═" * (w - w // 2) + "╣"
    bot = "╚" + "═" * (w // 2 - 1) + "╩" + "═" * (w - w // 2) + "╝"
    print(t(C.CYN, "  " + top))
    # title row spanning
    pad = max(0, w - len(title))
    L, R = pad // 2, pad - pad // 2
    print(t(C.CYN, "  ║") + t(C.PINK + C.B, " " * L + title + " " * R) + t(C.CYN, "║"))
    print(t(C.CYN, "  " + mid))

    rows = max(len(left), len(right))
    col_w = w // 2 - 1
    for i in range(rows):
        l = left[i] if i < len(left) else ("", "")
        r = right[i] if i < len(right) else ("", "")
        if l[0]:
            left_cell = t(C.CYN, f"{l[0]:>2}") + t(C.W, f" {l[1]}")
        else:
            left_cell = ""
        if r[0]:
            right_cell = t(C.CYN, f"{r[0]:>2}") + t(C.W, f" {r[1]}")
        else:
            right_cell = ""
        # pad visible roughly
        def vis(s: str) -> int:
            n = j = 0
            while j < len(s):
                if s[j] == "\033":
                    while j < len(s) and s[j] != "m":
                        j += 1
                    j += 1
                    continue
                n += 1
                j += 1
            return n

        lp = max(0, col_w - vis(left_cell))
        rp = max(0, col_w - vis(right_cell) + 1)
        print(
            t(C.CYN, "  ║")
            + left_cell
            + " " * lp
            + t(C.CYN, "│")
            + right_cell
            + " " * rp
            + t(C.CYN, "║")
        )
    print(t(C.CYN, "  " + bot))


def section(title: str) -> None:
    print()
    print(t(C.CYN, "  ─ " + title + " " + "─" * max(0, 40 - len(title))))
    print()


# ── API ──
def http_get(url: str) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "MBBank-Ontop/1.0",
            "Cache-Control": "no-store",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
        return json.loads(res.read().decode("utf-8", errors="replace"))


def fetch(rows: int = 20, days: int = 30, account: Optional[str] = None) -> Dict[str, Any]:
    q: Dict[str, str] = {"rows": str(rows), "days": str(days)}
    if account:
        q["account"] = account
    url = f"{API_BASE}{API_PATH}?{urllib.parse.urlencode(q)}"
    return http_get(url)


def show_balance_block(data: Dict[str, Any]) -> None:
    bal = data.get("balance")
    rng = data.get("range") or {}
    print(t(C.CYN, "  ╭──────────────────────────────────────╮"))
    print(
        t(C.CYN, "  │ ")
        + t(C.W, "Số dư hiện tại: ")
        + t(C.GRN + C.B, f"{money(bal):<18}")
        + t(C.CYN, "│")
    )
    if rng:
        print(
            t(C.CYN, "  │ ")
            + t(C.GRAY, f"Khoảng: {rng.get('from', '?')} → {rng.get('to', '?')}")
            + t(C.CYN, " │")
        )
    print(t(C.CYN, "  ╰──────────────────────────────────────╯"))
    print()


def show_transactions(data: Dict[str, Any]) -> None:
    txs = data.get("transactions") or []
    if not txs:
        print(t(C.YEL, "  (Không có giao dịch)"))
        return
    print(
        t(
            C.GRAY,
            f"  {'#':<4}{'Loại':<6}{'Số tiền':<16}{'Thời gian':<22}Nội dung",
        )
    )
    print(t(C.CYN, "  " + "─" * 70))
    for i, tx in enumerate(txs, 1):
        kind = tx.get("type") or ""
        is_in = kind == "IN"
        label = "VÀO" if is_in else "RA"
        col = C.GRN if is_in else C.YEL
        # parse from slim fields
        line1 = tx.get("line1") or ""
        # amount from amount field or line1
        amt = tx.get("amount")
        if amt is not None:
            sign = "+" if is_in else "-"
            amt_s = sign + money(amt)
        else:
            amt_s = line1.split("|")[0].strip() if "|" in line1 else line1
        date = tx.get("transactionDate") or ""
        if not date and "|" in line1:
            date = line1.split("|", 1)[1].strip()
        desc = (tx.get("description") or tx.get("line2") or "")[:40]
        print(
            t(col, f"  {i:<4}{label:<6}{amt_s:<16}")
            + t(C.W, f"{date:<22}")
            + t(C.GRAY, desc)
        )
        line3 = tx.get("line3") or ""
        if line3:
            print(t(C.GRAY, f"      {line3}"))
    print(t(C.CYN, "  " + "─" * 70))
    print(t(C.GRAY, f"  Tổng: {len(txs)} giao dịch"))


def action_history(rows: int, days: int) -> None:
    clear()
    logo()
    section(f"LỊCH SỬ GIAO DỊCH  ·  {days} ngày")
    print(t(C.YEL, f"  Đang tải dữ liệu (rows={rows}, days={days})..."))
    t0 = time.time()
    try:
        data = fetch(rows=rows, days=days)
    except urllib.error.HTTPError as e:
        print(t(C.RED, f"  Lỗi HTTP {e.code}"))
        pause()
        return
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
        pause()
        return
    ms = int((time.time() - t0) * 1000)
    if data.get("status") != "success":
        print(t(C.RED, f"  Thất bại: {data.get('msg', 'không rõ')}"))
        pause()
        return
    print(t(C.GRN, f"  Thành công — {ms} ms\n"))
    show_balance_block(data)
    show_transactions(data)
    pause()


def action_balance_pick() -> None:
    """Số dư + xem GD (API trả 1 STK chính; vẫn cho chọn khoảng ngày)."""
    clear()
    logo()
    section("SỐ DƯ / CHỌN KHOẢNG XEM GIAO DỊCH")
    print(t(C.YEL, "  Đang lấy số dư..."))
    try:
        data = fetch(rows=5, days=7)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
        pause()
        return
    if data.get("status") != "success":
        print(t(C.RED, f"  Thất bại: {data.get('msg')}"))
        pause()
        return

    show_balance_block(data)
    print(t(C.W, "  Chọn khoảng lịch sử:"))
    print(t(C.CYN, "  01") + t(C.W, "  7 ngày gần nhất"))
    print(t(C.CYN, "  02") + t(C.W, "  14 ngày"))
    print(t(C.CYN, "  03") + t(C.W, "  30 ngày"))
    print(t(C.CYN, "  04") + t(C.W, "  90 ngày (tối đa)"))
    print(t(C.GRAY, "  Enter  Quay về menu"))
    print()
    c = tty_input(t(C.CYN, "  Chọn (0): ")).strip()
    if not c or c == "0":
        return
    mapping = {"1": (30, 7), "01": (30, 7), "2": (50, 14), "02": (50, 14),
               "3": (80, 30), "03": (80, 30), "4": (100, 90), "04": (100, 90)}
    if c not in mapping:
        print(t(C.YEL, "  Lựa chọn không hợp lệ"))
        time.sleep(1)
        return
    rows, days = mapping[c]
    clear()
    logo()
    section(f"LỊCH SỬ GIAO DỊCH  ·  {days} ngày")
    print(t(C.YEL, "  Đang tải..."))
    try:
        data2 = fetch(rows=rows, days=days)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
        pause()
        return
    if data2.get("status") != "success":
        print(t(C.RED, f"  Thất bại: {data2.get('msg')}"))
        pause()
        return
    show_balance_block(data2)
    show_transactions(data2)
    pause()


def action_poll() -> None:
    clear()
    logo()
    section("THEO DÕI TỰ ĐỘNG")
    raw = tty_input(t(C.CYN, "  Chu kỳ (giây) [30]: ")).strip()
    try:
        interval = int(raw) if raw else 30
    except ValueError:
        interval = 30
    if interval < 10:
        print(t(C.YEL, "  Khuyến nghị ≥ 15–30 giây"))
    print(t(C.GRAY, "  Ctrl+C để dừng\n"))
    n = 0
    try:
        while True:
            n += 1
            print(t(C.CYN, f"  ── Lần #{n} · {datetime.now().strftime('%H:%M:%S')} ──"))
            try:
                data = fetch(rows=10, days=14)
                if data.get("status") == "success":
                    bal = data.get("balance")
                    print(t(C.GRN, f"  Số dư: {money(bal)}"))
                    txs = data.get("transactions") or []
                    if txs:
                        tx = txs[0]
                        print(t(C.W, f"  GD mới nhất: {tx.get('line1') or tx.get('amount')}"))
                    noti = data.get("notify") or {}
                    if noti.get("notified"):
                        print(t(C.PINK, f"  Đã gửi Zalo: {noti.get('notified')} tin"))
                else:
                    print(t(C.RED, f"  Lỗi: {data.get('msg')}"))
            except Exception as e:
                print(t(C.RED, f"  Lỗi: {e}"))
            for left in range(interval, 0, -1):
                sys.stdout.write(f"\r  {t(C.GRAY, 'Đợi')} {t(C.CYN, str(left))}s   ")
                sys.stdout.flush()
                time.sleep(1)
            sys.stdout.write("\r" + " " * 30 + "\r")
    except KeyboardInterrupt:
        print(t(C.YEL, "\n  Đã dừng theo dõi."))
        pause()


def action_info() -> None:
    clear()
    logo()
    section("THÔNG TIN")
    print(t(C.W, "  Ứng dụng : ") + t(C.CYN, "MB BANK Client"))
    print(t(C.W, "  Tác giả  : ") + t(C.GRN, "Ontop"))
    print(t(C.W, "  API      : ") + t(C.GRAY, API_BASE + API_PATH))
    print(t(C.W, "  Chức năng: ") + t(C.GRAY, "Số dư, lịch sử GD, theo dõi tự động"))
    pause()


def main_menu() -> None:
    while True:
        clear()
        logo()
        left = [
            ("01", "Số dư + xem giao dịch"),
            ("02", "Lịch sử 14 ngày"),
            ("03", "Lịch sử 30 ngày"),
            ("04", "Lịch sử 90 ngày"),
            ("05", "Theo dõi tự động"),
        ]
        right = [
            ("06", "Thông tin ứng dụng"),
            ("00", "Thoát chương trình"),
        ]
        draw_menu_box(" BẢNG CHỨC NĂNG ", left, right)
        print()
        choice = tty_input(t(C.CYN, "  Chọn chức năng (0): ")).strip()
        if choice in ("0", "00", ""):
            print(t(C.MB, "\n  Tạm biệt.\n"))
            break
        if choice in ("1", "01"):
            action_balance_pick()
        elif choice in ("2", "02"):
            action_history(40, 14)
        elif choice in ("3", "03"):
            action_history(60, 30)
        elif choice in ("4", "04"):
            action_history(100, 90)
        elif choice in ("5", "05"):
            action_poll()
        elif choice in ("6", "06"):
            action_info()
        else:
            print(t(C.YEL, "  Lựa chọn không hợp lệ"))
            time.sleep(0.8)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(t(C.YEL, "\n  Đã hủy.\n"))
