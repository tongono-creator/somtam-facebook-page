import os
import re
import random
import time
import requests
import tempfile
import xml.etree.ElementTree as ET
from google import genai
from google.genai import types

# ── Config ───────────────────────────────────────────────────────────
PAGE_ID           = "554501167740603"
PAGE_ACCESS_TOKEN = os.environ["SOMTAM_PAGE_ACCESS_TOKEN"]
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")

client       = genai.Client(api_key=GEMINI_API_KEY)
TEXT_MODELS  = ["gemini-2.5-flash", "gemini-3.5-flash"]
ACCENT_COLOR = (255, 107, 53)  # ส้ม #FF6B35

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SomtamBot/1.0; +github)"}

# ── Food Subreddits ──────────────────────────────────────────────────
FOOD_SUBREDDITS = [
    "FoodPorn",
    "food",
    "tonightsdinner",
    "streetfood",
    "DessertPorn",
    "Cooking",
    "recipes",
    "MealPrepSunday",
    "eatsandwiches",
    "sushi",
    "Pizza",
    "ramen",
    "noodles",
    "BBQ",
    "grilling",
]

IMAGE_EXTS   = (".jpg", ".jpeg", ".png", ".gif", ".webp")
CONTENT_TYPES = ["ความรู้", "tips", "เคล็ดลับ", "เมนูแนะนำ", "ตลก"]


# ── Reddit RSS ────────────────────────────────────────────────────────
def get_reddit_food_post():
    subreddit = random.choice(FOOD_SUBREDDITS)
    url = f"https://www.reddit.com/r/{subreddit}/hot.rss"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        root    = ET.fromstring(resp.content)
        ns      = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall("atom:entry", ns)

        image_posts = []
        for entry in entries:
            title   = entry.findtext("atom:title", "", ns).strip()
            content = entry.findtext("atom:content", "", ns)
            img_urls = re.findall(
                r'https?://[^\s"<>]+\.(?:jpg|jpeg|png|gif|webp)', content or ""
            )
            good_imgs = [u for u in img_urls if "i.redd.it" in u or "imgur.com" in u]
            if good_imgs and title:
                image_posts.append({
                    "title":     title,
                    "url":       good_imgs[0],
                    "subreddit": subreddit,
                })

        if not image_posts:
            print(f"[{subreddit}] no image posts in RSS")
            return None

        post = random.choice(image_posts[:10])
        print(f"[{subreddit}] picked: {post['title'][:60]}")
        return post

    except Exception as e:
        print(f"Reddit error ({subreddit}): {e}")
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
def analyze_image(img_path):
    """ดูรูปแล้วบอก food_name | vibe | genre"""
    with open(img_path, "rb") as f:
        img_data = f.read()
    prompt = (
        "ดูรูปนี้แล้วตอบ 3 อย่าง แยกด้วย | :\n"
        "1. ชื่ออาหาร ภาษาไทย 1-4 คำ\n"
        "2. ความรู้สึกแรกที่เห็น เช่น น่ากินมาก, ดูแห้งๆ, ดูตลกแปลก, หน้าตาประหลาด\n"
        "3. ประเภทอาหารในชีวิตจริง เลือก 1 จาก: "
        "ข้าวแกง, street_snack, บุฟเฟต์, ร้านตามสั่ง, ของหวาน, comfort_food, "
        "หมูกระทะ, ของตลาด, อาหารตะวันตก, ซูชิ, ราเมน, พิซซ่า, อาหารทะเล, อื่นๆ\n"
        "ตัวอย่าง: ข้าวแกง|น่ากินมาก หลากหลายถาด|ข้าวแกง\n"
        "ตัวอย่าง: ไก่ทอด|กรอบน่ากิน|street_snack\n"
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
            vibe      = parts[1].strip() if len(parts) > 1 else "ธรรมดา"
            genre     = parts[2].strip() if len(parts) > 2 else "อื่นๆ"
            return food_name, vibe, genre
        except Exception as e:
            print(f"[{model}] vision failed: {e}")
    return None, None, None


# ── Gemini Caption ────────────────────────────────────────────────────
# emotional triggers ตาม food genre — แต่ละ genre มี "ความรู้สึก" ที่คนไทยนึกถึงต่างกัน
GENRE_TRIGGERS = {
    "ข้าวแกง":       "ตักเพลินจนข้าวหมด, ร้านลับไม่มีป้าย, กับข้าวบ้านๆ ที่อันตราย, สิ้นเดือนก็ยังแวะ, บอกว่าเอา 2 อย่างสรุป 5",
    "street_snack":  "หยุดนิ้วไม่ได้, ซื้อเล่นๆ สรุปหมดถุง, ริมทางแต่อร่อยเกินร้านหรู, ของที่คำว่าพอไม่มีความหมาย",
    "บุฟเฟต์":       "กินให้คุ้มค่าตัว, รอบสองไม่อาย, มาหิวกลับอิ่ม, ลากจานไม่หยุด",
    "ร้านตามสั่ง":   "สั่งเพิ่มทุกครั้ง, ใส่ไข่ดาวสิ, ราคาเป็นมิตร แต่อ้วนไม่เป็นมิตร, ร้านดังไม่มีป้ายราคา",
    "ของหวาน":       "ความรู้สึกผิดที่อร่อย, ลดน้ำหนักไว้ก่อนแล้วกัน, หวานจนต้องนั่งสักครู่, คำเดียวก็ยังเกินพอ",
    "comfort_food":  "วันเหนื่อยต้องอันนี้, กินคนเดียวก็โอเค, บ้านๆ แต่ถูกใจ, ไม่สวยแต่อิ่มใจ",
    "หมูกระทะ":      "ปิ้งเองได้ที่, น้ำจิ้มแจ่มมาก, ควันหอม, ไปกันทีละโต๊ะใหญ่",
    "ของตลาด":       "เดินตลาดแล้วแวะ, ซื้อกลับบ้านทีละถุง, ราคาเป็นมิตร, ตื่นเช้ามาเพื่ออันนี้",
    "อาหารตะวันตก": "แพงแต่คุ้ม, ร้าน aesthetic, instagrammable, ฝรั่งกินแล้วยังต้องถ่ายรูป",
    "ซูชิ":          "กินเอง vs ร้านดัง ต่างกันมาก, สดจนต้องหลับตา, ราเตคืนเดียวสบาย",
    "ราเมน":         "น้ำซุปดูดหมดชาม, เส้นเหนียวพอดี, กินคนเดียวในร้านเงียบๆ",
    "พิซซ่า":        "ชีสยืดเป็นเมตร, สั่งมาแชร์แต่สุดท้ายกินคนเดียว, ขอบหนาหรือบาง eternal debate",
    "อาหารทะเล":     "สดมาก, กลิ่นทะเล, ต้มยำหม้อใหญ่, กุ้งตัวโต",
    "อื่นๆ":         "น่ากิน, อยากลอง, หิวขึ้นมาเฉยๆ",
}

REALISM_FILTER = (
    "เขียนเหมือนคนพิมพ์เองใน Facebook ไม่ใช่นักการตลาด\n"
    "ภาษาพูดธรรมดา ความคิดแรกที่นึกได้ ง่ายๆ ตรงๆ\n"
    "avoid: คำคม, punchline ประดิษฐ์, คำเปรียบเทียบแปลกๆ, ภาษาสวย\n"
    "prioritize: ความหิว, ความรู้สึกผิด, ความจริงของมนุษย์, ความบ้านๆ\n"
    "ตัวอย่างโทนที่ถูก: 'กินเล่น สรุปหมดถาด', 'เมนูที่ทำให้คำว่าเดี๋ยวค่อยลดพัง', 'ดูจากสีก็รู้ละว่าอร่อย'\n"
    "ตัวอย่างโทนที่ผิด: 'กรอบแบบตะโกน', 'ฟินจนมือวางไม่ลง', ประโยคประดิษฐ์ใดๆ\n"
)


def generate_hook(food_name, vibe, genre, content_type):
    triggers = GENRE_TRIGGERS.get(genre, GENRE_TRIGGERS["อื่นๆ"])
    is_funny = content_type == "ตลก" or any(w in vibe for w in ["ตลก", "แปลก", "เศร้า", "แห้ง", "ประหลาด", "บังคับ"])
    if is_funny:
        style = (
            f"รูป: {food_name} | ประเภท: {genre} | ความรู้สึกแรก: {vibe}\n"
            f"emotional context ของ {genre}: {triggers}\n"
            "เขียน hook text แนวแซว/กวนๆ ให้ตรง genre สำหรับใส่บนรูป\n"
            "บรรทัด 1: มุกง่ายๆ 3-5 คำ เหมือนความคิดแรกในหัวคน\n"
            "บรรทัด 2: ต่อสั้น 4-6 คำ\n"
        )
    else:
        style = (
            f"รูป: {food_name} | ประเภท: {genre} | ความรู้สึกแรก: {vibe}\n"
            f"emotional context ของ {genre}: {triggers}\n"
            "เขียน hook text สำหรับใส่บนรูปอาหาร ให้ตรง genre\n"
            "บรรทัด 1: hook 3-5 คำ ตรงๆ ไม่ประดิษฐ์\n"
            "บรรทัด 2: คำถาม/ประโยคสั้น 4-7 คำ\n"
        )
    prompt = f"{style}{REALISM_FILTER}ตอบแค่ 2 บรรทัด ไม่มี hashtag ไม่มี **"
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            lines = clean_text(resp.text.strip()).split("\n")
            lines = [l.strip() for l in lines if l.strip()]
            return lines[0] if lines else food_name[:20], lines[1] if len(lines) > 1 else ""
        except Exception as e:
            print(f"[{model}] hook failed: {e}")
    return food_name[:20], ""


def generate_caption(food_name, vibe, genre, content_type, subreddit):
    triggers = GENRE_TRIGGERS.get(genre, GENRE_TRIGGERS["อื่นๆ"])
    # human framework prompt — ใช้กับทุก type
    human_base = (
        f"อาหาร: {food_name} | ประเภท: {genre}\n"
        f"ความรู้สึกแรกที่เห็นรูปนี้: {vibe}\n"
        f"emotional context ของ {genre} ที่คนไทยนึกถึง: {triggers}\n\n"
        + REALISM_FILTER +
        "ถ้ารูปดูแปลก/ไม่น่ากิน/ตลก → เล่นมุกได้ ห้ามอวยอัตโนมัติ\n"
        "ถ้ารูปดูน่ากิน → เขียนให้คนรู้สึกหิวหรือรู้สึกผิด ใช้ emotional context ของ genre\n\n"
    )
    prompts = {
        "ความรู้": (
            human_base +
            "เขียน Facebook caption แนวให้ความรู้สนุกๆ\n"
            "บรรทัด 1: fact หรือ hook ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2: อธิบายสั้นๆ 1-2 ประโยค\n"
            "บรรทัด 3: hashtag 3 อัน\n"
            "ห้ามใช้ ** ตอบแค่ caption"
        ),
        "tips": (
            human_base +
            "เขียน Facebook caption แนว tips กินหรือทำ\n"
            "บรรทัด 1: hook ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2-3: tips 2 ข้อสั้นๆ\n"
            "บรรทัด 4: hashtag 3 อัน\n"
            "ห้ามใช้ ** ตอบแค่ caption"
        ),
        "เคล็ดลับ": (
            human_base +
            "เขียน Facebook caption แนวเคล็ดลับทำให้อร่อย\n"
            "บรรทัด 1: hook ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2-3: เคล็ดลับ 2-3 ข้อ\n"
            "บรรทัด 4: hashtag 3 อัน\n"
            "ห้ามใช้ ** ตอบแค่ caption"
        ),
        "เมนูแนะนำ": (
            human_base +
            "เขียน Facebook caption ชวนลองกิน\n"
            "บรรทัด 1: ประโยคชวนกิน ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2: บรรยายรสชาติสั้นๆ\n"
            "บรรทัด 3: คำถามชวนคอมเม้น\n"
            "บรรทัด 4: hashtag 3 อัน\n"
            "ห้ามใช้ ** ตอบแค่ caption"
        ),
        "ตลก": (
            human_base +
            "เขียน Facebook caption แนวตลก/แซว/กวนๆ เหมือนคอมเมนต์ไวรัล\n"
            "ไม่ต้องบรรยายภาพตรงๆ ไม่ต้องขายของ ไม่ต้องโลกสวย\n"
            "โทน: ตลกธรรมชาติ เหมือนความคิดในหัวคน สั้น กระแทก มีความ 'อิหยังวะ'\n"
            "บรรทัด 1: มุก/แซว ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2: ต่อมุกหรือชวนคอมเม้น\n"
            "บรรทัด 3: hashtag 2-3 อัน\n"
            "ห้ามใช้ ** ตอบแค่ caption"
        ),
    }
    prompt = prompts.get(content_type, prompts["เมนูแนะนำ"])
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
        post = get_reddit_food_post()
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

    # Vision วิเคราะห์รูปจริงๆ → food_name + vibe + genre
    food_name, vibe, genre = analyze_image(img_path)
    if not food_name or "ไม่ใช่อาหาร" in food_name:
        print("Not a food image, using Reddit title as fallback")
        food_name = post["title"]
        vibe      = "ธรรมดา"
        genre     = "อื่นๆ"

    print(f"Food: {food_name} | Genre: {genre} | Vibe: {vibe}")
    content_type = random.choice(CONTENT_TYPES)
    line1, line2 = generate_hook(food_name, vibe, genre, content_type)
    print(f"Hook: {line1} | {line2}")

    # PIL overlay
    try:
        from overlay_utils import add_overlay
        overlaid = add_overlay(img_path, line1, line2, ACCENT_COLOR)
        os.unlink(img_path)
        img_path = overlaid
    except Exception as e:
        print(f"Overlay failed (using original): {e}")

    caption = generate_caption(food_name, vibe, genre, content_type, post["subreddit"])
    caption += f"\n📷 via r/{post['subreddit']}"
    print(f"Caption:\n{caption}\n")

    success = post_photo(caption, img_path)
    if not success:
        print("FAILED")


if __name__ == "__main__":
    main()
