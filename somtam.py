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
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "AIzaSyCi6AbETW4XTjJpcbRxj2oL3ftEWRbv_xI")

client      = genai.Client(api_key=GEMINI_API_KEY)
TEXT_MODELS  = ["gemini-2.5-flash", "gemini-1.5-flash-latest"]
IMAGE_MODEL  = "gemini-2.0-flash-exp-image-generation"

HEADERS = {"User-Agent": "Mozilla/5.0"}

# ── Food Topics ───────────────────────────────────────────────────────
FOOD_CATEGORIES = [
    "ส้มตำ",
    "ลาบ หมู/ไก่/เป็ด",
    "ก้อย กุ้ง/ปลา",
    "ข้าวเหนียว",
    "ไก่ย่าง",
    "ซุปหน่อไม้",
    "ต้มแซ่บ",
    "น้ำตกหมู",
    "ยำวุ้นเส้น",
    "แกงอ่อม",
    "ปลาร้าทรงเครื่อง",
    "ส้มตำปูปลาร้า",
    "ส้มตำไทย",
    "ส้มตำซีฟู้ด",
]

CONTENT_TYPES = [
    "สูตร",        # สูตรทำกินเอง
    "เคล็ดลับ",   # tips อาหารอร่อย
    "เมนูแนะนำ",  # แนะนำเมนู
    "ความรู้",    # ความรู้เรื่องอาหาร
]


# ── Gemini Text ───────────────────────────────────────────────────────
def generate_caption(food, content_type):
    prompts = {
        "สูตร": (
            f"เขียน Facebook caption ภาษาไทยสำหรับเพจอาหารอีสาน แนะนำ{content_type}{food}\n"
            "บรรทัด 1: หัวข้อดึงดูด ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2-3: วัตถุดิบหลัก 3-4 อย่าง + วิธีทำสั้นๆ\n"
            "บรรทัด 4: hashtag 3 อัน\n"
            "ห้ามใช้ ** markdown ตอบแค่ caption"
        ),
        "เคล็ดลับ": (
            f"เขียน Facebook caption ภาษาไทยสำหรับเพจอาหาร เคล็ดลับทำ{food}ให้อร่อย\n"
            "บรรทัด 1: หัวข้อสั้น hook คน ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2-3: tips 2-3 ข้อ สั้นมาก\n"
            "บรรทัด 4: hashtag 3 อัน\n"
            "ห้ามใช้ ** markdown ตอบแค่ caption"
        ),
        "เมนูแนะนำ": (
            f"เขียน Facebook caption ภาษาไทยสำหรับเพจอาหาร แนะนำเมนู{food}\n"
            "บรรทัด 1: ประโยคชวนน้ำลายไหล ไม่เกิน 40 ตัวอักษร\n"
            "บรรทัด 2: บรรยายรสชาติสั้นๆ 1 ประโยค\n"
            "บรรทัด 3: คำถามชวนคอมเม้น\n"
            "บรรทัด 4: hashtag 3 อัน\n"
            "ห้ามใช้ ** markdown ตอบแค่ caption"
        ),
        "ความรู้": (
            f"เขียน Facebook caption ภาษาไทยสำหรับเพจอาหาร ความรู้เรื่อง{food}\n"
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
    return f"{food} อร่อยมาก!\n#อาหารไทย #อาหารอีสาน #ส้มตำ"


def clean_text(text):
    text = text.replace("\\n", "\n")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*",     r"\1", text)
    text = re.sub(r"__(.+?)__",     r"\1", text)
    text = re.sub(r"_(.+?)_",       r"\1", text)
    text = re.sub(r"^#+\s*",        "",    text, flags=re.MULTILINE)
    return text.strip()


# ── Gemini Image ──────────────────────────────────────────────────────
def generate_food_image(food, content_type):
    prompt = (
        f"Ultra-realistic Thai food photography of {food}, "
        "professional food styling, natural lighting, shallow depth of field, "
        "vibrant colors, appetizing presentation, wooden table background, "
        "4K quality, Instagram-worthy food photo"
    )
    try:
        resp = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            ),
        )
        for part in resp.candidates[0].content.parts:
            if part.inline_data:
                tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
                tmp.write(part.inline_data.data)
                tmp.close()
                print(f"Image generated: {tmp.name}")
                return tmp.name
    except Exception as e:
        print(f"Image gen failed: {e}")
    return None


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
        resp = requests.post(
            f"https://graph.facebook.com/v21.0/{post_id}/comments",
            data={"access_token": PAGE_ACCESS_TOKEN, "message": msg},
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

    food         = random.choice(FOOD_CATEGORIES)
    content_type = random.choice(CONTENT_TYPES)
    print(f"Food: {food} | Type: {content_type}")

    caption = generate_caption(food, content_type)
    print(f"Caption:\n{caption}\n")

    img_path = generate_food_image(food, content_type)
    if not img_path:
        print("Image generation failed")
        return

    post_photo(caption, img_path)


if __name__ == "__main__":
    main()
