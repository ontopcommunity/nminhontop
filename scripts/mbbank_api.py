#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MB BANK Client — by Ontop
"""
from __future__ import annotations

import getpass
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

class C:
    R = "\033[0m"
    B = "\033[1m"
    MB = "\033[1;38;5;27m"
    CYN = "\033[1;96m"
    GRN = "\033[1;92m"
    W = "\033[1;97m"
    GRAY = "\033[38;5;245m"
    YEL = "\033[1;93m"
    RED = "\033[1;91m"
    PINK = "\033[1;38;5;213m"
    TEAL = "\033[1;38;5;44m"
    ORNG = "\033[1;38;5;214m"
    LIME = "\033[1;38;5;118m"
    RB = [
        "\033[1;38;5;196m",
        "\033[1;38;5;208m",
        "\033[1;38;5;226m",
        "\033[1;38;5;46m",
        "\033[1;38;5;51m",
        "\033[1;38;5;39m",
        "\033[1;38;5;129m",
        "\033[1;38;5;201m",
    ]


def uc() -> bool:
    return sys.stdout.isatty() and not os.getenv("NO_COLOR")


def t(c: str, s: str) -> str:
    return f"{c}{s}{C.R}" if uc() else s


def rb(s: str, off: int = 0) -> str:
    if not uc():
        return s
    return "".join(f"{C.RB[(off + i) % len(C.RB)]}{ch}" for i, ch in enumerate(s)) + C.R


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


def g(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if obj is None:
            return default
        if isinstance(obj, dict) and k in obj:
            return obj[k]
        if hasattr(obj, k):
            return getattr(obj, k)
    return default


def vis_len(s: str) -> int:
    n = i = 0
    while i < len(s):
        if s[i] == "\033":
            while i < len(s) and s[i] != "m":
                i += 1
            i += 1
            continue
        n += 1
        i += 1
    return n


# ── khung cầu vồng ──
def box(title: str, lines: List[str], width: int = 64) -> None:
    print(rb("  ╔" + "═" * width + "╗", 0))
    pad = max(0, width - len(title))
    L, R = pad // 2, pad - pad // 2
    print(rb("  ║", 1) + t(C.MB, " " * L + title + " " * R) + rb("║", 3))
    print(rb("  ╠" + "═" * width + "╣", 2))
    for line in lines:
        sp = max(0, width - vis_len(line))
        print(rb("  ║", 4) + line + " " * sp + rb("║", 6))
    print(rb("  ╚" + "═" * width + "╝", 5))


def section(title: str) -> None:
    print()
    print(rb("  ─ " + title + " " + "─" * max(0, 40 - len(title))))
    print()


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
    print(rb("  ✦  by Ontop  ✦"))
    print(t(C.GRAY, f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"))
    print()


def draw_menu(title: str, left: List[Tuple[str, str]], right: List[Tuple[str, str]]) -> None:
    w = 64
    half = w // 2 - 1
    print(rb("  ╔" + "═" * w + "╗", 0))
    pad = max(0, w - len(title))
    L, R = pad // 2, pad - pad // 2
    print(rb("  ║", 1) + t(C.MB, " " * L + title + " " * R) + rb("║", 3))
    print(rb("  ╠" + "═" * half + "╦" + "═" * (w - half) + "╣", 2))
    rows = max(len(left), len(right))
    for i in range(rows):
        l = left[i] if i < len(left) else ("", "")
        r = right[i] if i < len(right) else ("", "")
        lc = (t(C.CYN, f"{l[0]:>2}") + t(C.W, f" {l[1]}")) if l[0] else ""
        rc = (t(C.CYN, f"{r[0]:>2}") + t(C.W, f" {r[1]}")) if r[0] else ""
        lp = max(0, half - vis_len(lc))
        rp = max(0, w - half - vis_len(rc))
        print(rb("  ║", 4) + lc + " " * lp + rb("│", 5) + rc + " " * rp + rb("║", 6))
    print(rb("  ╚" + "═" * half + "╩" + "═" * (w - half) + "╝", 7))


# ─────────── SESSION ───────────
_mb = None
_default_stk: Optional[str] = None


def ensure_lib() -> bool:
    try:
        import mbbank  # noqa: F401
        return True
    except ImportError:
        print(t(C.YEL, "  Đang cài thư viện..."))
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "mbbank-lib"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(t(C.RED, "  Cài thất bại. Chạy: pip install mbbank-lib"))
            return False
        try:
            import mbbank  # noqa: F401
            return True
        except ImportError:
            return False


def login():
    global _mb, _default_stk
    if _mb is not None:
        return _mb
    if not ensure_lib():
        return None
    import mbbank

    user = os.getenv("MB_USERNAME") or os.getenv("MB_USER") or ""
    pwd = os.getenv("MB_PASSWORD") or os.getenv("MB_PASS") or ""
    if not user:
        user = tty_input(t(C.CYN, "  Tên đăng nhập / SĐT: ")).strip()
    if not pwd:
        if sys.stdin.isatty():
            pwd = getpass.getpass(t(C.CYN, "  Mật khẩu: "))
        else:
            pwd = tty_input(t(C.CYN, "  Mật khẩu: ")).strip()
    print(t(C.YEL, "  Đang đăng nhập MB Bank..."))
    t0 = time.time()
    try:
        _mb = mbbank.MBBank(username=user, password=pwd)
        print(t(C.GRN, f"  Đăng nhập thành công ({int((time.time() - t0) * 1000)} ms)"))
        # STK mặc định = TK đăng nhập (STK đầu tiên)
        try:
            accts = get_accounts(_mb)
            if accts:
                _default_stk = str(g(accts[0], "acctNo", "accountNo", default="") or "")
                # ưu tiên STK trùng username nếu có
                for a in accts:
                    no = str(g(a, "acctNo", "accountNo", default="") or "")
                    if no and (no == user or no.endswith(user[-9:] if len(user) >= 9 else user)):
                        _default_stk = no
                        break
        except Exception:
            _default_stk = user
        if _default_stk:
            print(t(C.GRAY, f"  STK mặc định: {_default_stk}"))
        return _mb
    except Exception as e:
        print(t(C.RED, f"  Đăng nhập thất bại: {e}"))
        return None


def get_accounts(mb) -> List[Any]:
    data = mb.getBalance()
    return list(g(data, "acct_list", "acctList", default=[]) or [])


def default_stk(mb) -> Optional[str]:
    global _default_stk
    if _default_stk:
        return _default_stk
    accts = get_accounts(mb)
    if accts:
        _default_stk = str(g(accts[0], "acctNo", "accountNo", default="") or "") or None
    return _default_stk


# ═══════════════════════════════════════════════════════════
# GIAO DIỆN LỊCH SỬ — y chang bản API cũ
# (line1 / line2 / line3 · wallet card · không JSON · không icon)
# ═══════════════════════════════════════════════════════════
def show_wallet(balance: Any, from_d: str, to_d: str, total: int, ms: int = 0) -> None:
    lines = [
        t(C.MB, "  Số dư hiện tại"),
        t(C.LIME + C.B, f"      {money(balance)}"),
        "",
        t(C.GRAY, "  Khoảng  ") + t(C.W, f"{from_d} → {to_d}"),
        t(C.GRAY, "  Tổng GD ") + t(C.W, str(total)) + (t(C.GRAY, f"  ·  {ms} ms") if ms else ""),
    ]
    box(" SỐ DƯ ", lines, 64)


def show_history_ui(txs: List[dict], balance: Any, from_d: str, to_d: str, ms: int = 0) -> None:
    """
    Giao diện lịch sử bản API cũ:
      line1: ±số tiền | thời gian
      line2: nội dung
      line3: Số dư: ...
    """
    show_wallet(balance, from_d, to_d, len(txs), ms)
    print()
    print(rb("  ─────────────── LỊCH SỬ GIAO DỊCH ───────────────"))
    print()
    if not txs:
        print(t(C.YEL, "  (Không có giao dịch)"))
        print()
        print(rb("  ─────────────────────────────────────────────────"))
        return

    for i, tx in enumerate(txs, 1):
        is_in = tx.get("type") == "IN"
        col = C.LIME if is_in else C.ORNG
        sign = "+" if is_in else "−"
        amt = money(tx.get("amount"))
        date = tx.get("date") or ""
        desc = (tx.get("desc") or "")[:80]
        bal = tx.get("bal")
        line1 = f"{sign}{amt} | {date}"
        line2 = desc
        line3 = f"Số dư: {money(bal)}" if bal is not None else ""

        bar = rb("▌", i)
        print(f"  {bar} {t(col + C.B, f'#{i}')}")
        print(f"  {bar}   {t(C.W, line1)}")
        if line2:
            print(f"  {bar}   {t(C.GRAY, line2)}")
        if line3:
            print(f"  {bar}   {t(C.TEAL, line3)}")
        if i < len(txs):
            print(t(C.GRAY, "  · · · · · · · · · · · · · · · · · · · · · · · · · · · · · ·"))
    print()
    print(rb("  ─────────────────────────────────────────────────"))
    print(t(C.GRAY, f"  Tổng: {len(txs)} giao dịch"))


def fetch_and_show_history(mb, account_no: Optional[str], days: int = 30) -> None:
    to_d = datetime.now()
    fr_d = to_d - timedelta(days=min(max(days, 1), 90))
    from_s = fr_d.strftime("%d/%m/%Y")
    to_s = to_d.strftime("%d/%m/%Y")
    stk = account_no or default_stk(mb)
    print(t(C.YEL, f"  Đang lấy lịch sử STK {stk or 'mặc định'} · {from_s} → {to_s}..."))
    t0 = time.time()
    try:
        try:
            hist = mb.getTransactionAccountHistory(
                from_date=fr_d, to_date=to_d, accountNo=stk
            )
        except TypeError:
            hist = mb.getTransactionAccountHistory(from_date=fr_d, to_date=to_d)
    except Exception as e:
        print(t(C.RED, f"  Lỗi lấy lịch sử: {e}"))
        return
    ms = int((time.time() - t0) * 1000)

    raw = list(g(hist, "transactionHistoryList", default=[]) or [])
    txs = []
    balance = None
    for tx in raw:
        credit = str(g(tx, "creditAmount", default="0") or "0").replace(",", "")
        debit = str(g(tx, "debitAmount", default="0") or "0").replace(",", "")
        try:
            c_amt = float(credit or 0)
            d_amt = float(debit or 0)
        except Exception:
            c_amt, d_amt = 0.0, 0.0
        is_in = c_amt > 0
        amt = c_amt if is_in else d_amt
        bal = g(tx, "availableBalance", "balance", default=None)
        if bal is not None and balance is None:
            balance = bal
        txs.append(
            {
                "type": "IN" if is_in else "OUT",
                "amount": amt,
                "date": str(g(tx, "transactionDate", "postingDate", default=""))[:19],
                "desc": str(g(tx, "description", default="")),
                "bal": bal,
            }
        )
    # số dư realtime nếu có
    try:
        for a in get_accounts(mb):
            no = str(g(a, "acctNo", "accountNo", default="") or "")
            if stk and no == str(stk):
                balance = g(a, "currentBalance", "balance", "availableBalance", default=balance)
                break
        if balance is None and get_accounts(mb):
            balance = g(get_accounts(mb)[0], "currentBalance", "balance", default=None)
    except Exception:
        pass

    print(t(C.GRN, f"  Thành công — {ms} ms\n"))
    show_history_ui(txs, balance, from_s, to_s, ms)


# ─────────── TÍNH NĂNG ───────────
def feat_balance_pick(mb) -> None:
    """01 — chọn STK bất kỳ rồi xem lịch sử"""
    while True:
        clear()
        logo()
        section("SỐ DƯ  ·  DANH SÁCH STK")
        try:
            accts = get_accounts(mb)
        except Exception as e:
            print(t(C.RED, f"  Lỗi lấy số dư: {e}"))
            pause()
            return
        if not accts:
            print(t(C.YEL, "  Không tìm thấy tài khoản"))
            pause()
            return

        lines = []
        for i, a in enumerate(accts, 1):
            no = g(a, "acctNo", "accountNo", default="?")
            bal = g(a, "currentBalance", "balance", "availableBalance", default=0)
            alias = g(a, "acctAlias", "alias", default="") or ""
            cur = g(a, "currency", default="VND")
            lines.append(t(C.CYN, f"  {i:02}") + t(C.W, f"  STK: {no}"))
            if alias:
                lines.append(t(C.GRAY, f"      Tên: {alias}"))
            lines.append(t(C.LIME + C.B, f"      Số dư: {money(bal)} {cur}"))
            lines.append("")
        box(" DANH SÁCH TÀI KHOẢN ", lines, 64)
        print()
        print(t(C.W, "  Nhập số STK để xem lịch sử (từ trước đến nay)"))
        print(t(C.GRAY, "  Enter (trống) quay về menu chính"))
        print()
        choice = tty_input(t(C.CYN, "  Chọn STK (0): ")).strip()
        if not choice or choice == "0":
            return
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(accts):
                print(t(C.RED, "  Số không hợp lệ"))
                time.sleep(1)
                continue
        except ValueError:
            print(t(C.RED, "  Hãy nhập số"))
            time.sleep(1)
            continue
        stk = g(accts[idx], "acctNo", "accountNo", default=None)
        clear()
        logo()
        fetch_and_show_history(mb, stk, days=90)
        pause("Nhấn Enter để chọn STK khác...")


def feat_history_days(mb, days: int) -> None:
    """02/03/04 — luôn dùng STK mặc định khi đăng nhập"""
    clear()
    logo()
    stk = default_stk(mb)
    fetch_and_show_history(mb, stk, days=days)
    pause()


def feat_user(mb) -> None:
    clear()
    logo()
    section("THÔNG TIN NGƯỜI DÙNG")
    try:
        info = mb.userinfo()
        lines = []
        for label, *keys in [
            ("Họ tên", "custName", "name", "fullName"),
            ("SĐT", "phone", "mobile", "phoneNumber"),
            ("Email", "email"),
            ("CIF", "cif", "cifNumber"),
            ("CMND/CCCD", "idNumber", "nationalId"),
        ]:
            val = g(info, *keys, default=None)
            if val is not None and str(val).strip():
                lines.append(t(C.CYN, f"  {label:<12}") + t(C.W, str(val)))
        if not lines:
            for k in dir(info):
                if k.startswith("_"):
                    continue
                try:
                    v = getattr(info, k)
                    if isinstance(v, (str, int, float)) and not callable(v):
                        lines.append(t(C.CYN, f"  {k:<16}") + t(C.W, str(v)))
                except Exception:
                    pass
        if not lines:
            lines = [t(C.YEL, "  (Không đọc được thông tin)")]
        box(" THÔNG TIN ", lines, 64)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_cards(mb) -> None:
    clear()
    logo()
    section("DANH SÁCH THẺ")
    try:
        data = mb.getCardList()
        cards = list(g(data, "cardList", default=[]) or [])
        lines = []
        if not cards:
            lines.append(t(C.YEL, "  Không có thẻ"))
        for i, c_ in enumerate(cards, 1):
            no = g(c_, "cardNo", "cardNumber", default="?")
            typ = g(c_, "cardModule", "cardType", "cardClass", default="")
            st = g(c_, "cardStatus", "status", default="")
            lines.append(t(C.CYN, f"  {i:02}") + t(C.W, f"  {no}"))
            lines.append(t(C.GRAY, f"      Loại: {typ}  |  Trạng thái: {st}"))
            lines.append("")
        box(" THẺ ", lines, 64)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_saving(mb) -> None:
    clear()
    logo()
    section("TIẾT KIỆM")
    try:
        data = mb.getSavingList()
        items = list(
            g(data, "savingList", "list", "osaList", default=None)
            or g(data, "sbaList", default=[])
            or []
        )
        if not items:
            for k in dir(data):
                if k.startswith("_"):
                    continue
                v = getattr(data, k, None)
                if isinstance(v, list) and v:
                    items = v
                    break
        lines = []
        if not items:
            lines.append(t(C.YEL, "  Không có sổ tiết kiệm"))
        for i, s in enumerate(items, 1):
            no = g(s, "accNo", "acctNo", "accountNo", default="?")
            bal = g(s, "balance", "currentBalance", "amount", default="")
            lines.append(
                t(C.CYN, f"  {i:02}")
                + t(C.W, f"  {no}  ")
                + t(C.LIME, money(bal) if bal != "" else "")
            )
        box(" TIẾT KIỆM ", lines, 64)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_loan(mb) -> None:
    clear()
    logo()
    section("KHOẢN VAY")
    try:
        data = mb.getLoanList()
        items = list(g(data, "loanList", "list", default=[]) or [])
        lines = []
        if not items:
            lines.append(t(C.YEL, "  Không có khoản vay"))
        for i, s in enumerate(items, 1):
            no = g(s, "loanNo", "accNo", "acctNo", default="?")
            amt = g(s, "amount", "balance", "outstanding", default="")
            lines.append(
                t(C.CYN, f"  {i:02}")
                + t(C.W, f"  {no}  ")
                + t(C.ORNG, money(amt) if amt != "" else "")
            )
        box(" KHOẢN VAY ", lines, 64)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_loyalty(mb) -> None:
    clear()
    logo()
    section("LOYALTY / ĐIỂM")
    try:
        data = mb.getBalanceLoyalty()
        lines = []
        pts = g(data, "point", "balance", "loyaltyPoint", "totalPoint", default=None)
        if pts is not None:
            lines.append(t(C.LIME + C.B, f"  Điểm: {pts}"))
        else:
            for k in dir(data):
                if k.startswith("_"):
                    continue
                v = getattr(data, k, None)
                if isinstance(v, (int, float, str)) and not callable(v):
                    lines.append(t(C.CYN, f"  {k:<20}") + t(C.W, str(v)))
        if not lines:
            lines.append(t(C.YEL, "  (Trống)"))
        box(" LOYALTY ", lines, 64)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_interest(mb) -> None:
    clear()
    logo()
    section("LÃI SUẤT")
    try:
        data = mb.getInterestRate()
        lines = []
        for k in dir(data):
            if k.startswith("_"):
                continue
            v = getattr(data, k, None)
            if isinstance(v, (int, float, str)) and not callable(v):
                lines.append(t(C.CYN, f"  {k:<20}") + t(C.W, str(v)))
            elif isinstance(v, list) and v:
                lines.append(t(C.W, f"  {k}: {len(v)} mục"))
                for i, item in enumerate(v[:12], 1):
                    name = g(item, "name", "productName", "type", default=str(item)[:36])
                    rate = g(item, "rate", "interestRate", default="")
                    lines.append(t(C.GRAY, f"    {i:02}  {name}  {rate}"))
        if not lines:
            lines.append(t(C.YEL, "  (Trống)"))
        box(" LÃI SUẤT ", lines, 64)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_banks(mb) -> None:
    clear()
    logo()
    section("DANH SÁCH NGÂN HÀNG")
    try:
        data = mb.getBankList()
        banks = list(g(data, "listBank", "bankList", default=[]) or [])
        lines = [t(C.GRN, f"  Tổng: {len(banks)} ngân hàng"), ""]
        for i, b in enumerate(banks[:40], 1):
            code = g(b, "bankCode", "code", default="")
            name = g(b, "bankName", "name", default="")
            lines.append(t(C.CYN, f"  {i:03}") + t(C.W, f"  {str(code):<8}  {name}"))
        if len(banks) > 40:
            lines.append(t(C.GRAY, f"  … +{len(banks) - 40} ngân hàng"))
        box(" NGÂN HÀNG ", lines, 64)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_beneficiary(mb) -> None:
    clear()
    logo()
    section("THỤ HƯỞNG ĐÃ LƯU")
    try:
        try:
            data = mb.getFavorBeneficiaryList()
        except Exception:
            data = mb.getSavedBeneficiary()
        items = list(
            g(data, "beneficiaries", "list", "favorBeneficiaryList", default=[]) or []
        )
        lines = []
        if not items:
            lines.append(t(C.YEL, "  Không có thụ hưởng / danh sách trống"))
        for i, b in enumerate(items, 1):
            name = g(b, "beneficiariesName", "name", "accountName", default="")
            acc = g(b, "accountNo", "acctNo", default="")
            bk = g(b, "bankName", "bankCode", default="")
            lines.append(t(C.CYN, f"  {i:02}") + t(C.W, f"  {name}"))
            lines.append(t(C.GRAY, f"      STK: {acc}  |  {bk}"))
            lines.append("")
        box(" THỤ HƯỞNG ", lines, 64)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_phone(mb) -> None:
    clear()
    logo()
    section("TRA STK THEO SĐT")
    phone = tty_input(t(C.CYN, "  Nhập SĐT: ")).strip()
    if not phone:
        return
    try:
        data = mb.getAccountByPhone(phone)
        lines = []
        name = g(data, "accountName", "name", "custName", default="")
        acc = g(data, "accountNo", "acctNo", default="")
        bank = g(data, "bankName", "bankCode", default="")
        if name or acc:
            lines.append(t(C.CYN, "  Tên TK : ") + t(C.W, str(name)))
            lines.append(t(C.CYN, "  STK    : ") + t(C.W, str(acc)))
            lines.append(t(C.CYN, "  NH     : ") + t(C.W, str(bank)))
        else:
            for k in dir(data):
                if k.startswith("_"):
                    continue
                v = getattr(data, k, None)
                if isinstance(v, (str, int, float)) and v:
                    lines.append(t(C.CYN, f"  {k:<16}") + t(C.W, str(v)))
        if not lines:
            lines.append(t(C.YEL, "  (Không có dữ liệu)"))
        box(" KẾT QUẢ ", lines, 64)
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_transfer(mb) -> None:
    clear()
    logo()
    section("CHUYỂN TIỀN (cần OTP app MB)")
    print(t(C.RED, "  Cảnh báo: giao dịch thật — kiểm tra kỹ STK / số tiền\n"))
    try:
        accts = get_accounts(mb)
        if not accts:
            print(t(C.RED, "  Không có tài khoản nguồn"))
            pause()
            return
        for i, a in enumerate(accts, 1):
            print(
                t(C.CYN, f"  {i:02}")
                + t(
                    C.W,
                    f"  {g(a, 'acctNo')}  {money(g(a, 'currentBalance', 'balance', default=0))}",
                )
            )
        idx = int(tty_input(t(C.CYN, "  TK nguồn [1]: ")).strip() or "1") - 1
        src = g(accts[idx], "acctNo")
        code = tty_input(t(C.CYN, "  Mã ngân hàng (MB/VCB/TCB...): ")).strip().upper()
        dest = tty_input(t(C.CYN, "  STK nhận: ")).strip()
        amount = int(tty_input(t(C.CYN, "  Số tiền: ")).strip())
        msg = tty_input(t(C.CYN, "  Nội dung: ")).strip() or "CK"
        print(t(C.YEL, "  Đang tạo lệnh chuyển..."))
        ctx = mb.makeTransfer(
            src_account=src,
            dest_account=dest,
            bank_code=code,
            amount=amount,
            message=msg,
        )
        auth = ctx.get_auth_list()
        methods = list(g(auth, "authList", default=[]) or [])
        for i, m in enumerate(methods, 1):
            print(t(C.CYN, f"  {i:02}") + t(C.W, f"  {g(m, 'name', default=m)}"))
        mi = int(tty_input(t(C.CYN, "  Auth [1]: ")).strip() or "1") - 1
        method = methods[mi]
        try:
            if ctx.get_qr_code():
                print(t(C.GRAY, "  (Mở app MB quét QR/DOTP nếu cần)"))
        except Exception:
            pass
        otp = tty_input(t(C.CYN, "  Nhập OTP: ")).strip()
        result = ctx.transfer(otp=otp, auth_type=method)
        ok = g(result, "ok", "success", default=None)
        msg_r = g(result, "message", "msg", "description", default="")
        if ok is True or (msg_r and "success" in str(msg_r).lower()):
            print(t(C.GRN, f"  Thành công: {msg_r or 'OK'}"))
        else:
            print(t(C.YEL, f"  Kết quả: {msg_r or 'xem app MB để xác nhận'}"))
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
        traceback.print_exc()
    pause()


def feat_info() -> None:
    clear()
    logo()
    box(
        " THÔNG TIN ",
        [
            t(C.CYN, "  Ứng dụng : ") + t(C.W, "MB BANK Client"),
            t(C.CYN, "  Tác giả  : ") + t(C.GRN, "Ontop"),
            t(C.CYN, "  Phiên bản: ") + t(C.W, "2.1"),
        ],
        64,
    )
    pause()


def main_menu() -> None:
    clear()
    logo()
    mb = login()
    if mb is None:
        print(t(C.RED, "  Thoát."))
        return

    while True:
        clear()
        logo()
        left = [
            ("01", "Số dư + chọn STK xem GD"),
            ("02", "Lịch sử GD 14 ngày"),
            ("03", "Lịch sử GD 30 ngày"),
            ("04", "Lịch sử GD 90 ngày"),
            ("05", "Thông tin người dùng"),
            ("06", "Danh sách thẻ"),
            ("07", "Tiết kiệm"),
        ]
        right = [
            ("08", "Khoản vay"),
            ("09", "Loyalty / điểm"),
            ("10", "Lãi suất"),
            ("11", "Danh sách ngân hàng"),
            ("12", "Thụ hưởng đã lưu"),
            ("13", "Tra STK theo SĐT"),
            ("14", "Chuyển tiền (OTP)"),
            ("15", "Thông tin ứng dụng"),
            ("00", "Thoát chương trình"),
        ]
        draw_menu(" BẢNG CHỨC NĂNG ", left, right)
        if _default_stk:
            print(t(C.GRAY, f"\n  STK mặc định: {_default_stk}"))
        print()
        choice = tty_input(t(C.CYN, "  Chọn chức năng (0): ")).strip()
        try:
            if choice in ("0", "00", ""):
                print(t(C.MB, "\n  Tạm biệt.\n"))
                break
            elif choice in ("1", "01"):
                feat_balance_pick(mb)
            elif choice in ("2", "02"):
                feat_history_days(mb, 14)
            elif choice in ("3", "03"):
                feat_history_days(mb, 30)
            elif choice in ("4", "04"):
                feat_history_days(mb, 90)
            elif choice in ("5", "05"):
                feat_user(mb)
            elif choice in ("6", "06"):
                feat_cards(mb)
            elif choice in ("7", "07"):
                feat_saving(mb)
            elif choice in ("8", "08"):
                feat_loan(mb)
            elif choice in ("9", "09"):
                feat_loyalty(mb)
            elif choice in ("10",):
                feat_interest(mb)
            elif choice in ("11",):
                feat_banks(mb)
            elif choice in ("12",):
                feat_beneficiary(mb)
            elif choice in ("13",):
                feat_phone(mb)
            elif choice in ("14",):
                feat_transfer(mb)
            elif choice in ("15",):
                feat_info()
            else:
                print(t(C.YEL, "  Lựa chọn không hợp lệ"))
                time.sleep(0.8)
        except Exception as e:
            print(t(C.RED, f"  Lỗi: {e}"))
            traceback.print_exc()
            pause()


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(t(C.YEL, "\n  Đã hủy.\n"))
