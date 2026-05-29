import os
import re
import random
import time
import requests
import tempfile
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from google import genai
from google.genai import types

# ── Config ───────────────────────────────────────────────────────────
PAGE_ID           = "554501167740603"
PAGE_ACCESS_TOKEN = os.environ.get("SOMTAM_PAGE_ACCESS_TOKEN", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "") or "DUMMY_KEY"
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY", "")

client       = genai.Client(api_key=GEMINI_API_KEY, http_options={'timeout': 90.0})
TEXT_MODELS  = ["gemini-2.5-flash", "gemini-3.5-flash"]
ACCENT_COLOR = (255, 107, 53)  # ส้ม #FF6B35

def contains_thai(text):
    if not text:
        return False
    return bool(re.search(r'[\u0e00-\u0e7f]', text))

def segment_thai_text(text, client=client):
    if not text or not contains_thai(text):
        return text
    prompt = (
        "You are an expert Thai word segmentation tool. "
        "Your task is to insert a zero-width space character (\\u200b) at every natural word boundary in the provided Thai text. "
        "Strict rules:\n"
        "1. Do NOT modify, delete, or add any words, characters, punctuation, spaces, or newlines of the original text. "
        "Keep the exact same characters and layout.\n"
        "2. Do NOT add any introductory or concluding remarks. Output ONLY the segmented text.\n"
        "3. Ensure words like 'หวยออก', 'เงินเก็บ', 'แสนแรก', 'ทำงาน' are segmented at their natural boundaries (e.g., 'หวย\\u200bออก' or left as 'หวยออก', but never break syllables awkwardly).\n\n"
        f"Text to segment:\n{text}"
    )
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            segmented = resp.text.strip()
            clean_orig = text.replace('\\u200b', '')
            clean_seg = segmented.replace('\\u200b', '')
            if len(clean_orig) == len(clean_seg):
                return segmented
        except Exception as e:
            print(f"[{model}] segment_thai_text failed: {e}")
    return text

def translate_to_thai(text):
    if not text:
        return ""
    if contains_thai(text):
        return text
    prompt = f"Translate the following food-related English text to natural Thai food vocabulary. Only output the translation, no explanation:\n\n{text}"
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            translated = resp.text.strip()
            if contains_thai(translated):
                return translated
        except Exception as e:
            print(f"[{model}] Translation failed: {e}")
    return text  # Fallback to original text if translation fails

FALLBACK_POSTS = {
    "recipe": [
        {
            "title": "ส้มตำป่าทะเลครกแตก",
            "desc": "เมนูสุดแซ่บจัดเต็มยกทะเลมาไว้ในครก เผ็ดร้อนถึงใจสะท้านทรวงค่ะ",
            "ingredients": "• เส้นมะละกอดิบสับ 1 กำมือ\n• กุ้งสดแกะเปลือก 5 ตัว\n• ปลาหมึกหั่นแว่น 5 ชิ้น\n• พริกขี้หนูสวน 10 เม็ด\n• มะเขือเทศสีดา 2 ลูก\n• ผักกาดดองหั่น 1 ช้อนโต๊ะ\n• น้ำปลาร้าต้มสุก 2 ช้อนโต๊ะ\n• น้ำมะนาว 2 ช้อนโต๊ะ",
            "steps": "1. โขลกพริกขี้หนูและกระเทียมให้พอแตก\n2. ใส่มะเขือเทศ ผักกาดดอง และเครื่องปรุงทั้งหมดโขลกเบาๆ\n3. ใส่เส้นมะละกอ กุ้งสด และปลาหมึกลวกสุก คลุกเคล้าให้เข้ากัน\n4. ตักใส่ถาดพร้อมแซ่บกับผักสดและแคบหมูค่ะ",
            "caption": "▪️ ดึกแล้วท้องมันร้องหาความนัวระดับสิบใช่ไหมคะ\n▪️ วันนี้หนูพาสูตรส้มตำป่าทะเลครกแตกมาแจกค่ะ\n▪️ เครื่องแน่นล้นครก รสชาติเผ็ดแซ่บสะท้านทรวง\n▪️ ทำเองที่บ้านได้ง่ายๆ ไม่ต้องง้อร้านดัง\n▪️ มะนาวแท้ๆ ปลาร้านัวๆ กุ้งเด้งสู้ฟันสุดๆ ค่ะ\n▪️ เมนต์บอกหนูหน่อยว่าใครอยากชิมฝีมือหนูบ้างคะ\n#ส้มตำป่า #สูตรส้มตำ #พริก10เม็ด"
        },
        {
            "title": "ตำหลวงพระบางนัวปลาร้า",
            "desc": "ส้มตำเส้นแบนบางกรอบ ซึมซับน้ำปลาร้าเข้มข้นอร่อยนัวทุกคำค่ะ",
            "ingredients": "• มะละกอฝานแผ่นบาง 1 กำมือ\n• พริกแห้งและพริกสด 10 เม็ด\n• น้ำปลาร้าปรุงรสเข้มข้น 2.5 ช้อนโต๊ะ\n• น้ำตาลปี๊บ 1 ช้อนโต๊ะ\n• กะปิแท้ 1/2 ช้อนชา\n• มะเขือเครือ 3 ลูก\n• มะนาวแป้น 2 ลูก",
            "steps": "1. โขลกพริกแห้ง พริกสด และกะปิให้เข้ากัน\n2. ใส่น้ำตาลปี๊บ มะเขือเครือ บีบมะนาวใส่ทั้งเปลือกโขลกเบาๆ\n3. เติมน้ำปลาร้านัวๆ คนให้ละลายดี\n4. ใส่เส้นมะละกอแผ่นบาง คลุกเคล้าให้ซึมซับน้ำตำหลวงพระบาง\n5. โรยเม็ดกระถินตักเสิร์ฟพร้อมกากหมูเจียวค่ะ",
            "caption": "▪️ ใครชอบกินส้มตำเส้นแบนบางกรอบเชิญทางนี้เลยค่ะ\n▪️ ตำหลวงพระบางสูตรนี้แอดมินพี่สาวคอนเฟิร์มว่านัวมาก\n▪️ เส้นบางๆ ซับน้ำปลาร้ากับกะปิหอมๆ เข้าเนื้อสุดๆ\n▪️ กลิ่นโชยไปถึงปากซอย ข้างบ้านต้องถามว่าตำอะไร\n▪️ ทานคู่กับกากหมูเจียวใหม่ๆ และเม็ดกระถินคือที่สุด\n▪️ เซฟสูตรนี้ไว้ทำตามด่วนๆ เลยนะคะสาวๆ\n#ตำหลวงพระบาง #ส้มตำปลาร้า #พริก10เม็ด"
        },
        {
            "title": "กะเพราเนื้อสับพริกแห้ง",
            "desc": "กะเพราแท้สูตรโบราณ เผ็ดร้อนแห้งสนิทไม่ใส่ผักกาดขาวค่ะ",
            "ingredients": "• เนื้อวัวสับติดมัน 200 กรัม\n• พริกแห้งแดงและเขียว 10 เม็ด\n• กระเทียมไทย 1 หัว\n• ใบกะเพราป่าแดง 1 กำมือ\n• ซอสปรุงรส 1 ช้อนโต๊ะ\n• น้ำปลาแท้ 1 ช้อนโต๊ะ\n• น้ำตาลทรายปลายช้อนชา",
            "steps": "1. โขลกพริกแห้งและกระเทียมให้ละเอียดพอประมาณ\n2. ตั้งกระทะร้อนจัด นำพริกกระเทียมลงผัดจนฉุนกระเจิง\n3. ใส่เนื้อสับลงผัด ยีให้กระจายตัวและผัดจนแห้งเข้าเนื้อ\n4. ปรุงรสด้วยน้ำปลา ซอสปรุงรส และน้ำตาลเล็กน้อย\n5. ใส่ใบกะเพราป่า ผัดเร็วๆ ด้วยไฟแรงแล้วยกลงทันทีค่ะ",
            "caption": "▪️ เบื่อไหมคะกับการสั่งผัดกะเพราแล้วได้ถั่วฝักยาวแถมมา\n▪️ วันนี้แอดมินหนูขอแจกสูตรกะเพราเนื้อสับพริกแห้งแท้ๆ ค่ะ\n▪️ ผัดแบบแห้งๆ คั่วพริกหอมฉุนขึ้นจมูกจามกันทั้งบ้าน\n▪️ ใบกะเพราป่าแดงกลิ่นหอมแรงถึงใจไม่มีผักอื่นเจือปน\n▪️ โปะไข่ดาวกรอบๆ ขอบไหม้ไข่แดงเยิ้มๆ คือนิพพาน\n▪️ ไหนใครชอบกะเพราแห้งๆ เหมือนกันบ้าง มารายงานตัวด่วนค่ะ\n#กะเพราเนื้อสับ #กะเพราพริกแห้ง #พริก10เม็ด"
        }
    ],
    "contrast_review": [
        {
            "line1": "สั่งเผ็ดน้อย",
            "line2": "แต่แดงทั้งครก",
            "caption": "▪️ สั่งแม่ค้าว่าเผ็ดน้อยทีไร ได้สีแดงแป๊ดมาตลอดเลยค่ะ\n▪️ ในใจแม่ค้าคงคิดว่าพริก 10 เม็ดคือเลเวลอนุบาล\n▪️ ปากเจ่อเหงื่อไหลยาลดกรดต้องเข้าแล้วค่ะงานนี้\n▪️ แต่ในฐานะนักสู้เรื่องกิน เราไม่มียอมแพ้แน่นอนค่ะ\n▪️ ใครเคยสั่งเผ็ดน้อยแล้วได้เผ็ดร้อนระเบิดรูทวารแบบนี้บ้างคะ\n#สั่งเผ็ดน้อย #แซ่บสู้ชีวิต #พริก10เม็ด"
        },
        {
            "line1": "กินตอนนี้แซ่บปาก",
            "line2": "พรุ่งนี้ลำบากตูด",
            "caption": "▪️ วงการส้มตำเข้าแล้วออกยาก แต่เข้าห้องน้ำออกยากกว่าค่ะ\n▪️ ตอนกินคือนัวสะใจ พริกแห้งพริกสดจัดเต็มไม่มีกั๊ก\n▪️ พรุ่งนี้เช้าเตรียมตัวรับแรงกระแทกแบบสู้ชีวิตเลยค่ะ\n▪️ สัญญาณเตือนภัยในท้องเริ่มทำงานตั้งแต่ยังกินไม่หมดจาน\n▪️ แต่ถามว่าจะเข็ดไหม ตอบเลยว่าพรุ่งนี้เย็นเจอกันใหม่ค่ะ\n#อร่อยแซ่บ #เตือนภัยสายกิน #พริก10เม็ด"
        },
        {
            "line1": "คิวยาวเป็นกิโล",
            "line2": "แต่ยอมยืนรอ",
            "caption": "▪️ วิถีคนหิวที่แท้จริงคือการยืนรอคิวหน้าร้านส้มตำค่ะ\n▪️ แดดจะร้อนลมจะแรงแค่ไหนก็ทำอะไรความอยากกินไม่ได้\n▪️ แย่งชิงเก้าอี้ดนตรีตอนเที่ยงวันเหมือนไปรบในสนามรบ\n▪️ พอได้กินคำแรกปลาร้านัวๆ เท่านั้นแหละ หายเหนื่อยทันทีค่ะ\n▪️ ใครยอมยืนต่อคิวเพื่อของอร่อยบ้างคะรายงานตัวด่วน\n#รีวิวสตรีทฟู้ด #ส้มตำคิวยาว #พริก10เม็ด"
        }
    ],
    "debate": [
        {
            "left_label": "ส้มตำปลาร้า",
            "right_label": "ส้มตำไทย",
            "line1": "ตำไทย หรือ ตำปลาร้า",
            "line2": "อะไรคือนิพพาน?",
            "caption": "▪️ ศึกวันดวลเดือดแห่งวงการส้มตำไทยเลยค่ะทุกคน\n▪️ ฝั่งส้มตำปลาร้านัวสะใจ กลิ่นหอมฟุ้งแซ่บถึงทรวง\n▪️ หรือฝั่งส้มตำไทยเปรี้ยวหวานเคี้ยวมันถั่วลิสงคั่วเกลือ\n▪️ แต่ละทีมคือน่าอร่อยกินกันไม่ลงจริงๆ นะคะสาวๆ\n▪️ เมนต์บอกหนูหน่อยว่ามื้อเที่ยงนี้ทุกคนอยู่ทีมไหนกันคะ\n#ตำไทย #ตำปลาร้า #ศึกส้มตำ"
        },
        {
            "left_label": "กะเพราแท้",
            "right_label": "ใส่ถั่วฝักยาว",
            "line1": "กะเพราแท้มีแค่ใบ",
            "line2": "หรือมีผักร่วมด้วย?",
            "caption": "▪️ ประเด็นร้อนถกเถียงกันมาทุกยุคทุกสมัยไม่เคยจบค่ะ\n▪️ กะเพราแท้ที่ผัดแห้งๆ มีแค่เนื้อสัตว์กับใบกะเพราฉุนๆ\n▪️ ปะทะ กะเพราใส่ถั่วฝักยาว หัวหอมใหญ่ หรือข้าวโพดอ่อนเพื่อเพิ่มปริมาณ\n▪️ สำหรับหนูคือขอแบบแห้งๆ พริกแห้งใบกะเพราป่าเท่านั้นค่ะ\n▪️ แล้วทุกคนล่ะคะ รับได้ไหมถ้ากะเพรามีถั่วฝักยาวปนมา\n#ผัดกะเพรา #กะเพราแท้ #ถกเถียงอาหาร"
        },
        {
            "left_label": "ชาไทยสีส้ม",
            "right_label": "ชาเขียวนม",
            "line1": "ส้มหรือเขียว",
            "line2": "แก้วไหนเยียวยาใจ?",
            "caption": "▪️ บ่ายสามแล้วร่างกายต้องการคาเฟอีนและน้ำตาลด่วนๆ ค่ะ\n▪️ ระหว่างชาไทยสีส้มเข้มข้นกลิ่นหอมเอกลักษณ์ไทยแท้\n▪️ กับชาเขียวนมรสชาตินัวๆ หอมละมุนสไตล์มัทฉะยอดฮิต\n▪️ ตัดใจเลือกยากมากจนบางทีต้องสั่งมากินทั้งสองแก้วเลยค่ะ\n▪️ ชาไหนคือที่หนึ่งในใจของทุกคนคะวันนี้ เมนต์ด่วนค่ะ\n#ชาไทย #ชาเขียว #บ่ายนี้ดื่มอะไรดี"
        }
    ]
}


HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SomtamBot/1.0; +github)"}

# ── Pexels Search Queries ────────────────────────────────────────────
THAI_FOOD_QUERIES = [
    "thai food photography",
    "thai food photography",
    "thai street food photography",
    "thai street food photography",
    "som tam papaya salad food photography",
    "pad thai noodles food photography",
    "tom yum soup food styling",
    "thai spicy food photography",
    "thai curry food photography",
    "mango sticky rice food styling",
    "thai fried rice food photography",
    "moo ping grilled pork street food",
    "pad kra pao thai basil food photography",
    "bangkok street food photography",
    "thai food close up appetizing",
]

HISTORY_FILE = "posted_photos.txt"

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception:
            return []
    return []

def save_to_history(url):
    urls = load_history()
    urls.append(url)
    urls = urls[-150:]
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            for u in urls:
                f.write(u + "\n")
    except Exception as e:
        print(f"Error saving history: {e}")

RECIPE_HISTORY_FILE = "posted_recipes.txt"

def load_recipe_history():
    if os.path.exists(RECIPE_HISTORY_FILE):
        try:
            with open(RECIPE_HISTORY_FILE, "r", encoding="utf-8") as f:
                return [line.strip() for line in f if line.strip()]
        except Exception:
            return []
    return []

def save_recipe_to_history(title):
    titles = load_recipe_history()
    titles.append(title)
    titles = titles[-100:]  # Cap at 100
    try:
        with open(RECIPE_HISTORY_FILE, "w", encoding="utf-8") as f:
            for t in titles:
                f.write(t + "\n")
    except Exception as e:
        print(f"Error saving recipe history: {e}")


IMAGE_EXTS   = (".jpg", ".jpeg", ".png", ".gif", ".webp")
# content types = หมวดหมู่การเล่าเรื่องของสายกิน/สตรีทฟู้ด + ดราม่าและข้อพิพาทอาหารไทย
CONTENT_TYPES = ["สายแซ่บสู้ชีวิต", "วิถีสตรีทฟู้ด", "รีวิวแซ่บจิกกัด", "ความหิวยามดึก", "ข้อพิพาทอาหาร"]


# ── Pexels ───────────────────────────────────────────────────────────
def get_pexels_food_image(history_urls):
    if not PEXELS_API_KEY:
        print("PEXELS_API_KEY not set")
        return None

    for _ in range(5):
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
                continue
            
            # Filter out photos that have already been posted
            new_photos = [p for p in photos if (p["src"].get("large2x") or p["src"]["large"]) not in history_urls]
            if not new_photos:
                print(f"[Pexels] all photos on page {page} for query '{query}' already posted")
                new_photos = photos  # fallback if all are already posted on this page
                
            photo   = random.choice(new_photos)
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
    
    # Translate reddit_title to Thai first before using in vision prompt!
    reddit_title_thai = translate_to_thai(reddit_title)
    title_ctx = f'ชื่อโพสต์ต้นฉบับ: "{reddit_title_thai}"\n' if reddit_title_thai else ""
    prompt = (
        f"{title_ctx}"
        "Analyze this image carefully. Read the context title (ชื่อโพสต์ต้นฉบับ) first, but prioritize what is ACTUALLY visible in the image.\n"
        "Compare the context title with the image: If the title is about 'papaya salad/ส้มตำ' but the image actually depicts another dish like curry (แกงเขียวหวาน), grilled pork, or a general food market stall (ร้านข้าวแกงถาด), you MUST specify the actual food/stall name visible in the image. Do not make assumptions or default to 'ส้มตำ' unless it is actually there.\n\n"
        "Provide 4 fields separated by a vertical bar '|':\n"
        "1. Image Type: Choose either 'dish' (if it's a close-up of a food dish), 'stall' (if it's a street food stall, market vendor, or shop front), or 'other'.\n"
        "2. Food Name: The actual Thai name of the food or the type of food stall visible in the picture (1-4 Thai words, e.g., 'ร้านข้าวแกงถาด', 'ก๋วยเตี๋ยวเรือ', 'ส้มตำ', 'แกงเขียวหวาน'). If it is not related to Thai/Asian food, output 'ไม่ตรงคอนเทน'.\n"
        "3. Local Vibe Description: A short realistic description in Thai (5-8 words) of the local eating/food vibe based strictly on visual details (e.g., 'ตักแกงถาดเรียงรายในตลาด', 'แม่ค้ากำลังตักน้ำแกงร้อนๆ').\n"
        "4. Appeal Level: Choose from these types: ['สายแซ่บสู้ชีวิต', 'วิถีสตรีทฟู้ด', 'รีวิวแซ่บจิกกัด', 'ความหิวยามดึก', 'ข้อพิพาทอาหาร'].\n\n"
        "Format: Image Type | Food Name | Local Vibe Description | Appeal Level\n"
        "Example: dish | ส้มตำ | เหงื่อซิกปากเจ่อแต่สู้ตายจิ้มข้าวเหนียวต่อ | สายแซ่บสู้ชีวิต\n"
        "Example: stall | ร้านข้าวแกงถาด | กับข้าวเรียงรายในถาดละลานตาในตลาดสด | วิถีสตรีทฟู้ด"
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
            
            if not contains_thai(food_name):
                food_name = translate_to_thai(food_name)
            if not contains_thai(vibe):
                vibe = translate_to_thai(vibe)
                
            return image_type, food_name, vibe, genre
        except Exception as e:
            print(f"[{model}] vision failed: {e}")
    return "dish", translate_to_thai(reddit_title), "น้ำลายสอตั้งแต่เห็นพริกแดง", "วิถีสตรีทฟู้ด"


# ── Gemini Caption & Hook (Combined for Consistency) ───────────────────
LOCAL_FOODIE_VIBES = {
    "สายแซ่บสู้ชีวิต":   "สั่งแบบเผ็ดน้อยแต่ได้พริกสิบเม็ด, ปากเจ่อเหงื่อซิกแต่สู้ตายไม่ยอมแพ้, จัดจ้านแซ่บสะใจกันไปเลย",
    "วิถีสตรีทฟู้ด":    "ยืนต่อคิวรอโต๊ะกลางแดดตอนเที่ยง, เก้าอี้ดนตรีหน้าร้านอาหารป้าเข็นรถ, ขอของเคียงเพิ่มด่วน",
    "รีวิวแซ่บจิกกัด":  "รีวิวรสชาตินัวสะกดใจคนข้างบ้าน, จิกกัดความปากสว่างตูดพังวันพรุ่งนี้, แซวเพื่อนสายกินคลีนที่ยอมจำนนให้ของแซ่บ",
    "ความหิวยามดึก":    "ไถฟีดเจอของกินตอนตีสองน้ำลายสอ, ความทรมานของการเห็นของกินแซ่บยามค่ำคืน, ต้มบะหมี่ประทังชีพแต่ยังนึกถึงจานเด็ดในรูป",
    "ข้อพิพาทอาหาร":   "กะเพราใส่ถั่วฝักยาวเป็นตราบาปไหม, ความนัวของน้ำปลาร้าคือนิพพาน, การบีบมะนาวลงในอาหาร",
}

REALISM_FILTER = (
    "เขียนเหมือนคนไทยพิมพ์เองใน Facebook เมาท์มอยกัน ไม่ใช่นักการตลาด\n"
    "ภาษาพูดธรรมดา ความคิดแรกในหัวคนไทย ง่ายๆ ตรงๆ ไม่ประดิษฐ์ประดอย\n"
    "ใช้บุคลิกภาพเป็นผู้หญิงในการเล่าเรื่อง มีคำลงท้ายภาษาผู้หญิงเสมอ เช่น ค่ะ, คะ และใช้สรรพนามแทนตัวเองด้วยคำว่า หนู, เรา หรือ แอดมินพี่สาว\n"
    "avoid: คำคมสอนชีวิต, punchline สวยงาม, ภาษาอวยเกินจริง\n"
    "prioritize: ความตลกขำขัน, ความอยากอาหาร, ความแซ่บนัวสะใจคนไทย\n"
    "ตัวอย่างโทนที่ถูก: 'สั่งเผ็ดน้อยแต่สีแดงแป๊ดเลยค่ะ', 'ปากเจ่อเหงื่อซิกแต่หนูยังไหวค่ะ', 'น้ำลายไหลเลยค่ะตั้งแต่คำแรก'\n"
    "ตัวอย่างโทนที่ผิด: 'รสชาติที่ไม่มีที่สิ้นสุด', 'ประสบการณ์ใหม่', ประโยคประดิษฐ์ใดๆ\n"
)


def generate_post_content(img_path, image_type, food_name, vibe, genre, content_type, reddit_title=""):
    with open(img_path, "rb") as f:
        img_data = f.read()

    reactions = LOCAL_FOODIE_VIBES.get(genre, LOCAL_FOODIE_VIBES["วิถีสตรีทฟู้ด"])
    prompt = (
        f"You are an expert Thai social media copywriter for a food page named 'พริก 10 เม็ด' (Spicy Thai Food/Stall content). Write with a friendly female persona using female particles like 'ค่ะ' / 'คะ' and pronouns like 'หนู' / 'เรา'.\n"
        f"Analyze the attached image and generate highly engaging, funny, and relatable Facebook content in THAI language about this food/stall:\n"
        f"- Food/Stall Name: {food_name}\n"
        f"- Image Type: {image_type} (either 'dish' or 'stall')\n"
        f"- Appeal Level: {genre}\n"
        f"- Eating Vibe: {vibe}\n"
        f"- Post Category: {content_type}\n"
        f"- Original Source Context: {reddit_title}\n\n"
        "Strict Chain of Thought (CoT) Caption Consistency:\n"
        "  1. Read the Original Source Context to understand what this post is historically about.\n"
        "  2. Look at the attached image carefully: Identify what food, ingredients, objects, and environment are ACTUALLY present in the picture. Do not assume or hallucinate dishes that are not there (e.g., if there is curry/rice, DO NOT write about papaya salad or mortars. If it's a general food stall, write about general market stalls).\n"
        "  3. Write the Hooks and Caption ensuring they match the ACTUAL visual elements shown in the image.\n\n"
        "Post Category descriptions:\n"
        "  * 'สายแซ่บสู้ชีวิต': Thai people eating ultra-spicy food, sweating, mouth burning, but refusing to give up.\n"
        "  * 'วิถีสตรีทฟู้ด': Fun habits of street food lovers, queuing at stalls, lunch rush, fighting for tables.\n"
        "  * 'รีวิวแซ่บจิกกัด': Sarcastic, funny, and direct review of the food, spicy cravings, or morning-after consequences.\n"
        "  * 'ความหิวยามดึก': Sarcastic torture of late-night food cravings, eating instant noodles while dreaming of the food shown in the image.\n"
        "  * 'ข้อพิพาทอาหาร': Playful debate about Thai food recipes or ingredients (e.g., whether holy basil should have long beans, boat noodle soup thickness, crispy vs soft oyster omelet) to drive comments.\n\n"
        "Requirements:\n"
        "1. Output exactly 3 sections labeled with markers:\n"
        "   ===HOOK1=== (Hook Line 1: to be written on the image. Very short, 3-6 Thai words. Must feel like a casual first thought. Write strictly about the actual dish/stall in the image. e.g. if the image shows a curry shop, Hook must be about curry or market food)\n"
        "   ===HOOK2=== (Hook Line 2: to be written on the image. Very short, 3-5 Thai words. No placeholders or irrelevant context)\n"
        "   ===CAPTION=== (Facebook Caption: a short story structured as 6-8 bullet points. Start each bullet with a ▪️ emoji. 1-2 sentences per bullet. Must strictly describe the food/stall shown in the image)\n\n"
        "2. Strict Constraints for Natural Thai Style and Spelling (AVOID TYPOS & TRANSLATION ERRORS):\n"
        "   - WRITE IN NATURAL, CASUAL THAI STREET/FACEBOOK STYLE (ภาษาพูดธรรมดา ท้องถิ่น สบายๆ ขำๆ เหมือนแชร์เรื่องฮาๆ ลงกลุ่ม).\n"
        "   - AVOID ENGLISH LITERAL TRANSLATIONS.\n"
        "   - STRICT LOGICAL CONSISTENCY between hooks and caption: Hook lines and caption MUST tell the exact same story as the image.\n"
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
            label_pattern = r'^(ข้อความในโพสต์\s*Facebook|Facebook\s*Caption|Facebook\s*caption|Caption|caption|ข้อความบนรูป|ข้อความในรูป|ข้อความ|คำบรรยาย|คำอธิบาย|บรรทัดที่\s*\d+|บรรทัด\s*\d+|ประโยคที่\s*\d+|ประโยค\s*\d+|Hook\s*text|Hook|Line\s*\d+|[L|l]ine\s*\d+|\d+)\s*[:\-\.\s]\s*'
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
            timeout=60,
        )
        result = resp.json()
        if "id" in result:
            print(f"Comment {i} added: {result['id']}")
        else:
            print(f"Comment {i} error: {result}")
        if i < len(comments):
            time.sleep(random.uniform(30, 90))


def generate_recipe_content(history_recipes):
    history_str = ", ".join(history_recipes) if history_recipes else "ไม่มี"
    prompt = (
        "You are an expert Thai social media copywriter for 'พริก 10 เม็ด' (Spicy Thai Food page). Write with a friendly female persona using female particles like 'ค่ะ' / 'คะ' and pronouns like 'หนู' / 'เรา'.\n"
        "Generate a mouth-watering, easy-to-follow Thai recipe (สูตรอาหารไทยแซ่บๆ) that local Thai readers will love (e.g. ตำป่ารสเด็ด, ยำมาม่าหมูสับ, กะเพราพริกแห้งสูตรโบราณ, น้ำตกคอหมูย่าง).\n"
        f"STRICT NEGATIVE CONSTRAINT: Do NOT generate a recipe for any of the following menus/titles: {history_str}.\n"
        "Requirements:\n"
        "1. Output exactly 5 sections labeled with markers:\n"
        "   ===TITLE=== (Recipe Title, 2-4 Thai words, e.g., 'ตำป่าทะเลเดือด')\n"
        "   ===DESC=== (Short delicious summary/description of the dish, 1-2 sentences. Keep it short!)\n"
        "   ===INGREDIENTS=== (List of ingredients, one per line. Keep each line short and clean, max 5-7 words, e.g., '• มะละกอดิบสับ 1 กำมือ')\n"
        "   ===STEPS=== (Numbered steps to cook/prepare the dish, one per line. Keep each line short and clean, max 10-15 words. Maximum 5-6 steps, e.g., '1. โขลกพริกกับกระเทียมให้พอแตก')\n"
        "   ===CAPTION=== (A funny, engaging Facebook caption introducing the recipe, structured as 6-8 bullet points starting with ▪️ and ending with 3 hashtags)\n\n"
        "Ensure all details are in THAI. Do not use English words. Keep ingredients and steps concise so they fit perfectly in a card layout.\n"
        "STRICT NEGATIVE CONSTRAINT: Absolutely NO mention of foreigners, tourists, westerners, or foreigners reacting to Thai food. Focus 100% on local Thai foodie humor, struggles, and everyday food experiences in Thailand. (ห้ามพูดถึงหรืออ้างอิงถึงชาวต่างชาติ, ฝรั่ง, นักท่องเที่ยว หรือปฏิกิริยาของคนต่างชาติต่ออาหารไทยเด็ดขาด เน้นเฉพาะวิถีชีวิตคนไทยและคนชอบกินเผ็ดในไทยเท่านั้น)"
    )
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            result = resp.text.strip()
            print(f"Recipe Content Generation [{model}]:\n{result[:300]}...\n")
            
            t_match = re.search(r'===TITLE===\s*(.*)', result, re.IGNORECASE)
            d_match = re.search(r'===DESC===\s*(.*)', result, re.IGNORECASE)
            i_match = re.search(r'===INGREDIENTS===\s*(.*?)(?===\w+===|$)', result, re.DOTALL | re.IGNORECASE)
            s_match = re.search(r'===STEPS===\s*(.*?)(?===\w+===|$)', result, re.DOTALL | re.IGNORECASE)
            cap_match = re.search(r'===CAPTION===\s*(.*)', result, re.DOTALL | re.IGNORECASE)
            
            title = t_match.group(1).split('\n')[0].strip() if t_match else ""
            desc = d_match.group(1).split('\n')[0].strip() if d_match else ""
            ingredients = i_match.group(1).strip() if i_match else ""
            steps = s_match.group(1).strip() if s_match else ""
            caption = cap_match.group(1).strip() if cap_match else ""
                
            title = title.strip('"\'“”‘’')
            desc = desc.strip('"\'“”‘’')
            
            if title and not contains_thai(title):
                title = translate_to_thai(title)
            if desc and not contains_thai(desc):
                desc = translate_to_thai(desc)
            if ingredients and not contains_thai(ingredients):
                ingredients = translate_to_thai(ingredients)
            if steps and not contains_thai(steps):
                steps = translate_to_thai(steps)
            if caption and not contains_thai(caption):
                caption = translate_to_thai(caption)
            
            if title and ingredients and steps and caption and contains_thai(title) and contains_thai(caption):
                return title, desc, ingredients, steps, caption
        except Exception as e:
            print(f"[{model}] recipe content generation failed: {e}")
            
    print("Using recipe fallback post.")
    fb = random.choice(FALLBACK_POSTS["recipe"])
    return fb["title"], fb["desc"], fb["ingredients"], fb["steps"], fb["caption"]


def generate_contrast_review_content(img_path, image_type, food_name, vibe, reddit_title=""):
    with open(img_path, "rb") as f:
        img_data = f.read()

    # Pre-translate food_name, vibe, and reddit_title before using them in the prompt!
    food_name_thai = translate_to_thai(food_name)
    vibe_thai = translate_to_thai(vibe)
    reddit_title_thai = translate_to_thai(reddit_title)

    prompt = (
        f"You are an expert Thai social media copywriter for a food page named 'พริก 10 เม็ด' (Spicy Thai Food/Stall content). Write with a friendly female persona using female particles like 'ค่ะ' / 'คะ' and pronouns like 'หนู' / 'เรา'.\n"
        f"Analyze the attached image and generate a highly engaging, SARCASTIC contrast review about this food/stall:\n"
        f"- Food/Stall Name: {food_name_thai}\n"
        f"- Image Type: {image_type} (either 'dish' or 'stall')\n"
        f"- Eating Vibe: {vibe_thai}\n"
        f"- Context: {reddit_title_thai}\n\n"
        "Strict Chain of Thought (CoT) Caption Consistency:\n"
        "  1. Read the Context to understand what this post is historically about.\n"
        "  2. Look at the attached image carefully: Identify what food, ingredients, objects, and environment are ACTUALLY present in the picture. Do not assume or hallucinate dishes that are not there (e.g., if there is curry/rice, DO NOT write about papaya salad or mortars. If it's a general food stall, write about general market stalls).\n"
        "  3. Focus on a common food-related PAIN-POINT or contrast (e.g., ordering 'slightly spicy' but getting a volcano, late-night hunger vs diet plans, eating delicious food now vs paying the price tomorrow on the toilet, long queues, expectations vs reality) related SPECIFICALLY to the food/stall shown in the image.\n"
        "  4. Write the Hooks and Caption ensuring they match the ACTUAL visual elements shown in the image.\n\n"
        "Requirements:\n"
        "1. Output exactly 3 sections labeled with markers:\n"
        "   ===HOOK1=== (Hook Line 1: Sarcastic/pain-point statement to be written on the image. Very short, 3-6 Thai words. Must feel like a casual first thought, NO emojis. Write strictly about the actual dish/stall in the image)\n"
        "   ===HOOK2=== (Hook Line 2: Sarcastic follow-up, very short, 3-5 Thai words, NO emojis. No placeholders or irrelevant context)\n"
        "   ===CAPTION=== (Facebook Caption: a funny, sarcastic story structured as 6-8 bullet points. Start each bullet with a ▪️ emoji. End with 3 relevant hashtags. Must strictly describe the food/stall shown in the image)\n\n"
        "2. Strict Constraints for Natural Thai Style and Spelling:\n"
        "   - WRITE IN NATURAL, CASUAL THAI STREET/FACEBOOK STYLE.\n"
        "   - STRICT LOGICAL CONSISTENCY between hooks and caption: Hook lines and caption MUST tell the exact same story as the image.\n"
        "   - STRICT NEGATIVE CONSTRAINT: Absolutely NO mention of foreigners, tourists, westerners, or foreigners reacting to Thai food. Focus 100% on local Thai foodie humor and everyday struggles.\n"
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
            print(f"Contrast Review Generation [{model}]:\n{result[:300]}...\n")
            
            h1_match = re.search(r'===HOOK1===\s*(.*)', result, re.IGNORECASE)
            h2_match = re.search(r'===HOOK2===\s*(.*)', result, re.IGNORECASE)
            cap_match = re.search(r'===CAPTION===\s*(.*)', result, re.DOTALL | re.IGNORECASE)
            
            line1 = h1_match.group(1).split('\n')[0].strip() if h1_match else ""
            line2 = h2_match.group(1).split('\n')[0].strip() if h2_match else ""
            caption = cap_match.group(1).strip() if cap_match else ""
            
            label_pattern = r'^(ข้อความในโพสต์\s*Facebook|Facebook\s*Caption|Facebook\s*caption|Caption|caption|ข้อความบนรูป|ข้อความในรูป|ข้อความ|คำบรรยาย|คำอธิบาย|บรรทัดที่\s*\d+|บรรทัด\s*\d+|ประโยคที่\s*\d+|ประโยค\s*\d+|Hook\s*text|Hook|Line\s*\d+|[L|l]ine\s*\d+|\d+)\s*[:\-\.\s]\s*'
            line1 = re.sub(label_pattern, '', line1, flags=re.IGNORECASE).strip()
            line2 = re.sub(label_pattern, '', line2, flags=re.IGNORECASE).strip()
            line1 = line1.strip('"\'“”‘’')
            line2 = line2.strip('"\'“”‘’')
            
            if line1 and not contains_thai(line1):
                line1 = translate_to_thai(line1)
            if line2 and not contains_thai(line2):
                line2 = translate_to_thai(line2)
            if caption and not contains_thai(caption):
                caption = translate_to_thai(caption)
                
            if line1 and caption and contains_thai(line1) and contains_thai(caption):
                return line1, line2, caption
        except Exception as e:
            print(f"[{model}] contrast review content generation failed: {e}")
            
    print("Using contrast review fallback post.")
    fb = random.choice(FALLBACK_POSTS["contrast_review"])
    return fb["line1"], fb["line2"], fb["caption"]


def generate_debate_topic_and_queries(history_debates):
    history_str = ", ".join(history_debates) if history_debates else "ไม่มี"
    prompt = (
        "You are an expert Thai social media copywriter for 'พริก 10 เม็ด' (Spicy Thai Food page). Write with a friendly female persona using female particles like 'ค่ะ' / 'คะ' and pronouns like 'หนู' / 'เรา'.\n"
        "Select a fun, engaging, and controversial Thai food debate topic (e.g. กะเพราใส่ถั่วฝักยาว vs กะเพราแท้, ส้มตำปลาร้า vs ส้มตำไทย, ชาไทยสีส้ม vs ชาเขียว, บะหมี่แห้งเส้นเล็ก vs บะหมี่แห้งเส้นบะหมี่, ก๋วยเตี๋ยวเรือน้ำตก vs ก๋วยเตี๋ยวต้มยำ).\n"
        f"STRICT NEGATIVE CONSTRAINT: Do NOT generate a debate about any of the following topics/titles: {history_str}.\n"
        "Requirements:\n"
        "1. Output exactly 7 fields labeled with markers:\n"
        "   ===LEFT_LABEL=== (Label for left option, 1-3 Thai words, e.g., 'ใส่ถั่วฝักยาว')\n"
        "   ===RIGHT_LABEL=== (Label for right option, 1-3 Thai words, e.g., 'กะเพราแท้')\n"
        "   ===LEFT_QUERY=== (English search query for Pexels to find left image, 1-3 English words, e.g., 'stir fried basil long beans' or 'thai basil chicken')\n"
        "   ===RIGHT_QUERY=== (English search query for Pexels to find right image, 1-3 English words, e.g., 'pad kra pao' or 'spicy chicken basil')\n"
        "   ===HOOK1=== (Hook Line 1: Main statement, very short, 4-6 Thai words. NO emojis)\n"
        "   ===HOOK2=== (Hook Line 2: Question or sub-hook, very short, 3-5 Thai words. NO emojis)\n"
        "   ===CAPTION=== (A funny, engaging Facebook caption initiating the debate, structured as 6-8 bullet points starting with ▪️ and ending with 3 hashtags)\n\n"
        "Ensure all labels and hooks are in THAI. English queries should be standard, generic food terms that Pexels has images for (e.g. 'papaya salad', 'pad thai', 'green curry', 'spring rolls', 'fried rice', 'thai milk tea').\n"
        "STRICT NEGATIVE CONSTRAINT: Absolutely NO mention of foreigners, tourists, westerners, or foreigners reacting to Thai food. Focus 100% on local Thai foodie humor and everyday debates."
    )
    for model in TEXT_MODELS:
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            result = resp.text.strip()
            print(f"Debate Topic & Queries Generation [{model}]:\n{result[:400]}...\n")
            
            ll_match = re.search(r'===LEFT_LABEL===\s*(.*)', result, re.IGNORECASE)
            rl_match = re.search(r'===RIGHT_LABEL===\s*(.*)', result, re.IGNORECASE)
            lq_match = re.search(r'===LEFT_QUERY===\s*(.*)', result, re.IGNORECASE)
            rq_match = re.search(r'===RIGHT_QUERY===\s*(.*)', result, re.IGNORECASE)
            h1_match = re.search(r'===HOOK1===\s*(.*)', result, re.IGNORECASE)
            h2_match = re.search(r'===HOOK2===\s*(.*)', result, re.IGNORECASE)
            cap_match = re.search(r'===CAPTION===\s*(.*)', result, re.DOTALL | re.IGNORECASE)
            
            left_label = ll_match.group(1).split('\n')[0].strip() if ll_match else ""
            right_label = rl_match.group(1).split('\n')[0].strip() if rl_match else ""
            left_query = lq_match.group(1).split('\n')[0].strip() if lq_match else ""
            right_query = rq_match.group(1).split('\n')[0].strip() if rq_match else ""
            line1 = h1_match.group(1).split('\n')[0].strip() if h1_match else ""
            line2 = h2_match.group(1).split('\n')[0].strip() if h2_match else ""
            caption = cap_match.group(1).strip() if cap_match else ""
            
            label_pattern = r'^(ข้อความในโพสต์\s*Facebook|Facebook\s*Caption|Facebook\s*caption|Caption|caption|ข้อความบนรูป|ข้อความในรูป|ข้อความ|คำบรรยาย|คำอธิบาย|บรรทัดที่\s*\d+|บรรทัด\s*\d+|ประโยคที่\s*\d+|ประโยค\s*\d+|Hook\s*text|Hook|Line\s*\d+|[L|l]ine\s*\d+|\d+)\s*[:\-\.\s]\s*'
            left_label = re.sub(label_pattern, '', left_label, flags=re.IGNORECASE).strip()
            right_label = re.sub(label_pattern, '', right_label, flags=re.IGNORECASE).strip()
            left_query = left_query.strip('"\'“”‘’')
            right_query = right_query.strip('"\'“”‘’')
            line1 = re.sub(label_pattern, '', line1, flags=re.IGNORECASE).strip()
            line2 = re.sub(label_pattern, '', line2, flags=re.IGNORECASE).strip()
            line1 = line1.strip('"\'“”‘’')
            line2 = line2.strip('"\'“”‘’')
            
            if left_label and not contains_thai(left_label):
                left_label = translate_to_thai(left_label)
            if right_label and not contains_thai(right_label):
                right_label = translate_to_thai(right_label)
            if line1 and not contains_thai(line1):
                line1 = translate_to_thai(line1)
            if line2 and not contains_thai(line2):
                line2 = translate_to_thai(line2)
            if caption and not contains_thai(caption):
                caption = translate_to_thai(caption)
                
            if left_label and right_label and line1 and caption and contains_thai(left_label) and contains_thai(line1) and contains_thai(caption):
                return left_label, right_label, left_query, right_query, line1, line2, caption
        except Exception as e:
            print(f"[{model}] debate topic & queries generation failed: {e}")
            
    print("Using debate fallback post.")
    fb = random.choice(FALLBACK_POSTS["debate"])
    mock_queries = {
        "ส้มตำปลาร้า": "thai papaya salad",
        "ส้มตำไทย": "papaya salad",
        "กะเพราแท้": "pad kra pao",
        "ใส่ถั่วฝักยาว": "stir fried basil",
        "ชาไทยสีส้ม": "thai tea",
        "ชาเขียวนม": "green tea latte"
    }
    l_q = mock_queries.get(fb["left_label"], "thai food")
    r_q = mock_queries.get(fb["right_label"], "thai food")
    return fb["left_label"], fb["right_label"], l_q, r_q, fb["line1"], fb["line2"], fb["caption"]


def search_pexels_single_image(query, history_urls, block_urls=None):
    if not PEXELS_API_KEY:
        print("PEXELS_API_KEY not set")
        return None
    if block_urls is None:
        block_urls = set()

    for page in [1, 2, 3]:
        try:
            resp = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_API_KEY},
                params={"query": query, "per_page": 10, "page": page},
                timeout=10,
            )
            resp.raise_for_status()
            photos = resp.json().get("photos", [])
            if not photos:
                continue
            
            new_photos = []
            for p in photos:
                url = p["src"].get("large2x") or p["src"]["large"]
                if url not in history_urls and url not in block_urls:
                    new_photos.append(p)
            if not new_photos:
                new_photos = [p for p in photos if (p["src"].get("large2x") or p["src"]["large"]) not in block_urls]
                if not new_photos:
                    new_photos = photos
                
            photo = random.choice(new_photos)
            img_url = photo["src"].get("large2x") or photo["src"]["large"]
            return img_url
        except Exception as e:
            print(f"Pexels search error for '{query}': {e}")
    return None


def main():
    import sys
    dry_run = "--dry-run" in sys.argv
    forced_mode = None
    for arg in sys.argv:
        if arg.startswith("--mode="):
            forced_mode = arg.split("=")[1]

    print("=== พริก 10 เม็ด Bot ===")

    if forced_mode in ["recipe", "contrast_review", "debate"]:
        mode = forced_mode
    else:
        mode = random.choices(["recipe", "contrast_review", "debate"], weights=[35, 35, 30])[0]
    print(f"Selected Mode: {mode} (Forced: {forced_mode})")

    os.makedirs("output", exist_ok=True)
    img_path = None
    caption = ""

    if mode == "recipe":
        print("Generating Recipe Content...")
        history_recipes = load_recipe_history()
        title, desc, ingredients, steps, caption = generate_recipe_content(history_recipes)
        print(f"Recipe Title: {title}")
        print(f"Description: {desc}")
        
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        img_path = tmp.name
        tmp.close()
        
        try:
            from overlay_utils import create_recipe_card
            img_path = create_recipe_card(title, desc, ingredients, steps, img_path)
            print(f"Recipe Card generated: {img_path}")
        except Exception as e:
            print(f"Recipe Card generation failed: {e}")
            if os.path.exists(img_path):
                os.unlink(img_path)
            return

    elif mode == "contrast_review":
        history_urls = load_history()
        post = None
        for attempt in range(5):
            post = get_pexels_food_image(history_urls)
            if post:
                break
            print(f"Retry {attempt + 1}/5...")

        if not post and dry_run:
            print("[Dry-Run] Pexels failed or key missing. Using mock image post.")
            post = {
                "url": "https://images.pexels.com/photos/2067423/pexels-photo-2067423.jpeg",
                "title": "ส้มตำถาดรสแซ่บเผ็ดจัดจ้านสะใจคนกิน",
                "subreddit": "thai food"
            }

        if not post:
            print("No suitable post found after 5 attempts")
            return

        img_path = download_image(post["url"])
        if not img_path:
            print("Image download failed")
            return

        reddit_title = post["title"]
        image_type, food_name, vibe, genre = analyze_image(img_path, reddit_title=reddit_title)
        if not food_name or "ไม่ใช่อาหาร" in food_name or "ไม่ตรงคอนเทน" in food_name:
            food_name = reddit_title
            image_type = "dish"
            vibe = "น้ำลายสอตั้งแต่เห็นพริกแดง"
            genre = "วิถีสตรีทฟู้ด"

        print(f"Food: {food_name} | Type: {image_type} | Vibe: {vibe}")
        line1, line2, caption = generate_contrast_review_content(img_path, image_type, food_name, vibe, reddit_title=reddit_title)
        line1 = segment_thai_text(line1, client)
        line2 = segment_thai_text(line2, client)
        print(f"Contrast Hook: {line1} | {line2}")

        try:
            from overlay_utils import add_overlay
            overlaid = add_overlay(img_path, line1, line2, ACCENT_COLOR)
            os.unlink(img_path)
            img_path = overlaid
            print(f"Contrast Review Overlay generated: {img_path}")
        except Exception as e:
            print(f"Overlay failed: {e}")

        caption += f"\n📷 via Pexels"

    elif mode == "debate":
        print("Generating Debate Content...")
        history_recipes = load_recipe_history()
        left_label, right_label, left_query, right_query, line1, line2, caption = generate_debate_topic_and_queries(history_recipes)
        left_label = segment_thai_text(left_label, client)
        right_label = segment_thai_text(right_label, client)
        line1 = segment_thai_text(line1, client)
        line2 = segment_thai_text(line2, client)
        print(f"Debate Topic: {line1} | {line2}")
        print(f"Options: {left_label} ({left_query}) vs {right_label} ({right_query})")

        history_urls = load_history()
        
        left_img_url = search_pexels_single_image(left_query, history_urls)
        if not left_img_url and dry_run:
            print("[Dry-Run] Left image search failed or key missing. Using mock image.")
            left_img_url = "https://images.pexels.com/photos/5638527/pexels-photo-5638527.jpeg"
        left_img_path = None
        if left_img_url:
            left_img_path = download_image(left_img_url)
            
        right_img_url = search_pexels_single_image(right_query, history_urls, block_urls={left_img_url})
        if not right_img_url and dry_run:
            print("[Dry-Run] Right image search failed or key missing. Using mock image.")
            right_img_url = "https://images.pexels.com/photos/2067423/pexels-photo-2067423.jpeg"
        right_img_path = None
        if right_img_url:
            right_img_path = download_image(right_img_url)

        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        img_path = tmp.name
        tmp.close()

        try:
            from overlay_utils import create_split_debate_card
            img_path = create_split_debate_card(left_img_path, right_img_path, left_label, right_label, img_path)
            print(f"Split Debate Card generated: {img_path}")
        except Exception as e:
            print(f"Split Debate Card generation failed: {e}")
            if os.path.exists(img_path):
                os.unlink(img_path)
            return
        finally:
            if left_img_path and os.path.exists(left_img_path):
                os.unlink(left_img_path)
            if right_img_path and os.path.exists(right_img_path):
                os.unlink(right_img_path)

        caption += f"\n📷 via Pexels"

    print(f"Generated Caption:\n{caption}\n")

    if dry_run:
        dry_out_path = f"output/dryrun_{mode}.jpg"
        import shutil
        shutil.copy(img_path, dry_out_path)
        print(f"[Dry-Run] Saved card image to: {dry_out_path}")
        
        print("[Dry-Run] Testing affiliate comment matching...")
        try:
            from affiliate_utils import get_all_comments
            comments = get_all_comments(caption=caption, img_path=img_path)
            print(f"[Dry-Run] Generated Affiliate Comments ({len(comments)} total):")
            for idx, c in enumerate(comments, 1):
                if isinstance(c, dict):
                    print(f"  Comment {idx}: {c['message']} (Attachment: {c.get('picture_url')})")
                else:
                    print(f"  Comment {idx}: {c}")
        except Exception as e:
            print(f"[Dry-Run] Affiliate comment test failed: {e}")
            
        if os.path.exists(img_path):
            os.unlink(img_path)
        print("[Dry-Run] Completed successfully.")
    else:
        success = post_photo(caption, img_path)
        if success:
            if mode == "contrast_review" and 'post' in locals() and post:
                save_to_history(post["url"])
            elif mode == "recipe":
                save_recipe_to_history(title)
            elif mode == "debate":
                save_recipe_to_history(f"{left_label} vs {right_label}")
                if 'left_img_url' in locals() and left_img_url:
                    save_to_history(left_img_url)
                if 'right_img_url' in locals() and right_img_url:
                    save_to_history(right_img_url)
            print("Successfully posted to Facebook!")
        else:
            print("Post to Facebook FAILED")


if __name__ == "__main__":
    main()
