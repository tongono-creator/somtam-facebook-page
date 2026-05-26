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
# content types = หมวดหมู่การเล่าเรื่องของสายกิน/สตรีทฟู้ด + ดราม่าและข้อพิพาทอาหารไทย
CONTENT_TYPES = ["สายแซ่บสู้ชีวิต", "วิถีสตรีทฟู้ด", "รีวิวแซ่บจิกกัด", "ความหิวยามดึก", "ข้อพิพาทอาหาร"]


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
    """ดูรูปแล้วบอก image_type | food_name | local_vibe | appeal_level"""
    with open(img_path, "rb") as f:
        img_data = f.read()
    title_ctx = f'ชื่อโพสต์ต้นฉบับ: "{reddit_title}"\n' if reddit_title else ""
    prompt = (
        f"{title_ctx}"
        "Analyze this image and provide 4 fields separated by a vertical bar '|':\n"
        "1. Image Type: Choose either 'dish' (if it's a close-up of a food dish), 'stall' (if it's a street food stall, market vendor, or shop front), or 'other'.\n"
        "2. Food Name: The Thai name of the food or the type of food stall (1-4 Thai words, e.g., 'ส้มตำ', 'ร้านต้มยำกุ้ง', 'แกงเขียวหวาน'). If it is not related to Thai/Asian food, output 'ไม่ตรงคอนเทน'.\n"
        "3. Local Vibe Description: A short realistic description in Thai (5-8 words) of the local eating/food vibe (e.g., 'น้ำลายสอตั้งแต่เห็นพริกแดง', 'แม่ค้ากำลังตำส้มตำรัวสาก').\n"
        "4. Appeal Level: Choose from these types: ['สายแซ่บสู้ชีวิต', 'วิถีสตรีทฟู้ด', 'รีวิวแซ่บจิกกัด', 'ความหิวยามดึก', 'ข้อพิพาทอาหาร'].\n\n"
        "Format: Image Type | Food Name | Local Vibe Description | Appeal Level\n"
        "Example: dish | ส้มตำ | เหงื่อซิกปากเจ่อแต่สู้ตายจิ้มข้าวเหนียวต่อ | สายแซ่บสู้ชีวิต\n"
        "Example: stall | ร้านส้มตำรถเข็น | ยืนมุงหน้าร้านแย่งชิงเก้าอี้ดนตรีตอนเที่ยง | วิถีสตรีทฟู้ด"
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
            print(f"Vision Analysis: {result}")
            parts = result.split("|")
            image_type = parts[0].strip()
            food_name = parts[1].strip()
            vibe      = parts[2].strip() if len(parts) > 2 else "น้ำลายสอตั้งแต่เห็นพริกแดง"
            genre     = parts[3].strip() if len(parts) > 3 else "วิถีสตรีทฟู้ด"
            return image_type, food_name, vibe, genre
        except Exception as e:
            print(f"[{model}] vision failed: {e}")
    return "dish", reddit_title, "น้ำลายสอตั้งแต่เห็นพริกแดง", "วิถีสตรีทฟู้ด"


# ── Gemini Caption & Hook (Combined for Consistency) ───────────────────
LOCAL_FOODIE_VIBES = {
    "สายแซ่บสู้ชีวิต":   "สั่งส้มตำพริก 10 เม็ดแต่เตรียมยาลดกรดรอ, ปากเจ่อเหงื่อซิกแต่ซดน้ำส้มตำสู้ตาย, นวดสากคุมแม่ค้าแบบแซ่บๆ",
    "วิถีสตรีทฟู้ด":    "ยืนต่อคิวรอโต๊ะกลางแดดตอนเที่ยง, เก้าอี้ดนตรีหน้าร้านส้มตำป้าเข็นรถ, ขอเหนียวปิ้งเพิ่มด่วน",
    "รีวิวแซ่บจิกกัด":  "รีวิวส้มตำปลาร้าที่กลิ่นนัวสะกดใจคนข้างบ้าน, จิกกัดความปากสว่างตูดพังวันพรุ่งนี้, แซวเพื่อนสายกินคลีนที่ยอมจำนนให้ส้มตำ",
    "ความหิวยามดึก":    "ไถฟีดเจอปลาดุกย่างตอนตีสองน้ำลายสอ, ความทรมานของการเห็นของกินแซ่บยามค่ำคืน, ต้มบะหมี่ประทังชีพแต่ยังนึกถึงส้มตำ",
    "ข้อพิพาทอาหาร":   "กะเพราใส่ถั่วฝักยาวเป็นตราบาปไหม, ตำไทยกับตำปลาร้าอะไรคือนิพพาน, ผัดไทยบีบมะนาวหรือเปล่า",
}

REALISM_FILTER = (
    "เขียนเหมือนคนไทยพิมพ์เองใน Facebook เมาท์มอยกัน ไม่ใช่นักการตลาด\n"
    "ภาษาพูดธรรมดา ความคิดแรกในหัวคนไทย ง่ายๆ ตรงๆ ไม่ประดิษฐ์ประดอย\n"
    "avoid: คำคมสอนชีวิต, punchline สวยงาม, ภาษาอวยเกินจริง\n"
    "prioritize: ความตลกขำขัน, ความอยากอาหาร, ความแซ่บนัวสะใจคนไทย\n"
    "ตัวอย่างโทนที่ถูก: 'สั่งเผ็ดน้อยแต่แดงแป๊ดดด', 'ปากเจ่อเหงื่อซิกแต่ยังไหว', 'น้ำลายไหลเลยตั้งแต่คำแรก'\n"
    "ตัวอย่างโทนที่ผิด: 'รสชาติที่ไม่มีที่สิ้นสุด', 'ประสบการณ์ใหม่', ประโยคประดิษฐ์ใดๆ\n"
)


def generate_post_content(img_path, image_type, food_name, vibe, genre, content_type, reddit_title=""):
    with open(img_path, "rb") as f:
        img_data = f.read()

    reactions = LOCAL_FOODIE_VIBES.get(genre, LOCAL_FOODIE_VIBES["วิถีสตรีทฟู้ด"])
    prompt = (
        f"You are an expert Thai social media copywriter for a food page named 'พริก 10 เม็ด' (Spicy Thai Food/Stall content).\n"
        f"Analyze the attached image and generate highly engaging, funny, and relatable Facebook content in THAI language about this food/stall:\n"
        f"- Food/Stall Name: {food_name}\n"
        f"- Image Type: {image_type} (either 'dish' or 'stall')\n"
        f"- Appeal Level: {genre}\n"
        f"- Eating Vibe: {vibe}\n"
        f"- Post Category: {content_type}\n"
        f"- Original Source Context: {reddit_title}\n\n"
        "Post Category descriptions:\n"
        "  * 'สายแซ่บสู้ชีวิต': Thai people eating ultra-spicy food, sweating, mouth burning, but refusing to give up.\n"
        "  * 'วิถีสตรีทฟู้ด': Fun habits of street food lovers, queuing at stalls, lunch rush, fighting for tables.\n"
        "  * 'รีวิวแซ่บจิกกัด': Sarcastic, funny, and direct review of the food, spicy cravings, or morning-after consequences.\n"
        "  * 'ความหิวยามดึก': Sarcastic torture of late-night food cravings, eating instant noodles while dreaming of somtam.\n"
        "  * 'ข้อพิพาทอาหาร': Playful debate about Thai food recipes or ingredients (e.g., whether holy basil should have long beans, boat noodle soup thickness, crispy vs soft oyster omelet) to drive comments.\n\n"
        "Requirements:\n"
        "1. Output exactly 3 sections labeled with markers:\n"
        "   ===HOOK1=== (Hook Line 1: to be written on the image. Very short, 3-6 Thai words. Must feel like a casual first thought)\n"
        "   ===HOOK2=== (Hook Line 2: to be written on the image. Very short, 3-5 Thai words)\n"
        "   ===CAPTION=== (Facebook Caption: a short story structured as 6-8 bullet points. Start each bullet with a ▪️ emoji. 1-2 sentences per bullet.)\n\n"
        "2. Strict Constraints for Natural Thai Style and Spelling (AVOID TYPOS & TRANSLATION ERRORS):\n"
        "   - WRITE IN NATURAL, CASUAL THAI STREET/FACEBOOK STYLE (ภาษาพูดธรรมดา ท้องถิ่น สบายๆ ขำๆ เหมือนแชร์เรื่องฮาๆ ลงกลุ่ม).\n"
        "   - AVOID ENGLISH LITERAL TRANSLATIONS.\n"
        "   - STRICT LOGICAL CONSISTENCY between hooks and caption: Hook lines and caption MUST tell the exact same story.\n"
        "   - STRICT NEGATIVE CONSTRAINT: Absolutely NO mention of foreigners, tourists, westerners, or foreigners reacting to Thai food. Focus 100% on local Thai foodie humor, struggles, and everyday food experiences in Thailand. (ห้ามพูดถึงหรืออ้างอิงถึงชาวต่างชาติ, ฝรั่ง, นักท่องเที่ยว หรือปฏิกิริยาของคนต่างชาติต่ออาหารไทยเด็ดขาด เน้นเฉพาะวิถีชีวิตคนไทยและคนชอบกินเผ็ดในไทยเท่านั้น)\n"
        "   - Do not use markdown like ** or bolding in the caption.\n"
        "   - End the caption with 3 relevant hashtags.\n\n"
        f"Realism Guidelines:\n{REALISM_FILTER}\n"
        "Format of Response:\n"
        "===HOOK1=== [Hook Line 1]\n"
        "===HOOK2=== [Hook Line 2]\n"
        "===CAPTION=== [Facebook Caption]"
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
            print(f"Content Generation [{model}]:\n{result[:300]}...\n")
            
            line1 = "น่าสนใจมาก!"
            line2 = ""
            caption = ""
            
            h1_match = re.search(r'===HOOK1===\s*(.*)', result, re.IGNORECASE)
            h2_match = re.search(r'===HOOK2===\s*(.*)', result, re.IGNORECASE)
            cap_match = re.search(r'===CAPTION===\s*(.*)', result, re.DOTALL | re.IGNORECASE)
            
            if h1_match:
                line1 = h1_match.group(1).split('\n')[0].strip()
            if h2_match:
                line2 = h2_match.group(1).split('\n')[0].strip()
            if cap_match:
                caption = cap_match.group(1).strip()
            
            # Clean label prefixes if any
            label_pattern = r'^(ข้อความในโพสต์\s*Facebook|ข้อความบนรูป|ข้อความในรูป|ข้อความ|คำบรรยาย|คำอธิบาย|บรรทัดที่\s*\d+|บรรทัด\s*\d+|ประโยคที่\s*\d+|ประโยค\s*\d+|Hook\s*text|Hook|Line\s*\d+|[L|l]ine\s*\d+|\d+)\s*[:\-\.\s]\s*'
            line1 = re.sub(label_pattern, '', line1, flags=re.IGNORECASE).strip()
            line2 = re.sub(label_pattern, '', line2, flags=re.IGNORECASE).strip()
            line1 = line1.strip('"\'“”‘’')
            line2 = line2.strip('"\'“”‘’')
            
            if caption:
                return line1, line2, caption
        except Exception as e:
            print(f"[{model}] content generation failed: {e}")
            
    # Fallback
    return food_name[:20], "", f"{food_name} อร่อยมาก!\n#อาหาร #อร่อย"


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
            add_comment(post_id, caption=caption, img_path=img_path)
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
def add_comment(post_id, caption=None, img_path=None):
    from affiliate_utils import get_all_comments
    comments = get_all_comments(caption=caption, img_path=img_path)
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


def generate_debate_content():
    prompt = (
        "You are an expert Thai social media copywriter for 'พริก 10 เม็ด' (Spicy Thai Food page).\n"
        "Generate a highly engaging, funny, and relatable food debate question (ข้อพิพาทอาหาร) in THAI language to drive comments.\n"
        "Topics could be about Thai food ingredients (e.g., holy basil with long beans, sweet green curry, pineapple on pizza/fried rice), eating habits, or restaurant etiquette.\n"
        "Requirements:\n"
        "1. Output exactly 3 sections labeled with markers:\n"
        "   ===HOOK1=== (Hook Line 1: Main statement, very short, 4-6 Thai words. NO emojis)\n"
        "   ===HOOK2=== (Hook Line 2: Question or sub-hook, very short, 3-5 Thai words. NO emojis)\n"
        "   ===CAPTION=== (Facebook Caption: structured as 6-8 bullet points. Start each bullet with a ▪️ emoji. End with 3 relevant hashtags)\n\n"
        "Ensure natural Thai street style, large font readability, and no emojis in the hooks (emojis are fine in the caption).\n"
        "STRICT NEGATIVE CONSTRAINT: Absolutely NO mention of foreigners, tourists, westerners, or foreigners reacting to Thai food. Focus 100% on local Thai foodie humor, struggles, and everyday food experiences in Thailand. (ห้ามพูดถึงหรืออ้างอิงถึงชาวต่างชาติ, ฝรั่ง, นักท่องเที่ยว หรือปฏิกิริยาของคนต่างชาติต่ออาหารไทยเด็ดขาด เน้นเฉพาะวิถีชีวิตคนไทยและคนชอบกินเผ็ดในไทยเท่านั้น)"
    )
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            result = resp.text.strip()
            print(f"Debate Content Generation [{model}]:\n{result[:300]}...\n")
            
            line1 = "กะเพราแท้"
            line2 = "ต้องไม่มีถั่วฝักยาว?"
            caption = ""
            
            h1_match = re.search(r'===HOOK1===\s*(.*)', result, re.IGNORECASE)
            h2_match = re.search(r'===HOOK2===\s*(.*)', result, re.IGNORECASE)
            cap_match = re.search(r'===CAPTION===\s*(.*)', result, re.DOTALL | re.IGNORECASE)
            
            if h1_match:
                line1 = h1_match.group(1).split('\n')[0].strip()
            if h2_match:
                line2 = h2_match.group(1).split('\n')[0].strip()
            if cap_match:
                caption = cap_match.group(1).strip()
            
            # Clean label prefixes if any
            label_pattern = r'^(ข้อความในโพสต์\s*Facebook|ข้อความบนรูป|ข้อความในรูป|ข้อความ|คำบรรยาย|คำอธิบาย|บรรทัดที่\s*\d+|บรรทัด\s*\d+|ประโยคที่\s*\d+|ประโยค\s*\d+|Hook\s*text|Hook|Line\s*\d+|[L|l]ine\s*\d+|\d+)\s*[:\-\.\s]\s*'
            line1 = re.sub(label_pattern, '', line1, flags=re.IGNORECASE).strip()
            line2 = re.sub(label_pattern, '', line2, flags=re.IGNORECASE).strip()
            line1 = line1.strip('"\'“”‘’')
            line2 = line2.strip('"\'“”‘’')
            
            if caption:
                return line1, line2, caption
        except Exception as e:
            print(f"[{model}] debate content generation failed: {e}")
            
    return "กะเพราแท้", "ต้องไม่มีถั่วฝักยาว?", "คุณคิดยังไงกันบ้างครับ?\n#กะเพรา #อาหารไทย #ดราม่าอาหาร"


# ── Main ──────────────────────────────────────────────────────────────
def main():
    print("=== พริก 10 เม็ด Bot ===")

    content_type = random.choice(CONTENT_TYPES)
    print(f"Selected Category: {content_type}")

    if content_type == "ข้อพิพาทอาหาร":
        # 1. Generate text-only debate content
        line1, line2, caption = generate_debate_content()
        print(f"Debate Hooks: {line1} | {line2}")

        # Create temporary file path
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        img_path = tmp.name
        tmp.close()

        # 2. Render Gradient Card
        try:
            from overlay_utils import create_acid_debate_card
            img_path = create_acid_debate_card(line1, line2, img_path)
            print(f"Gradient Card generated: {img_path}")
        except Exception as e:
            print(f"Gradient Card generation failed: {e}")
            return

    else:
        # Original Pexels flow
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

        # Vision วิเคราะห์รูป → food_name + local eating vibe + appeal level
        image_type, food_name, vibe, genre = analyze_image(img_path, reddit_title=reddit_title)
        if not food_name or "ไม่ใช่อาหาร" in food_name or "ไม่ตรงคอนเทน" in food_name:
            print("Not a food image, using Reddit title as fallback")
            food_name = reddit_title
            image_type = "dish"
            vibe      = "น้ำลายสอตั้งแต่เห็นพริกแดง"
            genre     = "วิถีสตรีทฟู้ด"

        print(f"Food: {food_name} | Type: {image_type} | Vibe: {vibe} | Appeal: {genre}")
        line1, line2, caption = generate_post_content(img_path, image_type, food_name, vibe, genre, content_type, reddit_title=reddit_title)
        print(f"Hook: {line1} | {line2}")

        # PIL overlay
        try:
            from overlay_utils import add_overlay
            overlaid = add_overlay(img_path, line1, line2, ACCENT_COLOR)
            os.unlink(img_path)
            img_path = overlaid
        except Exception as e:
            print(f"Overlay failed (using original): {e}")

        caption += f"\n📷 via Pexels"

    print(f"Caption:\n{caption}\n")

    success = post_photo(caption, img_path)
    if not success:
        print("FAILED")


if __name__ == "__main__":
    main()
