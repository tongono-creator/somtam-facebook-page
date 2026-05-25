import os
import re
import random
import time
import requests
import tempfile
from google import genai
from google.genai import types

# ── Config ───────────────────────────────────────────────────────────
PAGE_ID           = "554501167740603"
PAGE_ACCESS_TOKEN = os.environ["SOMTAM_PAGE_ACCESS_TOKEN"]
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY", "")

client       = genai.Client(api_key=GEMINI_API_KEY)
TEXT_MODELS  = ["gemini-2.5-flash", "gemini-3.5-flash"]
ACCENT_COLOR = (255, 107, 53)  # ส้ม #FF6B35

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SomtamBot/1.0; +github)"}

# ── Pexels Search Queries ────────────────────────────────────────────
THAI_FOOD_QUERIES = [
    "thai food",
    "thai food",
    "thai food",
    "thai street food",
    "thai street food",
    "som tam papaya salad",
    "pad thai noodles",
    "tom yum soup",
    "thai spicy food",
    "thai curry",
    "mango sticky rice",
    "thai fried rice",
]

IMAGE_EXTS   = (".jpg", ".jpeg", ".png", ".gif", ".webp")
# content types = reaction ของฝรั่งที่กินอาหารไทย/เผ็ด
CONTENT_TYPES = ["ช็อกเผ็ด", "ติดใจ", "งงแต่กิน", "ไม่คาดหวัง", "กลับมาอีก"]


# ── Pexels ───────────────────────────────────────────────────────────
def get_pexels_food_image():
    if not PEXELS_API_KEY:
        print("PEXELS_API_KEY not set")
        return None

    query = random.choice(THAI_FOOD_QUERIES)
    page  = random.randint(1, 15)
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 20, "page": page},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            print(f"[Pexels] no results for '{query}' page {page}")
            return None
        photo   = random.choice(photos)
        img_url = photo["src"].get("large2x") or photo["src"]["large"]
        alt     = photo.get("alt", query)
        print(f"[Pexels] query='{query}' | alt='{alt[:60]}'")
        return {"url": img_url, "title": alt, "subreddit": query}
    except Exception as e:
        print(f"Pexels error: {e}")
        return None


# ── Download ──────────────────────────────────────────────────────────
def download_image(url):
    MAX_BYTES = 4 * 1024 * 1024
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, stream=True)
        resp.raise_for_status()
        data = b""
        for chunk in resp.iter_content(chunk_size=65536):
            data += chunk
            if len(data) > MAX_BYTES:
                print("Image too large, skipping")
                return None
        suffix = ".jpg"
        for ext in IMAGE_EXTS:
            if url.lower().split("?")[0].endswith(ext):
                suffix = ext
                break
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"Download failed: {e}")
        return None


# ── Gemini Vision ─────────────────────────────────────────────────────
def analyze_image(img_path, reddit_title=""):
    """ดูรูปแล้วบอก food_name | foreigner_reaction | challenge_level"""
    with open(img_path, "rb") as f:
        img_data = f.read()
    title_ctx = f'ชื่อโพสต์ต้นฉบับ: "{reddit_title}"\n' if reddit_title else ""
    prompt = (
        f"{title_ctx}"
        "ดูรูปนี้แล้วตอบ 3 อย่าง แยกด้วย | :\n"
        "1. ชื่ออาหาร ภาษาไทย 1-4 คำ\n"
        "   ถ้าเป็นอาหารตะวันตกล้วน (pizza, burger, pasta, steak ฯลฯ) ที่คนไทยไม่ตื่นเต้น\n"
        "   ตอบว่า: ไม่ตรงคอนเทน|ไม่เกี่ยว|ไม่เกี่ยว\n"
        "2. ถ้าฝรั่งกินครั้งแรก น่าจะ react ยังไง 5-8 คำ เช่น "
        "หน้าแดงน้ำตาไหลแต่ตักต่อ, ตาโตแล้วถ่ายรูปก่อนกิน, "
        "ส่ายหัวแต่ยังกัดต่อ, บอกว่าโอเคแต่เหงื่อแตก\n"
        "3. challenge level สำหรับฝรั่ง เลือก 1 จาก: "
        "เผ็ดช็อก, กลิ่นแรง, หน้าตาแปลกตา, น่ากินเลย, เผ็ดพอดี\n"
        "ตัวอย่าง: ส้มตำ|หน้าแดงน้ำตาไหลแต่ตักต่อ|เผ็ดช็อก\n"
        "ตัวอย่าง: ทุเรียน|ดมแล้วหยุด กัดแล้วไม่หยุด|กลิ่นแรง\n"
        "ถ้าไม่ใช่อาหาร ตอบว่า: ไม่ใช่อาหาร|ไม่เกี่ยว|ไม่เกี่ยว"
    )
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=img_data, mime_type="image/jpeg"),
                    types.Part.from_text(text=prompt),
                ],
            )
            result = resp.text.strip()
            print(f"Vision: {result}")
            parts = result.split("|")
            food_name = parts[0].strip()
            vibe      = parts[1].strip() if len(parts) > 1 else "ถ่ายรูปก่อนกิน"
            genre     = parts[2].strip() if len(parts) > 2 else "น่ากินเลย"
            return food_name, vibe, genre
        except Exception as e:
            print(f"[{model}] vision failed: {e}")
    return None, None, None


# ── Gemini Caption ────────────────────────────────────────────────────
# foreigner reactions ตาม challenge level — ฝรั่งมักจะ react ยังไงกับอาหารแต่ละแบบ
FOREIGNER_REACTIONS = {
    "เผ็ดช็อก":     "หน้าแดง น้ำตาไหล แต่ยังตักต่อ, 'it's fine' แต่เหงื่อแตกทั่วตัว, สั่งน้ำ 3 แก้วแต่ไม่ยอมหยุดกิน, กูเกิลว่า 'ส้มตำ addictive' ตอนกลางคืน",
    "กลิ่นแรง":     "หยุดก่อนแล้วดมอีกครั้ง, หน้าเบ้แต่กัดต่อ, ถ่ายรูปส่งเพื่อน 'กินอะไรก็ไม่รู้', แปลกใจมากที่ตัวเองชอบ",
    "หน้าตาแปลกตา": "ถ่ายรูปก่อนกินเสมอ, เปิด Google Translate ส่องเมนู, 'ไม่รู้ว่าคืออะไร แต่อร่อยมาก', TikTok reaction ทันที",
    "น่ากินเลย":    "สั่งซ้ำรอบสอง, ถ่ายรูป post IG ก่อนกิน, เดินกลับหาร้านเดิมวันถัดไป, 'Thai food is the best cuisine I've ever had'",
    "เผ็ดพอดี":     "'Perfect spice level', แนะนำเพื่อน, 'Now I understand why Thai people eat this every day', ยิ้มหลังกิน",
}

REALISM_FILTER = (
    "เขียนเหมือนคนไทยพิมพ์เองใน Facebook ขณะดูฝรั่งกินอาหาร ไม่ใช่นักการตลาด\n"
    "ภาษาพูดธรรมดา ความคิดแรกในหัวคนไทย ง่ายๆ ตรงๆ มีความ 'เราดูอยู่นะ'\n"
    "avoid: คำคม, punchline ประดิษฐ์, ภาษาสวย, อวยฝรั่งหรืออวยอาหาร\n"
    "prioritize: ความตลกของ reaction, ความภูมิใจในอาหารไทย, ความ 'ฝรั่งยังสู้ไม่ได้'\n"
    "ตัวอย่างโทนที่ถูก: 'บอกว่าไม่เผ็ด 555', 'ยังไหวไหมนะ', 'ติดใจแล้วสินะ', 'เขาไม่รู้หรอกว่านี่แค่เบาๆ'\n"
    "ตัวอย่างโทนที่ผิด: 'รสชาติที่ไม่มีที่สิ้นสุด', 'ประสบการณ์ใหม่', ประโยคประดิษฐ์ใดๆ\n"
)


def clean_hook_lines(raw_text):
    text = clean_text(raw_text)
    
    # Check if we should split by pipe or newline
    if "|" in text:
        parts = text.split("|")
    else:
        parts = text.split("\n")
        
    # Pattern to strip prefixes like "บรรทัด 1: ", "ข้อความในโพสต์ Facebook: ", "1. ", etc.
    label_pattern = r'^(ข้อความในโพสต์\s*Facebook|ข้อความบนรูป|ข้อความในรูป|ข้อความ|คำบรรยาย|คำอธิบาย|บรรทัดที่\s*\d+|บรรทัด\s*\d+|ประโยคที่\s*\d+|ประโยค\s*\d+|Hook\s*text|Hook|Line\s*\d+|[L|l]ine\s*\d+|\d+)\s*[:\-\.\s]\s*'
    
    cleaned_lines = []
    for part in parts:
        cleaned = re.sub(label_pattern, '', part, flags=re.IGNORECASE).strip()
        cleaned = cleaned.strip('"\'“”‘’')
        if cleaned:
            cleaned_lines.append(cleaned)
            
    return cleaned_lines


def generate_hook(food_name, vibe, genre, content_type, reddit_title=""):
    # vibe = reaction ฝรั่ง, genre = challenge level
    reactions = FOREIGNER_REACTIONS.get(genre, FOREIGNER_REACTIONS["น่ากินเลย"])
    is_shock = content_type in ("ช็อกเผ็ด", "งงแต่กิน") or any(
        w in vibe for w in ["แดง", "น้ำตา", "เหงื่อ", "ส่ายหัว", "งง", "เบ้"]
    )
    title_ctx = f'ชื่อโพสต์เจ้าของรูป: "{reddit_title}"\n' if reddit_title else ""
    if is_shock:
        style = (
            f"{title_ctx}"
            f"อาหาร: {food_name} | ฝรั่ง react: {vibe} | challenge: {genre}\n"
            f"reaction context: {reactions}\n"
            "เขียน hook text บนรูปอาหาร — มุมคนไทยดูฝรั่งกินแล้วช็อก\n"
            "บรรทัด 1: ต้องมีคำว่า 'ฝรั่ง' หรือ 'เขา' ชัดเจน 3-6 คำ\n"
            "  เช่น 'ฝรั่งเจอส้มตำ..', 'เขาบอกว่าโอเค..', 'ฝรั่งกิน[food_name]ครั้งแรก..'\n"
            "บรรทัด 2: ต่อแบบเห็นใจ/แซว 3-5 คำ ลงท้ายให้คนอยากคอมเม้น\n"
        )
    else:
        style = (
            f"{title_ctx}"
            f"อาหาร: {food_name} | ฝรั่ง react: {vibe} | challenge: {genre}\n"
            f"reaction context: {reactions}\n"
            "เขียน hook text บนรูปอาหาร — มุมคนไทยดูฝรั่งติดใจ\n"
            "บรรทัด 1: ต้องมีคำว่า 'ฝรั่ง' หรือ 'เขา' ชัดเจน 3-6 คำ\n"
            "  เช่น 'ฝรั่งติดใจ[food_name]แล้ว', 'เขากลับมาอีกแล้ว', 'ฝรั่งเข้าใจแล้วสิ'\n"
            "บรรทัด 2: คำถาม/ประโยคสั้น 3-5 คำ ชวนแชร์ประสบการณ์\n"
        )
    prompt = f"{style}{REALISM_FILTER}ตอบแค่ 2 บรรทัด ไม่มี hashtag ไม่มี **\n" \
             f"ห้ามเขียนคำนำ ห้ามเขียนสรุป ห้ามใส่ป้ายกำกับใดๆ เช่น 'บรรทัด 1:' หรือ 'Hook:' เด็ดขาด"
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            lines = clean_hook_lines(resp.text)
            return lines[0] if lines else food_name[:20], lines[1] if len(lines) > 1 else ""
        except Exception as e:
            print(f"[{model}] hook failed: {e}")
    return food_name[:20], ""


def generate_caption(food_name, vibe, genre, content_type, subreddit, reddit_title=""):
    # vibe = reaction ฝรั่ง, genre = challenge level
    reactions = FOREIGNER_REACTIONS.get(genre, FOREIGNER_REACTIONS["น่ากินเลย"])
    title_ctx = f'ชื่อโพสต์เจ้าของรูป: "{reddit_title}"\n' if reddit_title else ""
    # base context — มุมมองคนไทยดูฝรั่งกินอาหารไทย/เผ็ด
    human_base = (
        f"{title_ctx}"
        f"อาหาร: {food_name} | challenge level: {genre}\n"
        f"ฝรั่ง react ยังไง: {vibe}\n"
        f"pattern reaction ที่คนไทยคุ้นเคย: {reactions}\n\n"
        + REALISM_FILTER +
        "มุมมองหลัก: คนไทยดูฝรั่งกิน ตลก/ภูมิใจ/เห็นใจ\n"
        "ห้ามอวยฝรั่งหรืออวยอาหารแบบ generic — เล่าเรื่องให้มีชีวิต\n\n"
    )
    prompts = {
        "ช็อกเผ็ด": (
            human_base +
            "เขียน Facebook caption แบบ ▪️ bullet narrative — ฝรั่งกินแล้วโดนเผ็ดช็อก\n"
            "ใช้ ▪️ นำหน้าทุก bullet — 6-8 จุด เล่าเรื่องมีความต่อเนื่อง\n"
            "▪️ 1-2: Setup — เหตุการณ์ก่อนกิน ฝรั่งบอกยังไง\n"
            "▪️ 3-4: Moment — ตอนกิน reaction ตลกๆ ที่เห็น\n"
            "▪️ 5-6: Twist — แม้จะโดนเผ็ดแต่ยังตักต่อ ทำไม\n"
            "▪️ 7-8: Engage — เคยเจอฝรั่งกินอาหารไทยแล้ว react แบบนี้ไหม\n"
            "แต่ละ bullet: 1-2 ประโยค ภาษาพูดไม่ประดิษฐ์\n"
            "จบด้วย hashtag 3 อัน ห้ามใช้ ** ตอบแค่ caption"
        ),
        "ติดใจ": (
            human_base +
            "เขียน Facebook caption แบบ ▪️ bullet narrative — ฝรั่งกินแล้วติดใจ อยากกลับมาอีก\n"
            "ใช้ ▪️ นำหน้าทุก bullet — 6-8 จุด เล่าเรื่องมีความต่อเนื่อง\n"
            "▪️ 1-2: Setup — ฝรั่งกินครั้งแรกท่าทางยังไง\n"
            "▪️ 3-4: Hook — reaction ที่บอกว่าติดใจแน่ๆ\n"
            "▪️ 5-6: Insight — ทำไมอาหารนี้ถึงทำให้ฝรั่งติด\n"
            "▪️ 7-8: Engage — ควรแนะนำให้กินเมนูไหนต่อ\n"
            "แต่ละ bullet: 1-2 ประโยค ภาษาพูดธรรมดา ความภูมิใจในอาหารไทย\n"
            "จบด้วย hashtag 3 อัน ห้ามใช้ ** ตอบแค่ caption"
        ),
        "งงแต่กิน": (
            human_base +
            "เขียน Facebook caption แบบ ▪️ bullet narrative — ฝรั่งงงกับอาหารแต่กินจนหมด\n"
            "ใช้ ▪️ นำหน้าทุก bullet — 6-8 จุด โทน: ตลก เห็นใจ 'เขาไม่รู้ว่าเจออะไรอยู่'\n"
            "▪️ 1-2: Setup — หน้าตาอาหาร/กลิ่น ทำให้ฝรั่งงงยังไง\n"
            "▪️ 3-4: Moment — ตอนกินครั้งแรก หน้าตาเป็นยังไง\n"
            "▪️ 5-6: Twist — สุดท้ายกินจนหมด เพราะอะไร\n"
            "▪️ 7-8: Engage — คนไทยดูแล้วรู้สึกยังไง\n"
            "แต่ละ bullet: 1-2 ประโยค ภาษาพูดธรรมดา\n"
            "จบด้วย hashtag 3 อัน ห้ามใช้ ** ตอบแค่ caption"
        ),
        "ไม่คาดหวัง": (
            human_base +
            "เขียน Facebook caption แบบ ▪️ bullet narrative — ฝรั่งไม่คิดว่าจะอร่อย สุดท้ายชอบมาก\n"
            "ใช้ ▪️ นำหน้าทุก bullet — 6-8 จุด เล่าเรื่องมีความต่อเนื่อง\n"
            "▪️ 1-2: Setup — ฝรั่งเห็นอาหารครั้งแรก มีหน้าตา/กลิ่นยังไง\n"
            "▪️ 3-4: Moment — ลองกัด reaction ทันทีเป็นยังไง\n"
            "▪️ 5-6: Surprise — สิ่งที่ทำให้เขา 'โอ้โห ไม่คาดคิด'\n"
            "▪️ 7-8: Engage — อาหารไทยอะไรที่คุณคิดว่าฝรั่งจะงงแต่ชอบ\n"
            "แต่ละ bullet: 1-2 ประโยค ภาษาพูดธรรมดา\n"
            "จบด้วย hashtag 3 อัน ห้ามใช้ ** ตอบแค่ caption"
        ),
        "กลับมาอีก": (
            human_base +
            "เขียน Facebook caption แบบ ▪️ bullet narrative — ฝรั่งกินแล้วกลับมาหาซ้ำ กลายเป็น regular\n"
            "ใช้ ▪️ นำหน้าทุก bullet — 6-8 จุด เล่าเรื่องมีความต่อเนื่อง\n"
            "▪️ 1-2: Setup — ครั้งแรกที่กิน เขา react ยังไง\n"
            "▪️ 3-4: Pattern — พฤติกรรมที่บอกว่าติดแล้ว กลับมากี่ครั้ง\n"
            "▪️ 5-6: Why — อาหารนี้มีอะไรที่ทำให้ฝรั่งต้องกลับมา\n"
            "▪️ 7-8: Engage — อาหารไทยเมนูไหนที่คิดว่าฝรั่งต้องติดใจ\n"
            "แต่ละ bullet: 1-2 ประโยค ภาษาพูดธรรมดา\n"
            "จบด้วย hashtag 3 อัน ห้ามใช้ ** ตอบแค่ caption"
        ),
    }
    prompt = prompts.get(content_type, prompts["ติดใจ"])
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            return clean_text(resp.text.strip())
        except Exception as e:
            print(f"[{model}] caption failed: {e}")
    return f"{food_name} อร่อยมาก!\n#อาหาร #foodporn #อร่อย"


def clean_text(text):
    text = text.replace("\\n", "\n")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*",     r"\1", text)
    text = re.sub(r"__(.+?)__",     r"\1", text)
    text = re.sub(r"_(.+?)_",       r"\1", text)
    text = re.sub(r"^#+\s*",        "",    text, flags=re.MULTILINE)
    return text.strip()


# ── Facebook ──────────────────────────────────────────────────────────
def post_photo(caption, img_path):
    try:
        api_url = f"https://graph.facebook.com/v21.0/{PAGE_ID}/photos"
        with open(img_path, "rb") as f:
            resp = requests.post(
                api_url,
                data={"message": caption, "access_token": PAGE_ACCESS_TOKEN},
                files={"source": ("food.jpg", f, "image/jpeg")},
                timeout=60,
            )
        result = resp.json()
        if "id" in result:
            post_id = result.get("post_id") or result["id"]
            print(f"Posted: {post_id}")
            add_comment(post_id)
            return True
        else:
            print(f"Post failed: {result}")
            return False
    except Exception as e:
        print(f"Facebook error: {e}")
        return False
    finally:
        if img_path and os.path.exists(img_path):
            os.unlink(img_path)


# ── Comment ───────────────────────────────────────────────────────────
def add_comment(post_id):
    from affiliate_utils import get_all_comments
    comments = get_all_comments()
    delay0   = random.uniform(60, 180)
    print(f"Waiting {delay0:.0f}s before first comment...")
    time.sleep(delay0)
    for i, msg in enumerate(comments, 1):
        if isinstance(msg, dict):
            data = {"access_token": PAGE_ACCESS_TOKEN, "message": msg["message"]}
            if msg.get("picture_url"):
                data["attachment_url"] = msg["picture_url"]
        else:
            data = {"access_token": PAGE_ACCESS_TOKEN, "message": msg}
        resp = requests.post(
            f"https://graph.facebook.com/v21.0/{post_id}/comments",
            data=data,
        )
        result = resp.json()
        if "id" in result:
            print(f"Comment {i} added: {result['id']}")
        else:
            print(f"Comment {i} error: {result}")
        if i < len(comments):
            time.sleep(random.uniform(30, 90))


# ── Main ──────────────────────────────────────────────────────────────
def main():
    print("=== ส้มตำคุณอร Bot ===")

    post = None
    for attempt in range(5):
        post = get_pexels_food_image()
        if post:
            break
        print(f"Retry {attempt + 1}/5...")

    if not post:
        print("No suitable post found after 5 attempts")
        return

    img_path = download_image(post["url"])
    if not img_path:
        print("Image download failed")
        return

    reddit_title = post["title"]

    # Vision วิเคราะห์รูป → food_name + foreigner reaction vibe + challenge level
    food_name, vibe, genre = analyze_image(img_path, reddit_title=reddit_title)
    if not food_name or "ไม่ใช่อาหาร" in food_name or "ไม่ตรงคอนเทน" in food_name:
        print("Not a food image, using Reddit title as fallback")
        food_name = reddit_title
        vibe      = "ถ่ายรูปก่อนกิน"
        genre     = "น่ากินเลย"

    print(f"Food: {food_name} | Challenge: {genre} | Reaction: {vibe}")
    content_type = random.choice(CONTENT_TYPES)
    line1, line2 = generate_hook(food_name, vibe, genre, content_type, reddit_title=reddit_title)
    print(f"Hook: {line1} | {line2}")

    # PIL overlay
    try:
        from overlay_utils import add_overlay
        overlaid = add_overlay(img_path, line1, line2, ACCENT_COLOR)
        os.unlink(img_path)
        img_path = overlaid
    except Exception as e:
        print(f"Overlay failed (using original): {e}")

    caption = generate_caption(food_name, vibe, genre, content_type, post["subreddit"], reddit_title=reddit_title)
    caption += f"\n📷 via Pexels"
    print(f"Caption:\n{caption}\n")

    success = post_photo(caption, img_path)
    if not success:
        print("FAILED")


if __name__ == "__main__":
    main()
