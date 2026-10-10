#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MB BANK Client — mbbank-lib (thedtvn/MBBank)
Không lộ JSON. Chọn STK xem lịch sử full.

Chạy:
  pip install -q mbbank-lib
  MB_USERNAME=sdt MB_PASSWORD=mk python3 mbbank_api.py
"""
from __future__ import annotations

import getpass
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from typing import Any, List, Optional

# ─────────── ANSI (nổi trên nền đen) ───────────
class C:
    R = "\033[0m"
    B = "\033[1m"
    MB = "\033[1;38;5;27m"      # xanh dương đậm — logo
    MB2 = "\033[1;38;5;39m"
    W = "\033[1;97m"
    G = "\033[1;92m"
    RED = "\033[1;91m"
    YEL = "\033[1;93m"
    CYN = "\033[1;96m"
    MAG = "\033[1;95m"
    GRAY = "\033[38;5;245m"
    ORNG = "\033[1;38;5;214m"
    LIME = "\033[1;38;5;118m"
    TEAL = "\033[1;38;5;44m"
    PINK = "\033[1;38;5;213m"
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


def _c() -> bool:
    return sys.stdout.isatty() and not os.getenv("NO_COLOR")


def t(code: str, s: str) -> str:
    return f"{code}{s}{C.R}" if _c() else s


def rb(s: str, off: int = 0) -> str:
    if not _c():
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


def pause(msg: str = "Enter de ve menu...") -> None:
    try:
        tty_input(t(C.GRAY, f"\n  [ {msg} ] "))
    except EOFError:
        pass


def money(n: Any) -> str:
    try:
        v = int(float(str(n).replace(",", "").replace("đ", "").strip() or 0))
        return f"{v:,}".replace(",", ".") + "d"
    except Exception:
        return str(n) if n is not None else "—"


def g(obj: Any, *keys: str, default: Any = None) -> Any:
    for k in keys:
        if obj is None:
            return default
        if isinstance(obj, dict):
            if k in obj:
                return obj[k]
        elif hasattr(obj, k):
            return getattr(obj, k)
    return default


def line(char: str = "─", n: int = 58) -> None:
    print(rb("  " + char * n))


def header(title: str) -> None:
    line("═")
    print(t(C.MB2 + C.B, f"  {title}"))
    line("═")


# ─────────── LOGO (giữ nguyên chữ to) ───────────
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
    print(rb("  ✦  FULL CLIENT  ·  mbbank-lib  ·  thedtvn/MBBank  ✦"))
    print(t(C.GRAY, f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"))
    print()


# ─────────── SESSION ───────────
_mb = None


def ensure_lib() -> bool:
    try:
        import mbbank  # noqa: F401
        return True
    except ImportError:
        print(t(C.YEL, "  Dang cai mbbank-lib..."))
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "mbbank-lib"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(t(C.RED, "  Cai that bai. Chay: pip install mbbank-lib"))
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
        user = tty_input(t(C.CYN, "  Username / SDT: ")).strip()
    if not pwd:
        if sys.stdin.isatty():
            pwd = getpass.getpass(t(C.CYN, "  Password: "))
        else:
            pwd = tty_input(t(C.CYN, "  Password: ")).strip()

    print(t(C.YEL, "  Dang dang nhap MB Bank..."))
    t0 = time.time()
    try:
        _mb = mbbank.MBBank(username=user, password=pwd)
        print(t(C.G, f"  OK — login thanh cong ({int((time.time()-t0)*1000)} ms)\n"))
        return _mb
    except Exception as e:
        print(t(C.RED, f"  Login that bai: {e}"))
        return None


def get_accounts(mb) -> List[Any]:
    data = mb.getBalance()
    return list(g(data, "acct_list", "acctList", default=[]) or [])


# ─────────── HIỂN THỊ GD (không JSON) ───────────
def show_history(mb, account_no: Optional[str], days: int = 90) -> None:
    to_d = datetime.now()
    fr_d = to_d - timedelta(days=min(days, 90))
    print(t(C.YEL, f"  Dang lay lich su {fr_d.strftime('%d/%m/%Y')} -> {to_d.strftime('%d/%m/%Y')}..."))
    try:
        # một số bản lib nhận accountNo
        try:
            hist = mb.getTransactionAccountHistory(
                from_date=fr_d, to_date=to_d, accountNo=account_no
            )
        except TypeError:
            hist = mb.getTransactionAccountHistory(from_date=fr_d, to_date=to_d)
    except Exception as e:
        print(t(C.RED, f"  Loi lay lich su: {e}"))
        return

    txs = list(g(hist, "transactionHistoryList", default=[]) or [])
    header(f"LICH SU GD  ·  STK {account_no or 'mac dinh'}  ·  {len(txs)} GD")
    if not txs:
        print(t(C.YEL, "  (Khong co giao dich)"))
        return

    print(
        t(C.GRAY, f"  {'#':<4} {'Loai':<5} {'So tien':<16} {'Thoi gian':<20} Noi dung")
    )
    line("─")
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
        kind = "IN" if is_in else "OUT"
        col = C.LIME if is_in else C.ORNG
        sign = "+" if is_in else "-"
        date = str(g(tx, "transactionDate", "postingDate", default=""))[:19]
        desc = str(g(tx, "description", default=""))[:42]
        bal = g(tx, "availableBalance", "balance", default=None)
        print(
            t(col, f"  {i:<4} {kind:<5} {sign}{money(amt):<15} ")
            + t(C.W, f"{date:<20} ")
            + t(C.GRAY, desc)
        )
        if bal is not None:
            print(t(C.TEAL, f"       SD sau GD: {money(bal)}"))
    line("─")
    print(t(C.GRAY, f"  Tong: {len(txs)} giao dich (toi da ~90 ngay theo MB)"))


# ─────────── MENU SỐ DƯ + CHỌN STK ───────────
def menu_balance(mb) -> None:
    while True:
        clear()
        logo()
        header("SO DU  ·  DANH SACH STK")
        try:
            accts = get_accounts(mb)
        except Exception as e:
            print(t(C.RED, f"  Loi getBalance: {e}"))
            pause()
            return

        if not accts:
            print(t(C.YEL, "  Khong tim thay tai khoan"))
            pause()
            return

        print()
        for i, a in enumerate(accts, 1):
            no = g(a, "acctNo", "accountNo", default="?")
            bal = g(a, "currentBalance", "balance", "availableBalance", default=0)
            alias = g(a, "acctAlias", "alias", default="") or ""
            cur = g(a, "currency", default="VND")
            print(t(C.CYN + C.B, f"  [{i}]") + t(C.W, f"  STK: {no}"))
            if alias:
                print(t(C.GRAY, f"       Ten: {alias}"))
            print(t(C.LIME + C.B, f"       So du: {money(bal)} {cur}"))
            print()

        line("─")
        print(t(C.W, "  Nhap so STK de xem lich su GD (tu truoc den nay)"))
        print(t(C.GRAY, "  Enter (trong) de quay ve menu chinh"))
        print()
        choice = tty_input(t(C.MB2, "  Chon STK > ")).strip()
        if not choice:
            return
        try:
            idx = int(choice) - 1
            if idx < 0 or idx >= len(accts):
                print(t(C.RED, "  So khong hop le"))
                time.sleep(1)
                continue
        except ValueError:
            print(t(C.RED, "  Nhap so"))
            time.sleep(1)
            continue

        stk = g(accts[idx], "acctNo", "accountNo", default=None)
        clear()
        logo()
        show_history(mb, stk, days=90)
        pause("Enter de chon STK khac / ve...")


# ─────────── CÁC TÍNH NĂNG KHÁC (không JSON) ───────────
def feat_history_quick(mb, days: int) -> None:
    clear()
    logo()
    accts = get_accounts(mb)
    stk = g(accts[0], "acctNo", default=None) if accts else None
    show_history(mb, stk, days=days)
    pause()


def feat_cards(mb) -> None:
    clear()
    logo()
    header("DANH SACH THE")
    try:
        data = mb.getCardList()
        cards = list(g(data, "cardList", default=[]) or [])
        if not cards:
            print(t(C.YEL, "  Khong co the"))
        for i, c_ in enumerate(cards, 1):
            no = g(c_, "cardNo", "cardNumber", default="?")
            typ = g(c_, "cardModule", "cardType", "cardClass", default="")
            st = g(c_, "cardStatus", "status", default="")
            print(t(C.W, f"  [{i}]  {no}"))
            print(t(C.GRAY, f"       Loai: {typ}  |  Trang thai: {st}"))
            print()
    except Exception as e:
        print(t(C.RED, f"  Loi: {e}"))
    pause()


def feat_user(mb) -> None:
    clear()
    logo()
    header("THONG TIN USER")
    try:
        info = mb.userinfo()
        # in field-by-field, không dump JSON
        fields = [
            ("Cust name", "custName", "name", "fullName"),
            ("Phone", "phone", "mobile", "phoneNumber"),
            ("Email", "email"),
            ("CIF", "cif", "cifNumber"),
            ("ID", "idNumber", "nationalId"),
        ]
        shown = False
        for label, *keys in fields:
            val = g(info, *keys, default=None)
            if val is not None and str(val).strip():
                print(t(C.CYN, f"  {label:<12}") + t(C.W, str(val)))
                shown = True
        if not shown:
            # fallback: vài attribute public
            for k in dir(info):
                if k.startswith("_"):
                    continue
                try:
                    v = getattr(info, k)
                    if v is None or callable(v):
                        continue
                    if isinstance(v, (str, int, float)):
                        print(t(C.CYN, f"  {k:<16}") + t(C.W, str(v)))
                        shown = True
                except Exception:
                    pass
        if not shown:
            print(t(C.YEL, "  (Khong doc duoc truong hien thi)"))
    except Exception as e:
        print(t(C.RED, f"  Loi: {e}"))
    pause()


def feat_banks(mb) -> None:
    clear()
    logo()
    header("DANH SACH NGAN HANG")
    try:
        data = mb.getBankList()
        banks = list(g(data, "listBank", "bankList", default=[]) or [])
        print(t(C.G, f"  Tong: {len(banks)} ngan hang\n"))
        for i, b in enumerate(banks, 1):
            code = g(b, "bankCode", "code", default="")
            name = g(b, "bankName", "name", default="")
            print(t(C.W, f"  {i:3}. {str(code):<8}  {name}"))
    except Exception as e:
        print(t(C.RED, f"  Loi: {e}"))
    pause()


def feat_saving(mb) -> None:
    clear()
    logo()
    header("TIET KIEM")
    try:
        data = mb.getSavingList()
        items = list(
            g(data, "savingList", "list", "osaList", default=None)
            or g(data, "sbaList", default=[])
            or []
        )
        if not items:
            # thử in từng attr đơn giản
            print(t(C.YEL, "  Khong co so tiet kiem / hoac dinh dang khac"))
            for k in dir(data):
                if k.startswith("_"):
                    continue
                v = getattr(data, k, None)
                if isinstance(v, list) and v:
                    items = v
                    break
        for i, s in enumerate(items, 1):
            no = g(s, "accNo", "acctNo", "accountNo", default="?")
            bal = g(s, "balance", "currentBalance", "amount", default="")
            print(t(C.W, f"  [{i}]  {no}  {money(bal) if bal != '' else ''}"))
    except Exception as e:
        print(t(C.RED, f"  Loi: {e}"))
    pause()


def feat_loan(mb) -> None:
    clear()
    logo()
    header("KHOAN VAY")
    try:
        data = mb.getLoanList()
        items = list(g(data, "loanList", "list", default=[]) or [])
        if not items:
            print(t(C.YEL, "  Khong co khoan vay"))
        for i, s in enumerate(items, 1):
            no = g(s, "loanNo", "accNo", "acctNo", default="?")
            amt = g(s, "amount", "balance", "outstanding", default="")
            print(t(C.W, f"  [{i}]  {no}  {money(amt) if amt != '' else ''}"))
    except Exception as e:
        print(t(C.RED, f"  Loi: {e}"))
    pause()


def feat_loyalty(mb) -> None:
    clear()
    logo()
    header("LOYALTY / DIEM")
    try:
        data = mb.getBalanceLoyalty()
        pts = g(data, "point", "balance", "loyaltyPoint", "totalPoint", default=None)
        if pts is not None:
            print(t(C.LIME + C.B, f"  Diem: {pts}"))
        else:
            for k in dir(data):
                if k.startswith("_"):
                    continue
                v = getattr(data, k, None)
                if isinstance(v, (int, float, str)) and not callable(v):
                    print(t(C.CYN, f"  {k:<20}") + t(C.W, str(v)))
    except Exception as e:
        print(t(C.RED, f"  Loi: {e}"))
    pause()


def feat_phone(mb) -> None:
    clear()
    logo()
    header("TRA STK THEO SDT")
    phone = tty_input(t(C.CYN, "  Nhap SDT: ")).strip()
    if not phone:
        return
    try:
        data = mb.getAccountByPhone(phone)
        name = g(data, "accountName", "name", "custName", default="")
        acc = g(data, "accountNo", "acctNo", default="")
        bank = g(data, "bankName", "bankCode", default="")
        print()
        if name or acc:
            print(t(C.W, f"  Ten TK : {name}"))
            print(t(C.W, f"  STK    : {acc}"))
            print(t(C.W, f"  NH     : {bank}"))
        else:
            for k in dir(data):
                if k.startswith("_"):
                    continue
                v = getattr(data, k, None)
                if isinstance(v, (str, int, float)) and v:
                    print(t(C.CYN, f"  {k:<16}") + t(C.W, str(v)))
    except Exception as e:
        print(t(C.RED, f"  Loi: {e}"))
    pause()


def feat_beneficiary(mb) -> None:
    clear()
    logo()
    header("THU HUONG DA LUU")
    try:
        try:
            data = mb.getFavorBeneficiaryList()
        except Exception:
            data = mb.getSavedBeneficiary()
        items = list(
            g(data, "beneficiaries", "list", "favorBeneficiaryList", default=[]) or []
        )
        if not items:
            print(t(C.YEL, "  Khong co thu huong / danh sach trong"))
        for i, b in enumerate(items, 1):
            name = g(b, "beneficiariesName", "name", "accountName", default="")
            acc = g(b, "accountNo", "acctNo", default="")
            bk = g(b, "bankName", "bankCode", default="")
            print(t(C.W, f"  [{i}]  {name}"))
            print(t(C.GRAY, f"       STK: {acc}  |  {bk}"))
            print()
    except Exception as e:
        print(t(C.RED, f"  Loi: {e}"))
    pause()


def feat_transfer(mb) -> None:
    clear()
    logo()
    header("CHUYEN TIEN (can OTP app MB)")
    print(t(C.RED, "  Canh bao: giao dich that — kiem tra ky STK / so tien\n"))
    try:
        accts = get_accounts(mb)
        if not accts:
            print(t(C.RED, "  Khong co TK nguon"))
            pause()
            return
        for i, a in enumerate(accts, 1):
            print(
                t(
                    C.W,
                    f"  [{i}] {g(a,'acctNo')}  {money(g(a,'currentBalance','balance',default=0))}",
                )
            )
        idx = int(tty_input(t(C.CYN, "  TK nguon [1]: ")).strip() or "1") - 1
        src = g(accts[idx], "acctNo")
        code = tty_input(t(C.CYN, "  Bank code (MB/VCB/TCB...): ")).strip().upper()
        dest = tty_input(t(C.CYN, "  STK nhan: ")).strip()
        amount = int(tty_input(t(C.CYN, "  So tien: ")).strip())
        msg = tty_input(t(C.CYN, "  Noi dung: ")).strip() or "CK"

        print(t(C.YEL, "  Tao lenh chuyen..."))
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
            print(t(C.W, f"  [{i}] {g(m,'name',default=m)}"))
        mi = int(tty_input(t(C.CYN, "  Auth [1]: ")).strip() or "1") - 1
        method = methods[mi]
        try:
            qr = ctx.get_qr_code()
            if qr:
                print(t(C.GRAY, "  (Mo app MB quet QR/DOTP neu can)"))
        except Exception:
            pass
        otp = tty_input(t(C.CYN, "  Nhap OTP: ")).strip()
        result = ctx.transfer(otp=otp, auth_type=method)
        # chỉ báo thành công/thất bại, không dump object
        ok = g(result, "ok", "success", default=None)
        msg_r = g(result, "message", "msg", "description", default="")
        if ok is True or (msg_r and "success" in str(msg_r).lower()):
            print(t(C.G, f"  Thanh cong: {msg_r or 'OK'}"))
        else:
            print(t(C.YEL, f"  Ket qua: {msg_r or 'xem app MB de xac nhan'}"))
    except Exception as e:
        print(t(C.RED, f"  Loi: {e}"))
    pause()


# ─────────── MENU CHÍNH ───────────
def main_menu() -> None:
    clear()
    logo()
    mb = login()
    if mb is None:
        print(t(C.RED, "  Thoat."))
        return

    while True:
        clear()
        logo()
        line("═")
        print(t(C.MB2 + C.B, "  MENU CHINH"))
        line("═")
        print()
        items = [
            ("1", "So du + chon STK xem lich su full"),
            ("2", "Lich su GD 14 ngay (STK mac dinh)"),
            ("3", "Lich su GD 30 ngay"),
            ("4", "Thong tin user"),
            ("5", "Danh sach the"),
            ("6", "Tiet kiem"),
            ("7", "Khoan vay"),
            ("8", "Loyalty / diem"),
            ("9", "Danh sach ngan hang"),
            ("10", "Thu huong da luu"),
            ("11", "Tra STK theo SDT"),
            ("12", "Chuyen tien (OTP)"),
            ("0", "Thoat"),
        ]
        for num, label in items:
            col = C.LIME if num != "0" else C.GRAY
            print(t(col + C.B, f"  [{num:>2}]") + t(C.W, f"  {label}"))
        print()
        line("─")
        choice = tty_input(t(C.MB2, "  Chon > ")).strip()

        if choice == "0":
            print(t(C.MB, "\n  Tam biet.\n"))
            break
        elif choice == "1":
            menu_balance(mb)
        elif choice == "2":
            feat_history_quick(mb, 14)
        elif choice == "3":
            feat_history_quick(mb, 30)
        elif choice == "4":
            feat_user(mb)
        elif choice == "5":
            feat_cards(mb)
        elif choice == "6":
            feat_saving(mb)
        elif choice == "7":
            feat_loan(mb)
        elif choice == "8":
            feat_loyalty(mb)
        elif choice == "9":
            feat_banks(mb)
        elif choice == "10":
            feat_beneficiary(mb)
        elif choice == "11":
            feat_phone(mb)
        elif choice == "12":
            feat_transfer(mb)
        else:
            print(t(C.YEL, "  Sai lua chon"))
            time.sleep(0.8)


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(t(C.YEL, "\n  Huy.\n"))
