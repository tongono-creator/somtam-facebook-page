# -*- coding: utf-8 -*-
"""dilemma.py — โพสต์การ์ดคำถามดราม่าอาหารและข้อพิพาทร้านค้าสไตล์ Threads เพจพริก 10 เม็ด"""

import os
import sys
import io
import re
import json
import time
import random
import requests
import hashlib
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from google import genai
from google.genai import types
from google.genai.types import HttpOptions

# ── Config ───────────────────────────────────────────────────────────────────
PAGE_ID           = "554501167740603"
PAGE_ACCESS_TOKEN = os.environ.get("SOMTAM_PAGE_ACCESS_TOKEN", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")

if not PAGE_ACCESS_TOKEN or not GEMINI_API_KEY:
    try:
        from config import PAGE_ACCESS_TOKEN as _tok, GOOGLE_API_KEY as _key
        if not PAGE_ACCESS_TOKEN:
            PAGE_ACCESS_TOKEN = _tok
        if not GEMINI_API_KEY:
            GEMINI_API_KEY = _key
    except ImportError:
        pass

if not GEMINI_API_KEY:
    GEMINI_API_KEY = "DUMMY_KEY"

client       = genai.Client(api_key=GEMINI_API_KEY, http_options=HttpOptions(timeout=300000))
TEXT_MODELS  = ["gemini-flash-latest", "gemini-flash-latest"]
OUTPUT_DIR   = "output"
FONT_PATH    = os.path.join(os.path.dirname(__file__), "fonts", "Sarabun-ExtraBold.ttf")
HISTORY_FILE = "dilemma_history.txt"
HEADERS      = {"User-Agent": "Mozilla/5.0 (compatible; SomtamBot/1.0; +github)"}

ACCENT_COLOR = (255, 107, 53)   # ส้มจัดจ้าน #FF6B35
WHITE_COLOR  = (255, 255, 255)

os.makedirs(OUTPUT_DIR, exist_ok=True)

FOOD_SUBREDDITS = [
    "TalesFromYourServer",
    "KitchenConfidential",
    "mildlyinfuriating",
    "Chefit",
    "AITA",
    "FoodPorn",
    "food",
]

FIRST_PERSON_TERMS = ("ผม", "ฉัน", "ดิฉัน", "หนู", "เรา", "พวกเรา", "ตัวเรา", "ของเรา")

def contains_first_person(text):
    clean = (text or "").replace("\u200b", "")
    return any(term in clean for term in FIRST_PERSON_TERMS)

def apply_slang_rules(text):
    if not text:
        return text
    # Rule: แทนคำว่า ให้ไปตาย / ประหารชีวิต / ฆ่า ในบริบทเล่าเรื่องด้วย ไปคุยกับรากมะม่วง
    text = re.sub(r'ให้(?:ไป)?ตาย|ให้ประหารชีวิต|ส่งไปตาย|เอาไปฆ่า', 'ไปคุยกับรากมะม่วง', text)
    return text

def contains_thai(text):
    if not text:
        return False
    return any('\u0e00' <= char <= '\u0e7f' for char in text)

# ── History ──────────────────────────────────────────────────────────────────
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return [l.strip() for l in f if l.strip()]
        except Exception:
            return []
    return []

def save_to_history(url_or_key):
    items = load_history()
    items.append(url_or_key)
    items = items[-300:]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for it in items:
                f.write(it + "\n")
    except Exception as e:
        print(f"History save error: {e}")

def reddit_title_key(title):
    norm = re.sub(r"[^\w฀-๿]+", "", (title or "").strip().lower())
    if not norm:
        return ""
    return "title:" + hashlib.md5(norm.encode("utf-8")).hexdigest()[:16]

# ── Reddit fetch ─────────────────────────────────────────────────────────────
def get_reddit_food_story(history_set):
    NS = {"atom": "http://www.w3.org/2005/Atom"}
    subs = random.sample(FOOD_SUBREDDITS, len(FOOD_SUBREDDITS))
    for sub in subs:
        rss_url = f"https://www.reddit.com/r/{sub}/hot.rss?limit=30"
        try:
            resp = requests.get(rss_url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
            root    = ET.fromstring(resp.content)
            entries = root.findall("atom:entry", NS)
            candidates = []
            for entry in entries:
                title   = entry.findtext("atom:title", "", NS).strip()
                content = entry.findtext("atom:content", "", NS)
                link_el = entry.find("atom:link", NS)
                permalink = link_el.get("href", "") if link_el is not None else ""

                body = re.sub(r"<[^>]+>", " ", content or "").strip()
                body = re.sub(r"\s{2,}", " ", body)

                if (len(body) >= 150
                        and permalink not in history_set
                        and reddit_title_key(title) not in history_set
                        and "reddit.com/r/" in permalink):
                    candidates.append({
                        "subreddit": sub,
                        "title":     title,
                        "body":      body[:1200],
                        "permalink": permalink,
                    })
            if candidates:
                chosen = random.choice(candidates[:15])
                print(f"Food Story: r/{sub} | {chosen['title'][:70]}")
                return chosen
        except Exception as e:
            print(f"Reddit error ({sub}): {e}")
    return None

# ── Gemini text helper ───────────────────────────────────────────────────────
def gemini_text(prompt):
    for model in TEXT_MODELS:
        for attempt in range(2):
            try:
                resp = client.models.generate_content(model=model, contents=prompt)
                return resp.text.strip()
            except Exception as e:
                print(f"[{model}] attempt {attempt+1} failed: {e}")
                time.sleep(2)
    return ""

# ── Translation & Copywriting ────────────────────────────────────────────────
def generate_food_dilemma(title="", body="", subreddit="food"):
    prompt = (
        f"คุณคือแอดมินเพจ 'พริก 10 เม็ด' เพจอาหารและรีวิวของกินสุดแซ่บ คาแรคเตอร์สาวสายกิน ตัวมัมของวงการอาหาร ชวนเม้าท์ ชวนถก ลีลาจัดจ้าน เป็นกันเอง (ลงท้าย 'ค่ะ/นะคะ', แทนตัวเองด้วยชื่อเพจหรือแอดมิน)\n"
        f"จงนำเรื่องราวต่อไปนี้มาสร้างเป็น 'ดราม่าอาหารและข้อพิพาทชวนถก' สไตล์ Threads:\n\n"
        f"Title: {title}\n"
        f"Body: {body}\n\n"
        "กฎเหล็กสำคัญที่สุด:\n"
        "1. วางตัวเป็นบุคคลที่สาม (3rd-party observer) ที่ไปเจอเรื่องนี้มาเล่าต่อ เช่น 'ลูกค้าคนหนึ่ง...', 'ร้านอาหารแห่งหนึ่ง...', 'ไรเดอร์คนหนึ่ง...'\n"
        "   - ห้ามแต่งว่าเป็นประสบการณ์ส่วนตัวของแอดมินเด็ดขาด\n"
        "   - ห้ามมีสรรพนามบุคคลที่หนึ่ง (ผม, เรา, ฉัน, หนู) ในเหตุการณ์\n"
        "2. คำศัพท์พิเศษ: หากในเรื่องมีบริบทให้ไปตาย หรือลงโทษสูงสุด ให้ใช้คำสแลงว่า 'ไปคุยกับรากมะม่วง'\n"
        "3. สามารถหยอดคำศัพท์วัยรุ่น 2025 อย่างเป็นธรรมชาติ (เช่น ชีเสิร์ฟ, โฮ่งมาก, ตัวมัม, อ่อม, หัวจะปวด, กี่โมง)\n"
        "4. ตอบกลับเป็น JSON เพียวๆ เท่านั้น:\n"
        "{\n"
        '  "image_line1": "พาดหัวสั้นบรรทัด 1 สีส้ม (8-14 ตัวอักษร เช่น \'สั่งกะเพราหมูกรอบ\')",\n'
        '  "image_line2": "พาดหัวสั้นบรรทัด 2 สีขาว (8-14 ตัวอักษร เช่น \'ขอลีนๆ ไร้มัน?\')",\n'
        '  "caption": "เรื่องเล่าบริบทอาหาร/ร้านค้า 1-2 ย่อหน้า ปิดท้ายด้วยคำถามเลือกข้าง 2 ช้อยส์ และลงท้ายด้วย \'1/2\'",\n'
        '  "seed_comment": "ความคิดเห็นของแอดมินสาวตัวมัม (ลงท้ายค่ะ) ที่เลือกข้างชัดเจนข้างใดข้างหนึ่งทันทีแบบไม่มีกั๊กเพื่อจุดชนวนให้คนเถียง และลงท้ายด้วย \'2/2\'"\n'
        "}"
    )
    raw = gemini_text(prompt)
    line1, line2, caption, seed_comment = "", "", "", ""
    if raw:
        clean_raw = raw.strip()
        if clean_raw.startswith("```"):
            clean_raw = re.sub(r"^```(?:json)?\n", "", clean_raw)
            clean_raw = re.sub(r"\n```$", "", clean_raw)
            clean_raw = clean_raw.strip()

        m = re.search(r'\{.*?\}', clean_raw, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
                line1 = data.get("image_line1", "").strip()
                line2 = data.get("image_line2", "").strip()
                caption = data.get("caption", "").strip()
                seed_comment = data.get("seed_comment", "").strip()
            except Exception as e:
                print(f"JSON parse error: {e}")

    line1 = apply_slang_rules(line1)
    line2 = apply_slang_rules(line2)
    caption = apply_slang_rules(caption)
    seed_comment = apply_slang_rules(seed_comment)

    # Fallback to rich presets if failed
    if not line1 or not caption or not seed_comment or not contains_thai(line1) or not contains_thai(caption):
        print("Using local somtam dilemma fallbacks.")
        fallbacks = [
            {
                "line1": "กะเพราหมูกรอบ",
                "line2": "ขอลีนๆ ไร้มัน?",
                "caption": "ไปเจอโพสต์หนึ่งในโซเชียลค่ะ ลูกค้าคนหนึ่งสั่งกะเพราหมูกรอบ แต่กำชับร้านว่า 'ขอแบบไม่เอามันเลย เอาเนื้อล้วนๆ' ทางร้านแจ้งว่าหมูกรอบยังไงก็ต้องมีชั้นมัน ไม่อย่างนั้นจะเหนียวแห้ง ลูกค้าเลยโวยวายว่าร้านไม่ใส่ใจ ถ้าเป็นลูกเพจคิดว่าคำขอนี้สมเหตุสมผล หรือสั่งหมูชิ้นไปเลยดีกว่าคะ? 1/2",
                "seed_comment": "สั่งหมูกรอบแต่ไม่เอามัน สั่งหมูชิ้นหรืออกไก่แต่แรกจบเลยค่ะ หมูกรอบไม่ติดมันแล้วมันจะฟินกี่โมง 2/2"
            },
            {
                "line1": "บุฟเฟต์เหลือเยอะ",
                "line2": "แอบห่อกลับบ้าน?",
                "caption": "มีประเด็นในกลุ่มร้านอาหารค่ะ ลูกค้าโต๊ะหนึ่งกินบุฟเฟต์ปิ้งย่างไม่หมด เหลือเนื้อจานใหญ่เลยหยิบกล่องมาแอบตักใส่กระเป๋า พอพนักงานจับได้ก็อ้างว่า 'ก็จ่ายเงินครบหัวแล้ว เสียดายของ' ทางร้านเลยปรับเงินตามกฎ ถ้าเป็นทุกคนคิดว่าเคสนี้ร้านทำถูกแล้ว หรือควรยืดหยุ่นให้คะ? 1/2",
                "seed_comment": "เคสนี้ร้านทำถูกต้อง 100% ค่ะ บุฟเฟต์คือกินไม่อั้นในร้าน ไม่ใช่บุฟเฟต์เทคโฮม ทำแบบนี้ร้านเจ๊งพอดีค่ะ 2/2"
            },
            {
                "line1": "สั่งส้มตำเผ็ดน้อย",
                "line2": "แต่ใส่พริก 5 เม็ด",
                "caption": "ไปอ่านเจอดราม่าสายแซ่บมาค่ะ ลูกค้าสั่งส้มตำระบุชัดเจนว่า 'เผ็ดน้อย' แต่แม่ค้าตำพริกใส่ไป 5 เม็ด พอท้วงแม่ค้าบอกว่า 'ปกติร้านนี้ใส่ 15 เม็ด 5 เม็ดนี่คือเด็กกินแล้วนะ' สรุปเผ็ดน้อยของแต่ละคนไม่เท่ากัน เคสนี้คิดว่าแม่ค้าต้องปรับ หรือลูกค้าต้องระบุเป็นจำนวนเม็ดคะ? 1/2",
                "seed_comment": "เพื่อความปลอดภัยของกระเพาะอาหาร คราวหลังระบุไปเลยค่ะว่าพริกกี่เม็ด เพราะเผ็ดน้อยของแม่ค้าอีสานแท้คือระดับไฟลุกค่ะ 2/2"
            }
        ]
        chosen = random.choice(fallbacks)
        line1 = chosen["line1"]
        line2 = chosen["line2"]
        caption = chosen["caption"]
        seed_comment = chosen["seed_comment"]

    if "1/2" not in caption:
        caption = caption.rstrip() + " 1/2"
    if "2/2" not in seed_comment:
        seed_comment = seed_comment.rstrip() + " 2/2"

    return line1, line2, caption, seed_comment

# ── Text wrap helper ─────────────────────────────────────────────────────────
_LEADING_VOWELS  = set("เแโใไ")
_COMBINING_CHARS = set("่้๊๋์ิีึืุูัํ็")

def wrap_text(draw, text, font, max_width):
    words = [w for w in text.split(" ") if w]
    if not words:
        words = list(text)
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip() if cur else w
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [text]

# ── Generate image ───────────────────────────────────────────────────────────
def generate_image(line1, line2):
    """Dark card 1080x1080 — line 1 ส้ม (#FF6B35), line 2 ขาว (#FFFFFF) auto-fit กึ่งกลาง"""
    bkk  = timezone(timedelta(hours=7))
    ts   = datetime.now(bkk).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(OUTPUT_DIR, f"somtam_dilemma_{ts}.jpg")

    W = H = 1080
    img  = Image.new("RGB", (W, H), (0, 0, 0))   # pure black
    draw = ImageDraw.Draw(img)

    PAD      = 80
    max_w    = W - PAD * 2   # 920px
    LINE_GAP = 28

    raw_lines = [l.strip() for l in [line1, line2] if l.strip()]

    font_size = 110
    best_font = None
    best_lines = []
    while font_size >= 36:
        font = ImageFont.truetype(FONT_PATH, font_size)
        wrapped = []
        for idx, l in enumerate(raw_lines):
            for w in wrap_text(draw, l, font, max_w):
                wrapped.append((w, idx == 0))

        def lh(text):
            bb = draw.textbbox((0, 0), text, font=font)
            return bb[3] - bb[1]

        total_h  = sum(lh(t) + LINE_GAP for t, _ in wrapped)
        width_ok = all(draw.textbbox((0, 0), t, font=font)[2] <= max_w for t, _ in wrapped)

        if total_h <= H - PAD * 2 and width_ok:
            best_font  = font
            best_lines = wrapped
            break
        font_size -= 4

    if not best_font:
        best_font  = ImageFont.truetype(FONT_PATH, 36)
        best_lines = []
        for idx, l in enumerate(raw_lines):
            for w in wrap_text(draw, l, best_font, max_w):
                best_lines.append((w, idx == 0))

    print(f"Somtam dilemma font size: {font_size} | lines: {len(best_lines)}")

    def lh(text):
        bb = draw.textbbox((0, 0), text, font=best_font)
        return bb[3] - bb[1]
    total_h = sum(lh(t) + LINE_GAP for t, _ in best_lines)

    y = (H - total_h) // 2

    for text, is_first in best_lines:
        bb = draw.textbbox((0, 0), text, font=best_font)
        w  = bb[2] - bb[0]
        x  = (W - w) // 2
        dy = y - bb[1]
        line_color = ACCENT_COLOR if is_first else WHITE_COLOR
        draw.text((x + 3, dy + 3), text, font=best_font, fill=(30, 30, 30))
        draw.text((x, dy), text, font=best_font, fill=line_color)
        y += lh(text) + LINE_GAP

    # watermark
    try:
        wm_font = ImageFont.truetype(FONT_PATH, 26)
        wm_text = "พริก 10 เม็ด"
        bb = draw.textbbox((0, 0), wm_text, font=wm_font)
        draw.text(((W - (bb[2]-bb[0])) // 2, H - 55), wm_text, font=wm_font, fill=(70, 70, 70))
    except Exception:
        pass

    img.save(path, "JPEG", quality=92)
    print(f"Somtam image saved: {path}")
    return path

# ── Facebook Posting ─────────────────────────────────────────────────────────
def post_seed_comment(post_id, seed_comment):
    if not seed_comment:
        return
    try:
        data = {"access_token": PAGE_ACCESS_TOKEN, "message": seed_comment}
        resp = requests.post(f"https://graph.facebook.com/v25.0/{post_id}/comments", data=data, timeout=60)
        res = resp.json()
        print(f"Admin Seed Comment: {'OK id=' + res.get('id', '') if 'id' in res else res}")
    except Exception as e:
        print(f"Error posting admin seed comment: {e}")

def post_facebook(img_path, caption, seed_comment=None):
    print("Posting food dilemma to Facebook...")
    try:
        # Step 1: Upload photo as unpublished
        with open(img_path, "rb") as f:
            resp = requests.post(
                f"https://graph.facebook.com/v25.0/{PAGE_ID}/photos",
                data={"access_token": PAGE_ACCESS_TOKEN, "published": "false"},
                files={"source": ("dilemma.jpg", f, "image/jpeg")},
                timeout=60,
            )
        upload_result = resp.json()
        if "id" not in upload_result:
            print(f"Photo upload failed: {upload_result}")
            return None
        
        photo_id = upload_result["id"]
        print(f"Photo uploaded unpublished! ID: {photo_id}")
        
        # Step 2: Publish to feed
        resp2 = requests.post(
            f"https://graph.facebook.com/v25.0/{PAGE_ID}/feed",
            data={
                "access_token": PAGE_ACCESS_TOKEN,
                "message": caption,
                "attached_media": json.dumps([{"media_fbid": photo_id}])
            },
            timeout=60,
        )
        feed_result = resp2.json()
        if "id" in feed_result:
            post_id = feed_result["id"]
            print(f"Posted to feed! ID: {post_id}")
            # Step 3: Admin seed comment immediately (2/2)
            if seed_comment:
                post_seed_comment(post_id, seed_comment)
            add_affiliate_comments(post_id, caption)
            return post_id
        else:
            print(f"Feed publishing failed: {feed_result}")
            return None
    except Exception as e:
        print(f"Error posting to FB: {e}")
        return None

def add_affiliate_comments(post_id, caption):
    try:
        from affiliate_utils import get_all_comments
        comments = get_all_comments(caption=caption)
    except Exception:
        return
    delay = random.uniform(60, 180)
    print(f"Waiting {delay:.0f}s before first affiliate comment...")
    time.sleep(delay)
    for i, msg in enumerate(comments[:2], 1):
        if isinstance(msg, dict):
            data = {"access_token": PAGE_ACCESS_TOKEN, "message": msg["message"]}
            pic  = msg.get("picture_url", "")
            if pic and pic.startswith("http"):
                data["attachment_url"] = pic
        else:
            data = {"access_token": PAGE_ACCESS_TOKEN, "message": str(msg)}
        if not data.get("message", "").strip():
            continue
        r = requests.post(
            f"https://graph.facebook.com/v25.0/{post_id}/comments",
            data=data, timeout=60,
        )
        res = r.json()
        print(f"Affiliate Comment {i}: {'OK id=' + res['id'] if 'id' in res else res}")
        if i < len(comments):
            time.sleep(random.uniform(30, 90))

# ── Main ─────────────────────────────────────────────────────────────────────
def main(dry_run=False):
    history_set = set(load_history())
    post = get_reddit_food_story(history_set)
    title = post["title"] if post else ""
    body = post["body"] if post else ""
    sub = post["subreddit"] if post else "food"

    line1, line2, caption, seed_comment = generate_food_dilemma(title, body, sub)

    print("\n--- [SOMTAM FOOD DILEMMA] ---")
    print(f"Line 1 (Orange): {line1}")
    print(f"Line 2 (White):  {line2}")
    print(f"Caption (1/2):\n{caption}\n")
    print(f"Seed Comment (2/2):\n{seed_comment}\n")

    img_path = generate_image(line1, line2)

    if dry_run:
        sample_path = os.path.join(OUTPUT_DIR, "somtam_dilemma_sample.jpg")
        import shutil
        shutil.copy(img_path, sample_path)
        print(f"[DRY RUN] Generated sample card saved to: {sample_path}")
        print("[DRY RUN] Posting skipped.")
        return

    full_caption = f"{caption}\n\n#เรื่องกินเรื่องใหญ่ #ดราม่าอาหาร #พริก10เม็ด"
    post_facebook(img_path, full_caption, seed_comment=seed_comment)

    if post:
        save_to_history(post["permalink"])
        save_to_history(reddit_title_key(post["title"]))

    try:
        if os.path.exists(img_path):
            os.unlink(img_path)
    except Exception:
        pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    main(dry_run=args.dry_run)
