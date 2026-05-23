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
    """ดูรูปแล้วบอกว่าอาหารอะไร + ความรู้สึกแรกที่เห็น"""
    with open(img_path, "rb") as f:
        img_data = f.read()
    prompt = (
        "ดูรูปนี้แล้วตอบ 2 อย่าง แยกด้วย | :\n"
        "1. ชื่ออาหาร ภาษาไทย 1-4 คำ เช่น ส้มตำ, ไก่ย่าง, พิซซ่า\n"
        "2. ความรู้สึกแรกที่เห็น เช่น น่ากินมาก, ดูแห้งๆ, ดูตลกแปลก, ดูเศร้า, หน้าตาประหลาด, ดูธรรมดา\n"
        "ตัวอย่าง: ข้าวปั้น|ดูเหมือนโดนบังคับมาทำ\n"
        "ถ้าไม่ใช่อาหาร ตอบว่า: ไม่ใช่อาหาร|ไม่เกี่ยว"
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
            # parse food_name|vibe
            parts = result.split("|", 1)
            food_name = parts[0].strip()
            vibe      = parts[1].strip() if len(parts) > 1 else "ธรรมดา"
            return food_name, vibe
        except Exception as e:
            print(f"[{model}] vision failed: {e}")
    return None, None


# ── Gemini Caption ────────────────────────────────────────────────────
def generate_hook(food_name, vibe, content_type):
    if content_type == "ตลก" or any(w in vibe for w in ["ตลก", "แปลก", "เศร้า", "แห้ง", "ประหลาด", "บังคับ"]):
        style = (
            f"รูป: {food_name} | ความรู้สึกแรก: {vibe}\n"
            "เขียน hook text แนวแซว/ฮา/กวนๆ สำหรับใส่บนรูป\n"
            "บรรทัด 1: hook ตลก 3-5 คำ เหมือนคอมเมนต์ไวรัล\n"
            "บรรทัด 2: ต่อมุกสั้น 4-6 คำ"
        )
    else:
        style = (
            f"รูป: {food_name} | ความรู้สึกแรก: {vibe}\n"
            "เขียน hook text สั้นๆ ภาษาไทย สำหรับใส่บนรูปอาหาร\n"
            "บรรทัด 1: hook 3-5 คำ ชวนน้ำลายไหล\n"
            "บรรทัด 2: คำถาม/เคล็ดลับสั้น 4-7 คำ"
        )
    prompt = f"{style}\nตอบแค่ 2 บรรทัด ไม่มี hashtag ไม่มี **"
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            lines = clean_text(resp.text.strip()).split("\n")
            lines = [l.strip() for l in lines if l.strip()]
            return lines[0] if lines else food_name[:20], lines[1] if len(lines) > 1 else ""
        except Exception as e:
            print(f"[{model}] hook failed: {e}")
    return food_name[:20], ""


def generate_caption(food_name, vibe, content_type, subreddit):
    # human framework prompt — ใช้กับทุก type
    human_base = (
        f"อาหาร: {food_name}\n"
        f"ความรู้สึกแรกที่เห็นรูปนี้: {vibe}\n\n"
        "คิดเหมือนคนไถ Facebook จริงๆ ไม่ใช่นักการตลาด\n"
        "วิเคราะห์อารมณ์จากภาพ เดาความรู้สึกแรกที่คนเห็น\n"
        "ถ้ารูปดูแปลก/ไม่น่ากิน/ตลก → เล่นมุกได้ ห้ามอวยอัตโนมัติ\n"
        "ถ้ารูปดูน่ากิน → บรรยายแบบทำให้น้ำลายไหลจริงๆ\n\n"
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

    # Vision วิเคราะห์รูปจริงๆ → food_name + vibe
    food_name, vibe = analyze_image(img_path)
    if not food_name or "ไม่ใช่อาหาร" in food_name:
        print("Not a food image, using Reddit title as fallback")
        food_name = post["title"]
        vibe      = "ธรรมดา"

    print(f"Food: {food_name} | Vibe: {vibe}")
    content_type = random.choice(CONTENT_TYPES)
    line1, line2 = generate_hook(food_name, vibe, content_type)
    print(f"Hook: {line1} | {line2}")

    # PIL overlay
    try:
        from overlay_utils import add_overlay
        overlaid = add_overlay(img_path, line1, line2, ACCENT_COLOR)
        os.unlink(img_path)
        img_path = overlaid
    except Exception as e:
        print(f"Overlay failed (using original): {e}")

    caption = generate_caption(food_name, vibe, content_type, post["subreddit"])
    caption += f"\n📷 via r/{post['subreddit']}"
    print(f"Caption:\n{caption}\n")

    success = post_photo(caption, img_path)
    if not success:
        print("FAILED")


if __name__ == "__main__":
    main()
