import os
import re
import random
import time
import requests
import tempfile
from google import genai

# ── Config ───────────────────────────────────────────────────────────
PAGE_ID           = "554501167740603"
PAGE_ACCESS_TOKEN = os.environ["SOMTAM_PAGE_ACCESS_TOKEN"]
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
PEXELS_API_KEY    = os.environ["PEXELS_API_KEY"]

client      = genai.Client(api_key=GEMINI_API_KEY)
TEXT_MODELS = ["gemini-2.5-flash", "gemini-3.5-flash"]

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ── Food Topics ───────────────────────────────────────────────────────
FOOD_CATEGORIES = [
    ("ส้มตำ",              "som tum papaya salad thai"),
    ("ลาบหมู",             "larb moo thai minced pork salad"),
    ("ลาบไก่",             "larb gai thai chicken salad"),
    ("ก้อยกุ้ง",           "thai spicy shrimp salad"),
    ("ข้าวเหนียว",         "sticky rice thai food"),
    ("ไก่ย่าง",            "thai grilled chicken"),
    ("ซุปหน่อไม้",         "bamboo shoot soup thai"),
    ("ต้มแซ่บ",            "tom saep spicy thai soup"),
    ("น้ำตกหมู",           "waterfall pork thai food"),
    ("ยำวุ้นเส้น",         "glass noodle salad thai"),
    ("แกงอ่อม",            "thai herb curry"),
    ("ปลาร้าทรงเครื่อง",   "pla ra thai fermented fish"),
    ("ส้มตำปูปลาร้า",      "som tum crab thai"),
    ("ส้มตำไทย",           "som tum thai classic"),
    ("ส้มตำซีฟู้ด",        "som tum seafood thai"),
]

CONTENT_TYPES = [
    "สูตร",
    "เคล็ดลับ",
    "เมนูแนะนำ",
    "ความรู้",
]


# ── Pexels ────────────────────────────────────────────────────────────
def get_pexels_image(query):
    """ดึงรูปจาก Pexels ตาม keyword — คืน (image_url, photographer)"""
    try:
        resp = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={"query": query, "per_page": 15, "orientation": "landscape"},
            timeout=10,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos:
            print(f"Pexels: no results for '{query}'")
            return None, None
        photo = random.choice(photos)
        url = photo["src"]["large"]
        photographer = photo.get("photographer", "")
        print(f"Pexels: picked photo by {photographer} | {url[:60]}")
        return url, photographer
    except Exception as e:
        print(f"Pexels error: {e}")
        return None, None


def download_image(url):
    """Download รูปจาก URL คืน temp file path"""
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
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.write(data)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"Image download failed: {e}")
        return None


# ── Gemini Text ───────────────────────────────────────────────────────
def generate_caption(food_name, content_type):
    prompts = {
        "สูตร": (
            f"เขียน Facebook caption ภาษาไทยสำหรับเพจอาหารอีสาน แนะนำสูตร{food_name}\n"
            "บรรทัด 1: หัวข้อดึงดูด ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2-3: วัตถุดิบหลัก 3-4 อย่าง + วิธีทำสั้นๆ\n"
            "บรรทัด 4: hashtag 3 อัน\n"
            "ห้ามใช้ ** markdown ตอบแค่ caption"
        ),
        "เคล็ดลับ": (
            f"เขียน Facebook caption ภาษาไทยสำหรับเพจอาหาร เคล็ดลับทำ{food_name}ให้อร่อย\n"
            "บรรทัด 1: หัวข้อสั้น hook คน ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2-3: tips 2-3 ข้อ สั้นมาก\n"
            "บรรทัด 4: hashtag 3 อัน\n"
            "ห้ามใช้ ** markdown ตอบแค่ caption"
        ),
        "เมนูแนะนำ": (
            f"เขียน Facebook caption ภาษาไทยสำหรับเพจอาหาร แนะนำเมนู{food_name}\n"
            "บรรทัด 1: ประโยคชวนน้ำลายไหล ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2: บรรยายรสชาติสั้นๆ 1 ประโยค\n"
            "บรรทัด 3: คำถามชวนคอมเม้น\n"
            "บรรทัด 4: hashtag 3 อัน\n"
            "ห้ามใช้ ** markdown ตอบแค่ caption"
        ),
        "ความรู้": (
            f"เขียน Facebook caption ภาษาไทยสำหรับเพจอาหาร ความรู้เรื่อง{food_name}\n"
            "บรรทัด 1: fact น่าสนใจ ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2: อธิบายสั้นๆ 1-2 ประโยค\n"
            "บรรทัด 3: hashtag 3 อัน\n"
            "ห้ามใช้ ** markdown ตอบแค่ caption"
        ),
    }
    prompt = prompts.get(content_type, prompts["เมนูแนะนำ"])
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            return clean_text(resp.text.strip())
        except Exception as e:
            print(f"[{model}] caption failed: {e}")
    return f"{food_name} อร่อยมาก!\n#อาหารไทย #อาหารอีสาน #ส้มตำ"


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
                data={
                    "message":      caption,
                    "access_token": PAGE_ACCESS_TOKEN,
                },
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
    delay0 = random.uniform(60, 180)
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

    food_name, food_query = random.choice(FOOD_CATEGORIES)
    content_type          = random.choice(CONTENT_TYPES)
    print(f"Food: {food_name} | Type: {content_type} | Query: {food_query}")

    # ดึงรูปจาก Pexels
    img_url, _ = get_pexels_image(food_query)
    if not img_url:
        print("Pexels failed")
        return

    img_path = download_image(img_url)
    if not img_path:
        print("Download failed")
        return

    caption = generate_caption(food_name, content_type)
    if photographer:
        caption += f"\n📷 Photo by {photographer} via Pexels"
    print(f"Caption:\n{caption}\n")

    post_photo(caption, img_path)


if __name__ == "__main__":
    main()
