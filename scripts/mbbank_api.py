#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MB BANK · Full Client (thedtvn/MBBank · mbbank-lib)
Không qua API cloud — gọi trực tiếp MB như lib gốc.

Cài + chạy 1 dòng:
  pip install -q mbbank-lib && \\
  MB_USERNAME='sdt' MB_PASSWORD='mk' \\
  python3 <(curl -fsSL https://raw.githubusercontent.com/ontopcommunity/nminhontop/main/scripts/mbbank_api.py)

Hoặc:
  curl -fsSL ... -o mbbank_api.py && pip install -q mbbank-lib && python3 mbbank_api.py
"""
from __future__ import annotations

import getpass
import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta
from typing import Any, List, Optional

# ═══════════════════════ COLORS (nổi trên nền đen) ═══════════════════════
class C:
    R = "\033[0m"
    B = "\033[1m"
    D = "\033[2m"
    # MB BANK — xanh dương đậm / sáng trên nền đen
    MB = "\033[1;38;5;33m"
    MB2 = "\033[1;38;5;27m"
    MB3 = "\033[1;38;5;39m"
    # rainbow
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
    W = "\033[1;97m"
    G = "\033[1;92m"
    RED = "\033[1;91m"
    YEL = "\033[1;93m"
    CYN = "\033[1;96m"
    MAG = "\033[1;95m"
    GRAY = "\033[38;5;250m"
    DIM = "\033[38;5;240m"
    ORNG = "\033[1;38;5;214m"
    LIME = "\033[1;38;5;118m"
    PINK = "\033[1;38;5;213m"
    TEAL = "\033[1;38;5;44m"


def ok_color() -> bool:
    return sys.stdout.isatty() and not os.getenv("NO_COLOR")


def t(code: str, s: str) -> str:
    return f"{code}{s}{C.R}" if ok_color() else s


def rb(s: str, off: int = 0) -> str:
    if not ok_color():
        return s
    return "".join(f"{C.RB[(off + i) % len(C.RB)]}{ch}" for i, ch in enumerate(s)) + C.R


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


def box(title: str, lines: List[str], width: int = 66) -> None:
    print(rb("╔" + "═" * width + "╗", 0))
    pad = max(0, width - len(title))
    L, R = pad // 2, pad - pad // 2
    print(rb("║", 1) + t(C.MB, " " * L + title + " " * R) + rb("║", 3))
    print(rb("╠" + "═" * width + "╣", 2))
    for line in lines:
        sp = max(0, width - vis_len(line))
        print(rb("║", 4) + line + " " * sp + rb("║", 6))
    print(rb("╚" + "═" * width + "╝", 5))


def tty_input(prompt: str = "") -> str:
    if sys.stdin.isatty():
        return input(prompt)
    try:
        with open("/dev/tty", "r") as tty:
            sys.stdout.write(prompt)
            sys.stdout.flush()
            return tty.readline().rstrip("\n\r")
    except Exception as e:
        raise EOFError(f"Không đọc được bàn phím: {e}") from e


def pause() -> None:
    try:
        tty_input(t(C.GRAY, "  ⏎  Enter để về menu... "))
    except EOFError:
        pass


def money(n: Any) -> str:
    try:
        v = int(float(str(n).replace(",", "").replace("đ", "").strip() or 0))
        return f"{v:,}".replace(",", ".") + "đ"
    except Exception:
        return str(n)


def gattr(obj: Any, *names: str, default: Any = None) -> Any:
    for n in names:
        if obj is None:
            break
        if isinstance(obj, dict) and n in obj:
            return obj[n]
        if hasattr(obj, n):
            return getattr(obj, n)
    return default


def dump(obj: Any, limit: int = 2500) -> str:
    try:
        if hasattr(obj, "model_dump"):
            data = obj.model_dump()
        elif hasattr(obj, "dict"):
            data = obj.dict()
        elif hasattr(obj, "__dict__"):
            data = {k: v for k, v in vars(obj).items() if not k.startswith("_")}
        else:
            data = obj
        s = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    except Exception:
        s = str(obj)
    return s if len(s) <= limit else s[:limit] + "\n… (cắt)"


# ═══════════════════════ SESSION ═══════════════════════
_mb = None


def ensure_lib():
    try:
        import mbbank  # noqa: F401
        return True
    except ImportError:
        print(t(C.YEL, "  ⚠  Chưa có mbbank-lib — đang cài..."))
        import subprocess

        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "mbbank-lib"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(t(C.RED, "  ✖ pip install mbbank-lib thất bại"))
            print(t(C.GRAY, r.stderr[-400:] if r.stderr else ""))
            print(t(C.YEL, "  Thử: pip install mbbank-lib"))
            return False
        try:
            import mbbank  # noqa: F401
            return True
        except ImportError:
            print(t(C.RED, "  ✖ Vẫn không import được mbbank"))
            return False


def get_mb():
    global _mb
    if _mb is not None:
        return _mb
    if not ensure_lib():
        return None
    import mbbank

    user = os.getenv("MB_USERNAME") or os.getenv("MB_USER") or ""
    pwd = os.getenv("MB_PASSWORD") or os.getenv("MB_PASS") or ""
    if not user:
        user = tty_input(t(C.MB3, "  Username/SĐT: ")).strip()
    if not pwd:
        if sys.stdin.isatty():
            pwd = getpass.getpass(t(C.MB3, "  Password: "))
        else:
            pwd = tty_input(t(C.MB3, "  Password: ")).strip()
    print(t(C.CYN, "  ⏳ Đăng nhập MB Bank (OCR captcha)..."))
    t0 = time.time()
    try:
        _mb = mbbank.MBBank(username=user, password=pwd)
        print(t(C.G, f"  ✔  Login OK · {int((time.time() - t0) * 1000)}ms"))
        return _mb
    except Exception as e:
        print(t(C.RED, f"  ✖ Login fail: {e}"))
        return None


def banner() -> None:
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
    print(rb("  ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦ ✦"))
    print()
    box(
        " MB BANK  ·  FULL CLIENT (mbbank-lib) ",
        [
            t(C.GRAY, "  Lib gốc: ") + t(C.CYN, "github.com/thedtvn/MBBank"),
            t(C.GRAY, "  Cơ chế:  ")
            + t(C.W, "trực tiếp MB API")
            + t(C.GRAY, "  ·  không qua cloud proxy"),
            t(C.GRAY, "  Time:    ") + t(C.W, datetime.now().strftime("%d/%m/%Y %H:%M:%S")),
        ],
        width=66,
    )
    print()


# ═══════════════════════ FEATURES ═══════════════════════
def feat_balance(mb) -> None:
    print(t(C.CYN, "  ⏳ getBalance()..."))
    data = mb.getBalance()
    accts = gattr(data, "acct_list", "acctList", default=[]) or []
    lines = [t(C.MB, "  💰  TÀI KHOẢN")]
    if not accts:
        lines.append(t(C.YEL, "  (Không có tài khoản)"))
    for a in accts:
        no = gattr(a, "acctNo", "accountNo", default="?")
        bal = gattr(a, "currentBalance", "balance", "availableBalance", default="?")
        alias = gattr(a, "acctAlias", "alias", default="")
        cur = gattr(a, "currency", default="VND")
        lines.append(t(C.W, f"  ▸ {no}") + (t(C.GRAY, f"  ({alias})") if alias else ""))
        lines.append(t(C.LIME, f"    {money(bal)} {cur}"))
    box(" SỐ DƯ ", lines, 66)
    print(t(C.DIM, dump(data, 1200)))


def feat_history(mb, days: int = 14) -> None:
    to_d = datetime.now()
    fr_d = to_d - timedelta(days=days)
    print(t(C.CYN, f"  ⏳ getTransactionAccountHistory({days} ngày)..."))
    hist = mb.getTransactionAccountHistory(from_date=fr_d, to_date=to_d)
    txs = gattr(hist, "transactionHistoryList", default=[]) or []
    print()
    print(rb(f"  ── LỊCH SỬ {fr_d.date()} → {to_d.date()} ({len(txs)} GD) ──"))
    print()
    if not txs:
        print(t(C.YEL, "  (Trống)"))
        return
    for i, tx in enumerate(txs[:40], 1):
        credit = gattr(tx, "creditAmount", default="0") or "0"
        debit = gattr(tx, "debitAmount", default="0") or "0"
        try:
            c_amt = float(str(credit).replace(",", "") or 0)
            d_amt = float(str(debit).replace(",", "") or 0)
        except Exception:
            c_amt, d_amt = 0, 0
        is_in = c_amt > 0
        amt = c_amt if is_in else d_amt
        icon = "🟢 IN " if is_in else "🔴 OUT"
        col = C.LIME if is_in else C.ORNG
        date = gattr(tx, "transactionDate", "postingDate", default="")
        desc = str(gattr(tx, "description", default=""))[:70]
        bal = gattr(tx, "availableBalance", "balance", default=None)
        ref = gattr(tx, "refNo", default="")
        print(f"  {rb('▌', i)} {t(col, icon)} {t(C.W, money(amt))}  {t(C.GRAY, str(date))}")
        print(f"     {t(C.GRAY, desc)}")
        extra = []
        if bal is not None:
            extra.append(f"SD: {money(bal)}")
        if ref:
            extra.append(f"ref: {ref}")
        if extra:
            print(f"     {t(C.TEAL, ' · '.join(extra))}")
        if i < min(len(txs), 40):
            print(t(C.DIM, "  · · · · · · · · · · · · · · · · · · · · · · · ·"))
    if len(txs) > 40:
        print(t(C.YEL, f"  … còn {len(txs) - 40} GD"))


def feat_userinfo(mb) -> None:
    print(t(C.CYN, "  ⏳ userinfo()..."))
    info = mb.userinfo()
    box(" USER INFO ", [t(C.W, "  " + line) for line in dump(info, 2000).splitlines()], 66)


def feat_cards(mb) -> None:
    print(t(C.CYN, "  ⏳ getCardList()..."))
    data = mb.getCardList()
    cards = gattr(data, "cardList", default=[]) or []
    if not cards:
        print(t(C.YEL, "  Không có thẻ"))
        return
    lines = []
    for c_ in cards:
        no = gattr(c_, "cardNo", "cardNumber", default="?")
        typ = gattr(c_, "cardModule", "cardType", "cardClass", default="")
        st = gattr(c_, "cardStatus", "status", default="")
        lines.append(t(C.W, f"  ▸ {no}"))
        lines.append(t(C.GRAY, f"    type={typ}  status={st}"))
    box(" DANH SÁCH THẺ ", lines, 66)


def feat_saving(mb) -> None:
    print(t(C.CYN, "  ⏳ getSavingList()..."))
    data = mb.getSavingList()
    print(t(C.W, dump(data, 2000)))


def feat_loan(mb) -> None:
    print(t(C.CYN, "  ⏳ getLoanList()..."))
    data = mb.getLoanList()
    print(t(C.W, dump(data, 2000)))


def feat_loyalty(mb) -> None:
    print(t(C.CYN, "  ⏳ getBalanceLoyalty()..."))
    data = mb.getBalanceLoyalty()
    print(t(C.W, dump(data, 1500)))


def feat_interest(mb) -> None:
    print(t(C.CYN, "  ⏳ getInterestRate()..."))
    data = mb.getInterestRate()
    print(t(C.W, dump(data, 1500)))


def feat_banklist(mb) -> None:
    print(t(C.CYN, "  ⏳ getBankList()..."))
    data = mb.getBankList()
    banks = gattr(data, "listBank", "bankList", default=[]) or []
    print(t(C.G, f"  {len(banks)} ngân hàng"))
    for i, b in enumerate(banks[:30], 1):
        name = gattr(b, "bankName", "name", default="")
        code = gattr(b, "bankCode", "code", default="")
        print(t(C.W, f"  {i:2}. {code:8}  {name}"))
    if len(banks) > 30:
        print(t(C.GRAY, f"  … +{len(banks) - 30} bank"))


def feat_beneficiary(mb) -> None:
    print(t(C.CYN, "  ⏳ getFavorBeneficiaryList() / getSavedBeneficiary()..."))
    try:
        a = mb.getFavorBeneficiaryList()
        print(t(C.MB, "  --- Favor ---"))
        print(t(C.W, dump(a, 1500)))
    except Exception as e:
        print(t(C.YEL, f"  favor: {e}"))
    try:
        b = mb.getSavedBeneficiary()
        print(t(C.MB, "  --- Saved ---"))
        print(t(C.W, dump(b, 1500)))
    except Exception as e:
        print(t(C.YEL, f"  saved: {e}"))


def feat_phone(mb) -> None:
    phone = tty_input(t(C.MB3, "  SĐT cần tra: ")).strip()
    if not phone:
        return
    print(t(C.CYN, f"  ⏳ getAccountByPhone({phone})..."))
    data = mb.getAccountByPhone(phone)
    print(t(C.W, dump(data, 1500)))


def feat_transfer(mb) -> None:
    print(t(C.RED + C.B, "  ⚠  CHUYỂN TIỀN THẬT — cần OTP trên app MB"))
    print(t(C.YEL, "  Nhập sai STK/số tiền có thể mất tiền. Ctrl+C để hủy.\n"))
    try:
        bal = mb.getBalance()
        accts = gattr(bal, "acct_list", "acctList", default=[]) or []
        if not accts:
            print(t(C.RED, "  Không có tài khoản nguồn"))
            return
        print(t(C.MB, "  Tài khoản nguồn:"))
        for i, a in enumerate(accts, 1):
            print(
                t(
                    C.W,
                    f"  {i}. {gattr(a, 'acctNo')}  {money(gattr(a, 'currentBalance', 'balance', default=0))}",
                )
            )
        idx = int(tty_input(t(C.MB3, "  Chọn TK nguồn [1]: ")).strip() or "1") - 1
        src = gattr(accts[idx], "acctNo")

        banks = mb.getBankList()
        blist = gattr(banks, "listBank", default=[]) or []
        code = tty_input(t(C.MB3, "  Bank code (vd MB, VCB, TCB): ")).strip().upper()
        bank = next((b for b in blist if str(gattr(b, "bankCode", default="")).upper() == code), None)
        if not bank:
            print(t(C.RED, "  Không tìm thấy bank code"))
            return
        print(t(C.G, f"  → {gattr(bank, 'bankName')} ({code})"))

        dest = tty_input(t(C.MB3, "  STK / nickname nhận: ")).strip()
        amount = int(tty_input(t(C.MB3, "  Số tiền (VND): ")).strip())
        msg = tty_input(t(C.MB3, "  Nội dung CK: ")).strip() or "MB"

        print(t(C.CYN, "  ⏳ makeTransfer()..."))
        ctx = mb.makeTransfer(
            src_account=src,
            dest_account=dest,
            bank_code=code,
            amount=amount,
            message=msg,
        )
        auth_list = ctx.get_auth_list()
        methods = gattr(auth_list, "authList", default=[]) or []
        print(t(C.MB, "  Phương thức xác thực:"))
        for i, m in enumerate(methods, 1):
            print(t(C.W, f"  {i}. {gattr(m, 'name', default=m)}"))
        mi = int(tty_input(t(C.MB3, "  Chọn auth [1]: ")).strip() or "1") - 1
        method = methods[mi]

        try:
            qr_data = ctx.get_qr_code()
            if qr_data:
                print(t(C.YEL, "  QR/DOTP data (mở app MB quét nếu cần):"))
                print(t(C.GRAY, str(qr_data)[:200]))
                try:
                    import qrcode

                    qrcode.make(qr_data).show()
                except Exception:
                    pass
        except Exception:
            pass

        otp = tty_input(t(C.MB3, f"  OTP / mã ({gattr(method, 'name')}): ")).strip()
        result = ctx.transfer(otp=otp, auth_type=method)
        print(t(C.G, "  ✔  Kết quả:"))
        print(t(C.W, dump(result, 2000)))
    except Exception as e:
        print(t(C.RED, f"  ✖ Transfer lỗi: {e}"))
        traceback.print_exc()


def feat_raw(mb) -> None:
    print(t(C.GRAY, "  Gọi method bất kỳ trên object MBBank"))
    name = tty_input(t(C.MB3, "  Tên method (vd getCardList): ")).strip()
    if not name or not hasattr(mb, name):
        print(t(C.RED, "  Method không tồn tại"))
        print(t(C.GRAY, "  Gợi ý: " + ", ".join(
            n for n in dir(mb) if not n.startswith("_") and callable(getattr(mb, n, None))
        )[:500]))
        return
    fn = getattr(mb, name)
    print(t(C.CYN, f"  ⏳ {name}()..."))
    try:
        # try no-arg first
        out = fn()
        print(t(C.W, dump(out, 3000)))
    except TypeError:
        print(t(C.YEL, "  Method cần tham số — dùng menu chuyên biệt hoặc sửa script"))
    except Exception as e:
        print(t(C.RED, f"  ✖ {e}"))


def menu() -> None:
    banner()
    mb = get_mb()
    if mb is None:
        print(t(C.RED, "  Không đăng nhập được. Thoát."))
        return

    while True:
        print()
        box(
            " MENU  ·  TOÀN BỘ TÍNH NĂNG ",
            [
                t(C.LIME, "  [1]") + t(C.W, "  Số dư (getBalance)"),
                t(C.LIME, "  [2]") + t(C.W, "  Lịch sử GD 14 ngày"),
                t(C.LIME, "  [3]") + t(C.W, "  Lịch sử GD 30 ngày"),
                t(C.CYN, "  [4]") + t(C.W, "  User info"),
                t(C.CYN, "  [5]") + t(C.W, "  Danh sách thẻ (getCardList)"),
                t(C.CYN, "  [6]") + t(C.W, "  Tiết kiệm (getSavingList)"),
                t(C.CYN, "  [7]") + t(C.W, "  Khoản vay (getLoanList)"),
                t(C.CYN, "  [8]") + t(C.W, "  Loyalty points"),
                t(C.CYN, "  [9]") + t(C.W, "  Lãi suất (getInterestRate)"),
                t(C.MAG, "  [10]") + t(C.W, " Danh sách NH (getBankList)"),
                t(C.MAG, "  [11]") + t(C.W, " Thụ hưởng đã lưu"),
                t(C.MAG, "  [12]") + t(C.W, " Tra STK theo SĐT"),
                t(C.ORNG, "  [13]") + t(C.W, " CHUYỂN TIỀN (makeTransfer + OTP)"),
                t(C.YEL, "  [14]") + t(C.W, " Gọi method tùy ý (raw)"),
                t(C.GRAY, "  [0]") + t(C.GRAY, "  Thoát"),
            ],
            66,
        )
        print()
        try:
            choice = tty_input(t(C.MB, "  ❯ ") + t(C.W, "Chọn: ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        print()
        try:
            if choice == "0":
                print(t(C.MB, "  MB BANK client closed."))
                break
            elif choice == "1":
                feat_balance(mb)
            elif choice == "2":
                feat_history(mb, 14)
            elif choice == "3":
                feat_history(mb, 30)
            elif choice == "4":
                feat_userinfo(mb)
            elif choice == "5":
                feat_cards(mb)
            elif choice == "6":
                feat_saving(mb)
            elif choice == "7":
                feat_loan(mb)
            elif choice == "8":
                feat_loyalty(mb)
            elif choice == "9":
                feat_interest(mb)
            elif choice == "10":
                feat_banklist(mb)
            elif choice == "11":
                feat_beneficiary(mb)
            elif choice == "12":
                feat_phone(mb)
            elif choice == "13":
                feat_transfer(mb)
            elif choice == "14":
                feat_raw(mb)
            else:
                print(t(C.YEL, "  Chọn 0–14"))
                continue
        except Exception as e:
            print(t(C.RED, f"  ✖ Lỗi: {e}"))
            traceback.print_exc()
        pause()


def main(argv: List[str]) -> int:
    if "--help" in argv or "-h" in argv:
        print(__doc__)
        return 0
    # non-interactive shortcuts
    if "--balance" in argv or "--once" in argv:
        banner()
        mb = get_mb()
        if not mb:
            return 1
        feat_balance(mb)
        feat_history(mb, 14)
        return 0
    menu()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
