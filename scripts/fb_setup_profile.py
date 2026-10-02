#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup 4 FB acc: avatar khác nhau + 3 bài viết khác nhau mỗi acc.
Dùng Graph API token (EAAAA) trong fb_accounts.json.
Giữ cookie sống: refresh fb_dtsg + visit facebook.com định kỳ.
"""
from __future__ import annotations

import json, time, random, string, sys
from pathlib import Path
from typing import Dict, Any, List

import requests
from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))
from FacebookAPI import FacebookAPI

ACC_FILE = SCRIPT_DIR / "fb_accounts.json"
OUT_DIR = SCRIPT_DIR / "fb_setup_out"
OUT_DIR.mkdir(exist_ok=True)

# Màu / nội dung KHÁC NHAU cho từng acc (index 0..3)
PALETTES = [
    [(220, 60, 60), (60, 120, 220), (40, 160, 90), (180, 80, 200)],
    [(30, 30, 80), (200, 140, 40), (20, 150, 150), (100, 50, 50)],
    [(255, 120, 0), (0, 100, 180), (120, 40, 160), (50, 50, 50)],
    [(0, 128, 96), (180, 30, 90), (70, 90, 200), (140, 140, 40)],
]
CAPTIONS = [
    [
        "Buổi sáng năng lượng ☕ #{tag}",
        "Cuối tuần thư giãn, mọi người thế nào? #{tag}",
        "Chia sẻ một chút cảm xúc hôm nay 🌿 #{tag}",
    ],
    [
        "New day, new vibe ✨ #{tag}",
        "Just living life one post at a time #{tag}",
        "Grateful for small things today 🙏 #{tag}",
    ],
    [
        "Hôm nay trời đẹp quá 🌤️ #{tag}",
        "Coffee first, then world ☕ #{tag}",
        "Keep going, keep growing 💪 #{tag}",
    ],
    [
        "Simple moments matter 📷 #{tag}",
        "Weekend mood loading... #{tag}",
        "Stay positive, stay kind 🌸 #{tag}",
    ],
]

def log(m):
    print(m, flush=True)

def make_unique_image(path: Path, color, label: str, seed: str):
    """Ảnh unique theo seed (uid + label)."""
    random.seed(seed)
    w, h = 720, 720
    img = Image.new("RGB", (w, h), color)
    d = ImageDraw.Draw(img)
    # random shapes
    for _ in range(12):
        x1, y1 = random.randint(0, w), random.randint(0, h)
        x2, y2 = x1 + random.randint(40, 200), y1 + random.randint(40, 200)
        c = tuple(max(0, min(255, ch + random.randint(-40, 40))) for ch in color)
        d.ellipse([x1, y1, x2, y2], fill=c)
    d.rectangle([20, 20, w - 20, h - 20], outline=(255, 255, 255), width=12)
    d.text((60, h // 2 - 10), label[:28], fill=(255, 255, 255))
    img.save(path, "JPEG", quality=92)
    return path

def set_avatar(token: str, img_path: Path) -> Dict[str, Any]:
    with open(img_path, "rb") as f:
        r = requests.post(
            "https://graph.facebook.com/v18.0/me/picture",
            data={"access_token": token},
            files={"source": f},
            timeout=60,
        )
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:200]}
    return {"status": r.status_code, "body": body}

def create_text_post(token: str, message: str) -> Dict[str, Any]:
    r = requests.post(
        "https://graph.facebook.com/v18.0/me/feed",
        data={"message": message, "access_token": token},
        timeout=30,
    )
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text[:200]}
    return {"status": r.status_code, "body": body}

def try_cover_via_cookie(cookie: str, img_path: Path) -> Dict[str, Any]:
    """Cover user cá nhân Graph API thường không mở — thử upload photo published=false rồi thôi."""
    return {"status": 0, "body": {"note": "Cover cá nhân cần thao tác tay / cookie upload phức tạp"}}

def keepalive_cookie(cookie: str) -> Dict[str, Any]:
    """Làm mới activity + fb_dtsg để cookie sống lâu hơn (không phải vĩnh viễn)."""
    try:
        fb = FacebookAPI(cookie)
        info = fb.info()
        # visit home
        requests.get("https://www.facebook.com/", headers=fb.headers, timeout=15)
        requests.get(f"https://www.facebook.com/{fb.actor_id}", headers=fb.headers, timeout=15)
        return {"ok": bool(info.get("id") or info.get("name")), "info": info,
                "fb_dtsg": bool(fb.fb_dtsg)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:80]}

def setup_one(acc: dict, index: int) -> dict:
    uid = acc["uid"]
    token = acc.get("token") or ""
    cookie = acc.get("cookie") or ""
    result = {"uid": uid, "avatar": None, "posts": [], "keepalive": None, "errors": []}

    if not token:
        result["errors"].append("missing_token")
        return result

    tag = uid[-4:]
    colors = PALETTES[index % len(PALETTES)]
    caps = CAPTIONS[index % len(CAPTIONS)]

    # 1) Avatar unique
    av_path = OUT_DIR / f"avatar_{uid}.jpg"
    make_unique_image(av_path, colors[0], f"AV {uid[-6:]}", seed=f"av-{uid}")
    log(f"[{uid}] set avatar...")
    av = set_avatar(token, av_path)
    result["avatar"] = av
    log(f"[{uid}] avatar → {av['status']} {str(av['body'])[:100]}")
    time.sleep(2)

    # 2) 3 text posts unique
    for i in range(3):
        msg = caps[i].format(tag=f"u{tag}p{i+1}")
        # thêm timestamp unique
        msg = f"{msg}\n({uid[-6:]}-{int(time.time())}-{i+1})"
        log(f"[{uid}] post {i+1}/3: {msg[:50]}...")
        pr = create_text_post(token, msg)
        result["posts"].append({"msg": msg, **pr})
        log(f"[{uid}] post {i+1} → {pr['status']} {str(pr['body'])[:100]}")
        time.sleep(3 + random.random() * 2)

    # 3) keepalive cookie
    if cookie:
        log(f"[{uid}] keepalive cookie...")
        result["keepalive"] = keepalive_cookie(cookie)
        log(f"[{uid}] keepalive → {result['keepalive']}")

    return result

def main():
    accs = json.loads(ACC_FILE.read_text(encoding="utf-8"))
    log(f"Setup {len(accs)} FB accounts\n")
    all_results = []
    for i, acc in enumerate(accs):
        log(f"======== ACC {i+1}/{len(accs)} {acc['uid']} ========")
        try:
            r = setup_one(acc, i)
        except Exception as e:
            r = {"uid": acc["uid"], "errors": [str(e)]}
            log(f"ERR {e}")
        all_results.append(r)
        time.sleep(4)

    out = OUT_DIR / "setup_result.json"
    out.write_text(json.dumps(all_results, ensure_ascii=False, indent=2))
    log(f"\n=== SUMMARY ===")
    for r in all_results:
        posts_ok = sum(1 for p in r.get("posts") or [] if p.get("status") == 200 and "id" in str(p.get("body")))
        av_ok = (r.get("avatar") or {}).get("status") == 200
        log(f"  {r['uid']}: avatar={'OK' if av_ok else 'FAIL'} posts={posts_ok}/3 keepalive={(r.get('keepalive') or {}).get('ok')}")
    log(f"Saved {out}")
    log("\nLưu ý cover ảnh bìa: Graph API user thường không set được — làm tay trên FB nếu TTC bắt buộc.")
    log("Cookie không thể sống vĩnh viễn: chạy keepalive định kỳ (mỗi vài giờ).")

if __name__ == "__main__":
    main()
