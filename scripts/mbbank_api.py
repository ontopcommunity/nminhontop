#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MB BANK Client — by Ontop
Toàn bộ tính năng mbbank-lib + giao diện terminal.
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

# ─────────── MÀU (nổi trên nền đen) ───────────
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


def uc() -> bool:
    return sys.stdout.isatty() and not os.getenv("NO_COLOR")


def t(c: str, s: str) -> str:
    return f"{c}{s}{C.R}" if uc() else s


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


# ─────────── LOGO ───────────
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
    print(t(C.PINK + C.B, "  MB BANK CLIENT") + t(C.GRAY, "  v2.0"))
    print(t(C.GRN, "  TRỰC TUYẾN: ") + t(C.W, "by Ontop"))
    print()


def section(title: str) -> None:
    print()
    print(t(C.CYN, "  ─ " + title + " " + "─" * max(0, 42 - len(title))))
    print()


def draw_menu(title: str, left: List[Tuple[str, str]], right: List[Tuple[str, str]]) -> None:
    w = 64
    half = w // 2 - 1
    print(t(C.CYN, "  ╔" + "═" * w + "╗"))
    pad = max(0, w - len(title))
    L, R = pad // 2, pad - pad // 2
    print(t(C.CYN, "  ║") + t(C.PINK + C.B, " " * L + title + " " * R) + t(C.CYN, "║"))
    print(t(C.CYN, "  ╠" + "═" * half + "╦" + "═" * (w - half) + "╣"))
    rows = max(len(left), len(right))
    for i in range(rows):
        l = left[i] if i < len(left) else ("", "")
        r = right[i] if i < len(right) else ("", "")
        lc = (t(C.CYN, f"{l[0]:>2}") + t(C.W, f" {l[1]}")) if l[0] else ""
        rc = (t(C.CYN, f"{r[0]:>2}") + t(C.W, f" {r[1]}")) if r[0] else ""
        lp = max(0, half - vis_len(lc))
        rp = max(0, w - half - vis_len(rc))
        print(
            t(C.CYN, "  ║")
            + lc
            + " " * lp
            + t(C.CYN, "│")
            + rc
            + " " * rp
            + t(C.CYN, "║")
        )
    print(t(C.CYN, "  ╚" + "═" * half + "╩" + "═" * (w - half) + "╝"))


# ─────────── SESSION ───────────
_mb = None


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
    global _mb
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
        return _mb
    except Exception as e:
        print(t(C.RED, f"  Đăng nhập thất bại: {e}"))
        return None


def get_accounts(mb) -> List[Any]:
    data = mb.getBalance()
    return list(g(data, "acct_list", "acctList", default=[]) or [])


# ─────────── LỊCH SỬ GD (style bảng sạch, không icon, không JSON) ───────────
def show_history(mb, account_no: Optional[str], days: int = 90) -> None:
    to_d = datetime.now()
    fr_d = to_d - timedelta(days=min(max(days, 1), 90))
    print(
        t(
            C.YEL,
            f"  Đang lấy lịch sử {fr_d.strftime('%d/%m/%Y')} → {to_d.strftime('%d/%m/%Y')}...",
        )
    )
    try:
        try:
            hist = mb.getTransactionAccountHistory(
                from_date=fr_d, to_date=to_d, accountNo=account_no
            )
        except TypeError:
            hist = mb.getTransactionAccountHistory(from_date=fr_d, to_date=to_d)
    except Exception as e:
        print(t(C.RED, f"  Lỗi lấy lịch sử: {e}"))
        return

    txs = list(g(hist, "transactionHistoryList", default=[]) or [])
    section(f"LỊCH SỬ GIAO DỊCH  ·  STK {account_no or 'mặc định'}  ·  {len(txs)} GD")
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
        credit = str(g(tx, "creditAmount", default="0") or "0").replace(",", "")
        debit = str(g(tx, "debitAmount", default="0") or "0").replace(",", "")
        try:
            c_amt = float(credit or 0)
            d_amt = float(debit or 0)
        except Exception:
            c_amt, d_amt = 0.0, 0.0
        is_in = c_amt > 0
        amt = c_amt if is_in else d_amt
        label = "VÀO" if is_in else "RA"
        col = C.GRN if is_in else C.YEL
        sign = "+" if is_in else "-"
        date = str(g(tx, "transactionDate", "postingDate", default=""))[:19]
        desc = str(g(tx, "description", default=""))[:40]
        bal = g(tx, "availableBalance", "balance", default=None)
        print(
            t(col, f"  {i:<4}{label:<6}{sign}{money(amt):<15}")
            + t(C.W, f"{date:<22}")
            + t(C.GRAY, desc)
        )
        if bal is not None:
            print(t(C.TEAL, f"      Số dư sau GD: {money(bal)}"))
    print(t(C.CYN, "  " + "─" * 70))
    print(t(C.GRAY, f"  Tổng: {len(txs)} giao dịch (tối đa ~90 ngày theo MB)"))


# ─────────── 01 SỐ DƯ + CHỌN STK ───────────
def feat_balance(mb) -> None:
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

        for i, a in enumerate(accts, 1):
            no = g(a, "acctNo", "accountNo", default="?")
            bal = g(a, "currentBalance", "balance", "availableBalance", default=0)
            alias = g(a, "acctAlias", "alias", default="") or ""
            cur = g(a, "currency", default="VND")
            print(t(C.CYN, f"  {i:02}") + t(C.W, f"  STK: {no}"))
            if alias:
                print(t(C.GRAY, f"      Tên: {alias}"))
            print(t(C.GRN + C.B, f"      Số dư: {money(bal)} {cur}"))
            print()

        print(t(C.W, "  Nhập số STK để xem lịch sử (từ trước đến nay)"))
        print(t(C.GRAY, "  Enter (trống) để quay về menu chính"))
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
        show_history(mb, stk, days=90)
        pause("Nhấn Enter để chọn STK khác...")


def feat_history_days(mb, days: int) -> None:
    clear()
    logo()
    accts = get_accounts(mb)
    stk = g(accts[0], "acctNo", default=None) if accts else None
    show_history(mb, stk, days=days)
    pause()


def feat_user(mb) -> None:
    clear()
    logo()
    section("THÔNG TIN NGƯỜI DÙNG")
    try:
        info = mb.userinfo()
        labels = [
            ("Họ tên", "custName", "name", "fullName"),
            ("SĐT", "phone", "mobile", "phoneNumber"),
            ("Email", "email"),
            ("CIF", "cif", "cifNumber"),
            ("CMND/CCCD", "idNumber", "nationalId"),
        ]
        shown = False
        for label, *keys in labels:
            val = g(info, *keys, default=None)
            if val is not None and str(val).strip():
                print(t(C.CYN, f"  {label:<12}") + t(C.W, str(val)))
                shown = True
        if not shown:
            for k in dir(info):
                if k.startswith("_"):
                    continue
                try:
                    v = getattr(info, k)
                    if isinstance(v, (str, int, float)) and not callable(v):
                        print(t(C.CYN, f"  {k:<16}") + t(C.W, str(v)))
                        shown = True
                except Exception:
                    pass
        if not shown:
            print(t(C.YEL, "  (Không đọc được thông tin)"))
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
        if not cards:
            print(t(C.YEL, "  Không có thẻ"))
        for i, c_ in enumerate(cards, 1):
            no = g(c_, "cardNo", "cardNumber", default="?")
            typ = g(c_, "cardModule", "cardType", "cardClass", default="")
            st = g(c_, "cardStatus", "status", default="")
            print(t(C.CYN, f"  {i:02}") + t(C.W, f"  {no}"))
            print(t(C.GRAY, f"      Loại: {typ}  |  Trạng thái: {st}"))
            print()
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
        if not items:
            print(t(C.YEL, "  Không có sổ tiết kiệm"))
        for i, s in enumerate(items, 1):
            no = g(s, "accNo", "acctNo", "accountNo", default="?")
            bal = g(s, "balance", "currentBalance", "amount", default="")
            print(
                t(C.CYN, f"  {i:02}")
                + t(C.W, f"  {no}  ")
                + t(C.GRN, money(bal) if bal != "" else "")
            )
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
        if not items:
            print(t(C.YEL, "  Không có khoản vay"))
        for i, s in enumerate(items, 1):
            no = g(s, "loanNo", "accNo", "acctNo", default="?")
            amt = g(s, "amount", "balance", "outstanding", default="")
            print(
                t(C.CYN, f"  {i:02}")
                + t(C.W, f"  {no}  ")
                + t(C.YEL, money(amt) if amt != "" else "")
            )
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_loyalty(mb) -> None:
    clear()
    logo()
    section("LOYALTY / ĐIỂM")
    try:
        data = mb.getBalanceLoyalty()
        pts = g(data, "point", "balance", "loyaltyPoint", "totalPoint", default=None)
        if pts is not None:
            print(t(C.GRN + C.B, f"  Điểm: {pts}"))
        else:
            for k in dir(data):
                if k.startswith("_"):
                    continue
                v = getattr(data, k, None)
                if isinstance(v, (int, float, str)) and not callable(v):
                    print(t(C.CYN, f"  {k:<20}") + t(C.W, str(v)))
    except Exception as e:
        print(t(C.RED, f"  Lỗi: {e}"))
    pause()


def feat_interest(mb) -> None:
    clear()
    logo()
    section("LÃI SUẤT")
    try:
        data = mb.getInterestRate()
        for k in dir(data):
            if k.startswith("_"):
                continue
            v = getattr(data, k, None)
            if isinstance(v, (int, float, str)) and not callable(v):
                print(t(C.CYN, f"  {k:<20}") + t(C.W, str(v)))
            elif isinstance(v, list) and v:
                print(t(C.W, f"  {k}: {len(v)} mục"))
                for i, item in enumerate(v[:15], 1):
                    name = g(item, "name", "productName", "type", default=str(item)[:40])
                    rate = g(item, "rate", "interestRate", default="")
                    print(t(C.GRAY, f"    {i:02}  {name}  {rate}"))
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
        print(t(C.GRN, f"  Tổng: {len(banks)} ngân hàng\n"))
        for i, b in enumerate(banks, 1):
            code = g(b, "bankCode", "code", default="")
            name = g(b, "bankName", "name", default="")
            print(t(C.CYN, f"  {i:03}") + t(C.W, f"  {str(code):<8}  {name}"))
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
        if not items:
            print(t(C.YEL, "  Không có thụ hưởng / danh sách trống"))
        for i, b in enumerate(items, 1):
            name = g(b, "beneficiariesName", "name", "accountName", default="")
            acc = g(b, "accountNo", "acctNo", default="")
            bk = g(b, "bankName", "bankCode", default="")
            print(t(C.CYN, f"  {i:02}") + t(C.W, f"  {name}"))
            print(t(C.GRAY, f"      STK: {acc}  |  {bk}"))
            print()
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
        name = g(data, "accountName", "name", "custName", default="")
        acc = g(data, "accountNo", "acctNo", default="")
        bank = g(data, "bankName", "bankCode", default="")
        print()
        if name or acc:
            print(t(C.CYN, "  Tên TK : ") + t(C.W, str(name)))
            print(t(C.CYN, "  STK    : ") + t(C.W, str(acc)))
            print(t(C.CYN, "  NH     : ") + t(C.W, str(bank)))
        else:
            for k in dir(data):
                if k.startswith("_"):
                    continue
                v = getattr(data, k, None)
                if isinstance(v, (str, int, float)) and v:
                    print(t(C.CYN, f"  {k:<16}") + t(C.W, str(v)))
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
            qr = ctx.get_qr_code()
            if qr:
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
    section("THÔNG TIN ỨNG DỤNG")
    print(t(C.CYN, "  Ứng dụng : ") + t(C.W, "MB BANK Client"))
    print(t(C.CYN, "  Tác giả  : ") + t(C.GRN, "Ontop"))
    print(t(C.CYN, "  Phiên bản: ") + t(C.W, "2.0"))
    pause()


# ─────────── MENU CHÍNH ───────────
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
        print()
        choice = tty_input(t(C.CYN, "  Chọn chức năng (0): ")).strip()

        try:
            if choice in ("0", "00", ""):
                print(t(C.MB, "\n  Tạm biệt.\n"))
                break
            elif choice in ("1", "01"):
                feat_balance(mb)
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
