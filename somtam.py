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
from google.genai.types import HttpOptions

# ── Config ───────────────────────────────────────────────────────────
PAGE_ID           = "554501167740603"
PAGE_ACCESS_TOKEN = os.environ.get("SOMTAM_PAGE_ACCESS_TOKEN", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "") or "DUMMY_KEY"
PEXELS_API_KEY    = os.environ.get("PEXELS_API_KEY", "")

API_ENABLED = True
client       = genai.Client(api_key=GEMINI_API_KEY, http_options=HttpOptions(timeout=300000))
TEXT_MODELS       = ["gemini-flash-latest", "gemini-flash-latest"]
ACCENT_COLOR = (255, 107, 53)  # ส้ม #FF6B35

def contains_thai(text):
    if not text:
        return False
    return bool(re.search(r'[\u0e00-\u0e7f]', text))

_LEADING_VOWELS  = set('เแโใไ')
_COMBINING_CHARS = set('่้๊๋์ิีึืุูัํ็')

THAI_WORDS = [
    "รายละเอียด", "โปรโมชั่น", "เครื่องมือ", "คอมพิวเตอร์", "แอปพลิเคชัน", "เก็บเงินปลายทาง",
    "โทรศัพท์", "แบตเตอรี่", "บัตรเครดิต", "พร้อมส่ง", "จัดส่ง", "ต่างประเทศ",
    "พรีออเดอร์", "ประหยัด", "ปลอดภัย", "คุ้มค่า", "สะดวกสบาย", "ธรรมชาติ",
    "คุณภาพ", "ภาพถ่าย", "พลาสติก", "ของแท้", "รับประกัน", "ลิขสิทธิ์",
    "แนะนำ", "สินค้า", "รีวิว", "สุดยอด", "ดีที่สุด", "สะดวก", "สบาย", "ง่ายดาย",
    "รวดเร็ว", "โปรโมชั่", "ส่วนลด", "คูปอง", "จัดส่ง", "ประกัน",
    "ชาร์จ", "หน้าจอ", "ลำโพง", "หูฟัง", "กล้อง", "เลนส์", "มือถือ", "ปุ่มกด",
    "สำหรับ", "เกี่ยวกับ", "อย่างไร", "เมื่อไหร่", "ที่ไหน", "เท่าไหร่",
    "ทุกคน", "ทุกวัน", "ทุกคืน", "สุดท้าย", "แรกเริ่ม", "จริงจัง",
    "สวัสดี", "ขอบคุณ", "ขอโทษ", "ยินดี", "หัวเราะ", "ร้องไห้",
    "ทำงาน", "พักผ่อน", "ออกกำลัง", "ท่องเที่ยว", "เดินทาง",
    "เก้าอี้", "โต๊ะทำงาน", "เบาะรอง", "พิงหลัง", "สายรัด", "การ์ตูน",
    "กระเป๋า", "รองเท้า", "เสื้อผ้า", "กางเกง", "นาฬิกา", "แว่นตา", "เครื่อง", "ระบบ",
    "ความสุข", "ร่างกาย", "สุขภาพ", "ออกกำลัง", "อาหาร", "ผลไม้", "น้ำดื่ม", "กาแฟ",
    "ราคา", "พิเศษ", "ทั่วไป", "ส่งฟรี", "ลดราคา", "ของแถม", "ปลายทาง",
    "ชั่วโมง", "นาที", "วินาที", "สัปดาห์", "ปีใหม่", "วันนี้", "พรุ่งนี้", "เมื่อวาน",
    "ใครก็ตาม", "สิ่งใด", "ทั้งหมด", "บางส่วน", "ประเภท", "รูปแบบ",
    "ติดตาม", "กดไลก์", "แชร์โพส", "คอมเมนต์", "คลิกลิงก์", "พิกัด", "ชี้เป้า",
    "ค่ะ", "ครับ", "ผม", "เรา", "คุณ", "ท่าน",
    "พี่", "น้อง", "พ่อ", "แม่", "เพื่อน", "บ้าน", "เมือง", "เวลา", "ดีใจ", "เสียใจ", 
    "รัก", "ชอบ", "เกลียด", "กลัว", "โกรธ", "ทำ", "กิน", "นอน", "เดิน", "วิ่ง", "นั่ง", 
    "ยืน", "พูด", "ฟัง", "ดู", "เห็น", "คิด", "รู้", "จำ", "ลืม", "เรียน", "เล่น", "ซื้อ", 
    "ขาย", "ราคา", "ถูก", "แพง", "ลด", "แถม", "ส่ง", "ด่วน", "ฟรี", "รับ", "ศูนย์",
    "แท้", "ใหม่", "เก่า", "แรก", "นี้", "นั้น", "โน้น", "นี่", "นั่น", "โน่น", "อะไร", 
    "ใคร", "กี่", "บ้าง", "ทุก", "บาง", "จริง", "จัง", "แท้", "เทียม", "ปลอม", "สาย", 
    "เคส", "ฟิล์ม", "ภาพ", "รูป", "เสียง", "เพลง", "หนัง", "เกม", "แอป", "เว็บ", "เน็ต", 
    "โค้ด", "โอน", "หวย", "ออก", "เงิน", "เก็บ", "แสน", "แรก", "งาน", "การ", "ช่วย", 
    "บอก", "ให้", "คน", "ทอง", "ร้อย", "พัน", "หมื่น", "ล้าน", "มาก", "น้อย", "ดี", 
    "เลว", "ชั่ว", "สูง", "ต่ำ", "ดำ", "ขาว", "แดง", "เขียว", "เหลือง", "ฟ้า", "ส้ม", 
    "ชมพู", "ม่วง", "เทา", "สวย", "หล่อ", "และ", "หรือ", "แต่", "ที่", "ซึ่ง", "อัน", 
    "ของ", "เพื่อ", "ใน", "จาก", "โดย", "ตาม", "กับ", "มี", "เป็น", "จะ", "ต้อง", 
    "อยาก", "นุ่ม", "แข็ง", "ใหญ่", "เล็ก", "ยาว", "สั้น", "กว้าง", "แคบ", "หนา", 
    "บาง", "ร้อน", "เย็น", "อุ่น", "หนาว", "ง่าย", "ยาก", "เร็ว", "ช้า", "ได้", 
    "เลย", "ด้วย", "จาก", "ถึง", "จน", "กว่า", "ก็", "ยัง", "อีก", "แล้ว", "นะ", 
    "สิ", "ละ", "หน่อย", "นิด", "ชิ้น", "กล่อง", "อัน", "ตัว", "ใบ", "คู่", "ชุด", 
    "แผ่น", "ม้วน"
]

def local_segment_thai(text):
    if not text:
        return ""
    word_set = set(THAI_WORDS)
    max_len = max(len(w) for w in THAI_WORDS)
    
    result = []
    i = 0
    n = len(text)
    
    while i < n:
        if not contains_thai(text[i]):
            result.append(text[i])
            i += 1
            continue
            
        matched = False
        for l in range(min(max_len, n - i), 0, -1):
            substr = text[i:i+l]
            if substr in word_set:
                result.append(substr)
                i += l
                matched = True
                break
        
        if not matched:
            start = i
            while i < n and contains_thai(text[i]):
                word_matched_here = False
                if i > start:
                    for l in range(min(max_len, n - i), 0, -1):
                        if text[i:i+l] in word_set:
                            word_matched_here = True
                            break
                if word_matched_here:
                    break
                i += 1
            result.append(text[start:i])
            
    output = []
    for idx, part in enumerate(result):
        if idx > 0:
            prev_char = result[idx-1][-1]
            curr_char = part[0]
            if (contains_thai(prev_char) and contains_thai(curr_char) and 
                prev_char != '\u200b' and curr_char != '\u200b' and
                curr_char not in _COMBINING_CHARS and
                prev_char not in _LEADING_VOWELS):
                output.append('\u200b')
        output.append(part)
        
    return "".join(output)

def segment_thai_text(text, client=client):
    global API_ENABLED
    if not text or not contains_thai(text):
        return text
    if not API_ENABLED:
        return local_segment_thai(text)
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
    for model_idx, model in enumerate(TEXT_MODELS):
        if model_idx > 0:
            import time; time.sleep(2)
        try:
            resp = client.models.generate_content(model=model, contents=prompt)
            segmented = resp.text.strip().replace('\\u200b', '\u200b')
            clean_orig = text.replace('\u200b', '').replace('\\u200b', '')
            clean_seg = segmented.replace('\u200b', '').replace('\\u200b', '')
            if len(clean_orig) == len(clean_seg):
                return segmented
        except Exception as e:
            print(f"[{model}] segment_thai_text failed: {e}")
            
    print("[Warning] segment_thai_text failed on all models. Disabling API calls for this run.")
    API_ENABLED = False
    return local_segment_thai(text)

def translate_to_thai(text):
    if not text:
        return ""
    if contains_thai(text):
        return text
    prompt = f"Translate the following food-related English text to natural Thai food vocabulary. Only output the translation, no explanation:\n\n{text}"
    for model_idx, model in enumerate(TEXT_MODELS):
        if model_idx > 0:
            import time; time.sleep(2)
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
            "title": "ต้มยำกุ้ง",
            "desc": "น้ำข้น vs น้ำใส",
            "ingredients": "ทีมไหนคือรสชาติไทยแท้?",
            "steps": "",
            "caption": "หนูขอเปิดศาลอาหารไทยหน่อยค่ะ ต้มยำกุ้งนี่ควรเป็นน้ำใสจี๊ดๆ หอมสมุนไพร หรือเป็นน้ำข้นมันนัวใส่นมถึงจะฟินกว่ากันคะ\n\nบางคนบอกน้ำใสคือของแท้ รสจัด สด คลีนกว่า แต่อีกทีมบอกน้ำข้นนี่แหละซดแล้วสะใจ กินกับข้าวคือที่สุด\n\nพี่ๆ อยู่ทีมไหนคะ น้ำใสหรือน้ำข้น แล้วมีบ้านไหนใส่นมข้นจืดจนโดนแม่ดุบ้างไหมคะ",
            "query": "tom yum soup"
        },
        {
            "title": "ข้าวมันไก่",
            "desc": "เอาหนัง vs ไม่เอาหนัง",
            "ingredients": "ทีมไหนฟินกว่ากันคะ?",
            "steps": "",
            "caption": "มาเปิดประเด็นศาลอาหารไทยรอบเย็นค่ะ เวลาสั่งข้าวมันไก่นี่พี่ๆ ชอบแบบเอาหนังมันๆ ชุ่มฉ่ำ หรือลอกหนังออกกินแต่เนื้อล้วนคลีนๆ กันคะ\n\nฝั่งคนชอบหนังบอกว่าข้าวมันไก่ที่ไม่มีหนังมันขาดวิญญาณความอร่อยไปเลย แต่อีกทีมก็บอกว่าเนื้อล้วนสิคะได้รสไก่เต็มๆ แถมไม่เลี่ยนด้วย\n\nพี่ๆ อยู่ทีมเอาหนังหรือทีมไม่เอาหนังคะ แล้วเวลาสั่งนี่โดนเพื่อนทักบ้างไหมคะ",
            "query": "chicken rice"
        },
        {
            "title": "ผัดกะเพรา",
            "desc": "ใส่ถั่วฝักยาว vs ไม่ใส่ถั่วฝักยาว",
            "ingredients": "แบบไหนคือแท้โบราณ?",
            "steps": "",
            "caption": "หนูขอเคลียร์ประเด็นนี้ให้จบเลยค่ะ ผัดกะเพราที่พี่ๆ ชอบกินต้องผัดแห้งๆ พริกกระเทียมใบกะเพราล้วน หรือรับได้กับการใส่ถั่วฝักยาว ข้าวโพดอ่อน หอมใหญ่คะ\n\nฝั่งคนชอบพริกล้วนบอกว่าใส่ผักอื่นไม่ใช่กะเพราแท้หรอกค่ะ เสียรสชาติ แต่อีกทีมบอกว่ามีถั่วฝักยาวช่วยเพิ่มสัมผัสเคี้ยวเพลินแถมได้ปริมาณเยอะขึ้นนะ\n\nพี่ๆ คิดว่ายังไงคะ ผัดกะเพราใส่ถั่วฝักยาวนี่ผ่านหรือควรร้องเรียนดีคะ",
            "query": "pad kra pao"
        }
    ],
    "contrast_review": [
        {
            "line1": "สั่งเผ็ดน้อย",
            "line2": "แต่แดงทั้งครก",
            "url": "https://images.pexels.com/photos/10527603/pexels-photo-10527603.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
            "caption": "สั่งแม่ค้าว่าเผ็ดน้อยทีไร ได้สีแดงแป๊ดมาตลอดเลยค่ะ ในใจแม่ค้าคงคิดว่าพริก 10 เม็ดคือเลเวลอนุบาล ปากเจ่อเหงื่อไหลยาลดกรดต้องเข้าแล้วค่ะงานนี้ แต่ในฐานะนักสู้เรื่องกิน เราไม่มียอมแพ้แน่นอนค่ะ ใครเคยสั่งเผ็ดน้อยแล้วได้เผ็ดร้อนระเบิดรูทวารแบบนี้บ้างคะ\n#สั่งเผ็ดน้อย #แซ่บสู้ชีวิต #พริก10เม็ด"
        },
        {
            "line1": "กินตอนนี้แซ่บปาก",
            "line2": "พรุ่งนี้ลำบากตูด",
            "url": "https://images.pexels.com/photos/10527603/pexels-photo-10527603.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
            "caption": "วงการส้มตำเข้าแล้วออกยาก แต่เข้าห้องน้ำออกยากกว่าค่ะ ตอนกินคือนัวสะใจ พริกแห้งพริกสดจัดเต็มไม่มีกั๊ก พรุ่งนี้เช้าเตรียมตัวรับแรงกระแทกแบบสู้ชีวิตเลยค่ะ แต่ถามว่าจะเข็ดไหม ตอบเลยว่าพรุ่งนี้เย็นเจอกันใหม่ค่ะ\n#อร่อยแซ่บ #เตือนภัยสายกิน #พริก10เม็ด"
        },
        {
            "line1": "คิวยาวเป็นกิโล",
            "line2": "แต่ยอมยืนรอ",
            "url": "https://images.pexels.com/photos/34699470/pexels-photo-34699470.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
            "caption": "วิถีคนหิวที่แท้จริงคือการยืนรอคิวหน้าร้านส้มตำค่ะ แดดจะร้อนลมจะแรงแค่ไหนก็ทำอะไรความอยากกินไม่ได้ พอได้กินคำแรกปลาร้านัวๆ เท่านั้นแหละ หายเหนื่อยทันทีค่ะ ใครยอมยืนต่อคิวเพื่อของอร่อยบ้างคะรายงานตัวด่วน\n#รีวิวสตรีทฟู้ด #ส้มตำคิวยาว #พริก10เม็ด"
        }
    ],
    "trivia": [
        {
            "line1": "กำเนิดส้มตำไทย",
            "line2": "มะละกอมาจากไหน?",
            "url": "https://images.pexels.com/photos/10527603/pexels-photo-10527603.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
            "caption": "รู้ไหมคะว่าส้มตำที่เรากินกันแซ่บๆ ทุกวันนี้ มะละกอไม่ได้มีต้นกำเนิดในไทยนะ จริงๆ มะละกอเป็นพืชพื้นเมืองของอเมริกากลางค่ะ นำเข้ามาโดยพ่อค้าชาวโปรตุเกสตั้งแต่สมัยอยุธยาตอนปลาย แล้วคนไทยเริ่มเอามาโขลกใส่น้ำปลา พริก และมะนาวจนกลายเป็นส้มตำแซ่บๆ ใครเป็นมะละกอเลิฟเวอร์ยกมือขึ้นด่วนๆ เลยนะคะสาวๆ\n#ประวัติส้มตำ #มะละกอแซ่บ #พริก10เม็ด"
        },
        {
            "line1": "ผัดกะเพราโบราณ",
            "line2": "ใส่ซีอิ๊วดำไหม?",
            "url": "https://images.pexels.com/photos/28996226/pexels-photo-28996226.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940",
            "caption": "กะเพราแท้สูตรโบราณดั้งเดิมจริงๆ เขาใส่ซีอิ๊วดำกันไหมคะสาวๆ จากสูตรดั้งเดิมสมัยก่อนจะไม่ใส่ซีอิ๊วดำเลยค่ะ จะเน้นผัดกับพริกแห้งและกระเทียมให้หอมฉุนแบบแห้งๆ ไหนใครชอบกะเพราแบบใส่ซีอิ๊วดำหรือแบบโบราณมากกว่ากัน คอมเมนต์บอกหนูหน่อยนะคะ\n#กะเพราโบราณ #อาหารไทย #พริก10เม็ด"
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

def extract_pexels_id(url):
    if not url:
        return None
    # Matches /photos/12345/ or /photo/12345/
    match = re.search(r'/photos?/(\d+)/', url)
    if match:
        return match.group(1)
    # Matches pexels-photo-12345.jpeg
    match = re.search(r'pexels-photo-(\d+)', url)
    if match:
        return match.group(1)
    return url.split('?')[0]

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

    history_ids = {extract_pexels_id(url) for url in history_urls if extract_pexels_id(url)}
    last_photos = []

    for attempt in range(5):
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
            
            last_photos = photos
            
            # Filter out photos by Pexels ID robustly
            new_photos = []
            for p in photos:
                url = p["src"].get("large2x") or p["src"]["large"]
                pid = extract_pexels_id(url)
                if pid not in history_ids:
                    new_photos.append(p)
            
            if new_photos:
                photo   = random.choice(new_photos)
                img_url = photo["src"].get("large2x") or photo["src"]["large"]
                alt     = photo.get("alt", query)
                print(f"[Pexels] query='{query}' | alt='{alt[:60]}'")
                return {"url": img_url, "title": alt, "subreddit": query}
            else:
                print(f"[Pexels] all photos on page {page} for query '{query}' already posted. Retrying...")
        except Exception as e:
            print(f"Pexels error: {e}")

    # Last resort fallback: choose from the last query's results
    if last_photos:
        print("[Pexels] Absolute last resort fallback to already posted photo")
        photo = random.choice(last_photos)
        img_url = photo["src"].get("large2x") or photo["src"]["large"]
        alt = photo.get("alt", "thai food")
        return {"url": img_url, "title": alt, "subreddit": "thai food"}
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
    
    # Pass alt text as hint only — do NOT translate, keep English to reduce bias
    title_ctx = (
        f'[Pexels alt text — auto-generated, may NOT match actual dish]: "{reddit_title}"\n'
        if reddit_title else ""
    )
    prompt = (
        f"{title_ctx}"
        "CRITICAL: The Pexels alt text above is auto-generated SEO text and frequently describes the wrong dish or uses generic ingredient names. "
        "Your food identification MUST come from visual analysis of the image ONLY. IGNORE the alt text if it conflicts with what you actually see.\n\n"
        "Look at the actual dish: identify the COOKING METHOD (ยำ, ต้ม, ผัด, แกง, ทอด, ลาบ, etc.) AND the main ingredient together. "
        "Do NOT name just an ingredient — name the complete dish.\n\n"
        "Provide 4 fields separated by a vertical bar '|':\n"
        "1. Image Type: Choose either 'dish' (close-up food dish), 'stall' (street food stall/market vendor), or 'other'.\n"
        "2. Food Name: Full Thai dish name including cooking method (2-5 Thai words). "
        "Examples: 'ยำมะพร้าวอ่อน' (NOT just 'มะพร้าว'), 'ต้มยำกุ้ง' (NOT just 'กุ้ง'), 'ผัดกะเพราหมู', 'ส้มตำปูปลาร้า', 'ร้านข้าวแกงถาด'. "
        "If not Thai/Asian food output 'ไม่ตรงคอนเทน'.\n"
        "3. Local Vibe: Short Thai description 5-8 words based strictly on visual details.\n"
        "4. Appeal Level: One of ['สายแซ่บสู้ชีวิต', 'วิถีสตรีทฟู้ด', 'รีวิวแซ่บจิกกัด', 'ความหิวยามดึก', 'ข้อพิพาทอาหาร'].\n\n"
        "Format: Image Type | Food Name | Local Vibe | Appeal Level\n"
        "Example: dish | ยำมะพร้าวอ่อนทะเล | น้ำยำเปรี้ยวแซ่บหอมมะนาวสดๆ | สายแซ่บสู้ชีวิต\n"
        "Example: stall | ร้านข้าวแกงถาด | กับข้าวเรียงรายในถาดละลานตาในตลาดสด | วิถีสตรีทฟู้ด"
    )
    for model_idx, model in enumerate(TEXT_MODELS):
        if model_idx > 0:
            import time; time.sleep(2)
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
        "   ===CAPTION=== (Facebook Caption: a short, natural story written as a single paragraph of 2-4 sentences. Absolutely NO bullet points, lists, or symbols like ▪️. Must strictly describe the food/stall shown in the image, showing high relatable foodie humor, struggles, or late-night cravings depending on the category. Ask a relatable question at the end to drive engagement)\n\n"
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
    for model_idx, model in enumerate(TEXT_MODELS):
        if model_idx > 0:
            import time; time.sleep(2)
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


def validate_debate_content(topic, options, question, caption):
    # Check for forbidden words
    for word in ["วัตถุดิบ", "ขั้นตอนการทำ", "ขั้นตอน"]:
        if word in topic or word in options or word in question or word in caption:
            print(f"Validation failed: Contains forbidden word '{word}'")
            return False
            
    # Check for ordered list numbers (e.g. "1.", "2.", "3.")
    if re.search(r'\b\d+[\.\)\s\u200b]', topic + " " + options + " " + question + " " + caption):
        print("Validation failed: Contains ordered list numbers")
        return False
        
    # Check for bullet points or lists
    for char in ["•", "*", "-", "▪️", "▫️"]:
        if char in topic or char in options or char in question or char in caption:
            print(f"Validation failed: Contains bullet point/list symbol '{char}'")
            return False
            
    # Check for broken/unformatted lines (e.g., "=")
    if "=" in topic or "=" in options or "=" in question or "=" in caption:
        print("Validation failed: Contains broken line symbol '='")
        return False
        
    # Check for image text character limit (topic + options + question <= 60 chars)
    total_img_text = len(topic) + len(options) + len(question)
    if total_img_text > 60:
        print(f"Validation failed: Image text too long ({total_img_text} chars > 60)")
        return False
        
    # Check for hashtags in caption
    if "#" in caption:
        print("Validation failed: Caption contains hashtags")
        return False

    # Check for female polite particles (ค่ะ/คะ)
    if "ค่ะ" not in caption and "คะ" not in caption:
        print("Validation failed: Caption lacks female polite particles (ค่ะ/คะ)")
        return False

    return True


def generate_recipe_content(history_recipes):
    history_str = ", ".join(history_recipes) if history_recipes else "ไม่มี"
    prompt = (
        "You are an expert Thai social media copywriter for 'พริก 10 เม็ด' (Spicy Thai Food page). Write with a friendly female persona using female particles like 'ค่ะ' / 'คะ' and pronouns like 'หนู' / 'เรา'.\n"
        "Your task is to create a food debate/controversy post ('ศาลอาหารไทย') focusing on a single, highly relatable food debate or choice-forcing topic in Thai cuisine (e.g., ต้มยำกุ้งน้ำข้น vs น้ำใส, ข้าวมันไก่เอาหนัง vs ไม่เอาหนัง, ผัดกะเพราใส่ถั่วฝักยาว vs ไม่ใส่ถั่วฝักยาว, ผัดไทใส่เต้าหู้ vs ไม่ใส่, ผัดซีอิ๊วเส้นใหญ่ vs เส้นหมี่, แกงส้มผักรวม vs แกงเหลืองใต้, กินข้าวไข่ดาวไข่แดงเยิ้ม vs สุกสนิท, บะหมี่กึ่งสำเร็จรูปเส้นอืด vs เส้นเหนียวหนึบ).\n"
        f"STRICT NEGATIVE CONSTRAINT: Do NOT choose or generate a topic for any of the following menus/titles: {history_str}.\n\n"
        "**STRICT RULES FOR POST CONTENT**:\n"
        "1. **NO recipe instructions**: Do NOT list ingredients, measurements, or cooking steps. Do NOT write a recipe.\n"
        "2. **NO bullet points or numbers**: Absolutely do NOT use list symbols (•, *, -, ▪️, ▫️) or ordered list numbers (1., 2., 3.).\n"
        "3. **Short image text**: The text to be overlaid on the image must be extremely short and readable in 1 second. The total characters across TOPIC, OPTIONS, and QUESTION must be under 50 characters.\n"
        "4. **No broken lines**: Do NOT output lines with '=' or empty placeholders.\n"
        "5. **No hashtags**: The caption must NOT contain any hashtags (#) anywhere.\n"
        "6. **No newsy/bot buzzwords**: Do NOT use words like 'ดราม่า', 'ช็อก', 'ไวรัล', 'ปัญหาสังคม', 'แชร์สูตร'.\n"
        "7. **Female conversational caption**: The caption must be structured into 2-4 short paragraphs, written in a friendly, conversational female tone using 'หนู' (or 'เรา') and 'ค่ะ/คะ'. Frame the debate by explaining why people choose each side, making it highly relatable ('เรื่องนี้เกิดกับเราหรือที่บ้านได้'). End with a sharp, direct choice-forcing question like 'พี่ๆ ทีมไหนคะ?' or 'บ้านไหนทำแบบนี้บ้างคะ?'.\n\n"
        "Output exactly 5 sections labeled with markers:\n"
        "===TOPIC=== (The food item name, 2-4 Thai words, e.g. 'ต้มยำกุ้ง', 'ข้าวมันไก่')\n"
        "===OPTIONS=== (The two sides/choices separated by 'vs', e.g. 'น้ำข้น vs น้ำใส', 'เอาหนัง vs ไม่เอาหนัง')\n"
        "===QUESTION=== (A short question for the image, 2-5 Thai words, e.g. 'ทีมไหนคือรสชาติไทยแท้?', 'เลือกแบบไหนคะ?')\n"
        "===CAPTION=== (The Facebook caption matching the Rules above)\n"
        "===PEXELS_QUERY=== (English search query to find a high-quality, appetizing photo of this food item on Pexels, e.g., 'tom yum soup', 'hainanese chicken rice')\n"
    )
    for attempt in range(10):
        model = TEXT_MODELS[attempt % len(TEXT_MODELS)]
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    temperature=0.7,
                )
            )
            result = resp.text.strip()
            
            t_match = re.search(r'===TOPIC===\s*(.*)', result, re.IGNORECASE)
            o_match = re.search(r'===OPTIONS===\s*(.*?)(?===\w+===|$)', result, re.DOTALL | re.IGNORECASE)
            q_match = re.search(r'===QUESTION===\s*(.*?)(?===\w+===|$)', result, re.DOTALL | re.IGNORECASE)
            cap_match = re.search(r'===CAPTION===\s*(.*?)(?===\w+===|$)', result, re.DOTALL | re.IGNORECASE)
            pexels_match = re.search(r'===PEXELS_QUERY===\s*(.*)', result, re.IGNORECASE)
            
            topic = t_match.group(1).split('\n')[0].strip() if t_match else ""
            options = o_match.group(1).split('\n')[0].strip() if o_match else ""
            question = q_match.group(1).split('\n')[0].strip() if q_match else ""
            caption = cap_match.group(1).strip() if cap_match else ""
            pexels_query = pexels_match.group(1).split('\n')[0].strip() if pexels_match else ""
            
            topic = topic.strip('"\'“”‘’')
            options = options.strip('"\'“”‘’')
            question = question.strip('"\'“”‘’')
            caption = caption.strip('"\'“”‘’')
            pexels_query = pexels_query.strip('"\'“”‘’')
            
            if topic and not contains_thai(topic):
                topic = translate_to_thai(topic)
            if options and not contains_thai(options):
                options = translate_to_thai(options)
            if question and not contains_thai(question):
                question = translate_to_thai(question)
            if caption and not contains_thai(caption):
                caption = translate_to_thai(caption)
                
            if topic and options and question and caption and contains_thai(topic) and contains_thai(caption):
                if validate_debate_content(topic, options, question, caption):
                    print(f"Food debate generation succeeded on attempt {attempt+1} (model={model})")
                    if not pexels_query:
                        pexels_query = "thai food"
                    return topic, options, question, "", caption, pexels_query
                else:
                    print(f"Attempt {attempt+1} failed validation.")
        except Exception as e:
            print(f"Attempt {attempt+1} [{model}] failed: {e}")
            
    print("Using debate fallback post.")
    fb = random.choice(FALLBACK_POSTS["recipe"])
    return fb["title"], fb["desc"], fb["ingredients"], fb["steps"], fb["caption"], fb.get("query", "thai food")


def generate_contrast_review_content(img_path, image_type, food_name, vibe, reddit_title=""):
    with open(img_path, "rb") as f:
        img_data = f.read()

    # Pre-translate food_name, vibe, and reddit_title before using them in the prompt!
    food_name_thai = translate_to_thai(food_name)
    vibe_thai = translate_to_thai(vibe)
    reddit_title_thai = translate_to_thai(reddit_title)

    prompt = (
        f"You are an expert Thai social media copywriter for a food page named 'พริก 10 เม็ด' (Spicy Thai Food/Stall content). Write with a friendly female persona using female particles like 'ค่ะ' / 'คะ' and pronouns like 'หนู' / 'เรา'.\n"
        f"Analyze the attached image and generate a highly engaging food controversy or debate post about this food/stall:\n"
        f"- Food/Stall Name: {food_name_thai}\n"
        f"- Image Type: {image_type} (either 'dish' or 'stall')\n"
        f"- Eating Vibe: {vibe_thai}\n"
        f"- Context: {reddit_title_thai}\n\n"
        "Strict Chain of Thought (CoT) Caption Consistency:\n"
        "  1. Read the Context to understand what this post is historically about.\n"
        "  2. Look at the attached image carefully: Identify what food, ingredients, objects, and environment are ACTUALLY present in the picture. Do not assume or hallucinate dishes that are not there (e.g., if there is curry/rice, DO NOT write about papaya salad or mortars. If it's a general food stall, write about general market stalls).\n"
        "  3. Focus on a common Thai food debate or controversy related to the food/stall shown in the image (e.g., กะเพราใส่ถั่วฝักยาวเป็นตราบาปไหม, ต้มยำต้องน้ำใสหรือน้ำข้นถึงจะที่สุด, ส้มตำตำไทยควรหวานนำหรือเปรี้ยวนำ, ผัดไทยใส่หัวหอมซอยดีไหม) to provoke discussions.\n"
        "  4. Write the Hooks and Caption ensuring they match the ACTUAL visual elements shown in the image.\n\n"
        "Requirements:\n"
        "1. Output exactly 3 sections labeled with markers:\n"
        "   ===HOOK1=== (Hook Line 1: Debate-framing statement to be written on the image. Very short, 3-6 Thai words. Must feel like a casual first thought, NO emojis. Write strictly about the actual dish/stall in the image. e.g. 'ทีมไหนรายงานตัวคะ', 'ต้องไม่ใส่ถั่วฝักยาว!', 'น้ำใสหรือน้ำข้นดี')\n"
        "   ===HOOK2=== (Hook Line 2: Sarcastic debate continuation, very short, 3-5 Thai words, NO emojis. No placeholders or irrelevant context)\n"
        "   ===CAPTION=== (Facebook Caption: a funny, debate-sparking story written as a single paragraph of 2-4 sentences. Absolutely NO bullet points, lists, or symbols like ▪️ or -. Must strictly describe the food/stall shown in the image, showing high foodie humor. You MUST end the caption with a direct team-selection question in the polite female persona, e.g. 'กะเพราใส่ถั่วฝักยาวนี่พี่ๆ ทีมไหนกันบ้างคะ? กะเพราแท้หรือได้หมด?' or 'ต้มยำกุ้งนี่พี่ๆ ทีมน้ำใสหรือน้ำข้นคะ? คอมเมนต์บอกหนูหน่อยน้า' and end with 3 relevant hashtags)\n\n"
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

    for model_idx, model in enumerate(TEXT_MODELS):
        if model_idx > 0:
            import time; time.sleep(2)
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
                return line1, line2, caption, None
        except Exception as e:
            print(f"[{model}] contrast review content generation failed: {e}")
            
    print("Using contrast review fallback post.")
    fb = random.choice(FALLBACK_POSTS["contrast_review"])
    return fb["line1"], fb["line2"], fb["caption"], fb.get("url")


def generate_trivia_content(img_path, query, history_trivias):
    with open(img_path, "rb") as f:
        img_data = f.read()
        
    history_str = ", ".join(history_trivias) if history_trivias else "ไม่มี"
    prompt = (
        "You are an expert Thai social media copywriter for 'พริก 10 เม็ด' (Spicy Thai Food page). Write with a friendly female persona using female particles like 'ค่ะ' / 'คะ' and pronouns like 'หนู' / 'เรา'.\n"
        "Analyze the attached image and generate a highly engaging, funny, and fascinating Thai food trivia fact (สาระสายกิน) that highlights a food myth, origin, or ingredient controversy related to the food shown in the image (e.g. origins of chili in Thai food, historical debate on putting sugar/peanuts, or recipe myths).\n"
        f"STRICT NEGATIVE CONSTRAINT: Do NOT generate trivia for any of the following topics/titles: {history_str}.\n"
        "Requirements:\n"
        "1. Output exactly 3 sections labeled with markers:\n"
        "   ===HOOK1=== (Hook Line 1: Debate/fact-framing statement to be written on the image. Very short, 3-6 Thai words. NO emojis. Write strictly about the actual food/dish in the image)\n"
        "   ===HOOK2=== (Hook Line 2: Hook continuation or question, very short, 3-5 Thai words, NO emojis)\n"
        "   ===CAPTION=== (Facebook Caption: a funny, fascinating food trivia story written as a single paragraph of 2-4 sentences. Absolutely NO bullet points, lists, or symbols like ▪️ or -. Must strictly describe the food/stall shown in the image, showing high foodie humor. You MUST end the caption with a direct debate/opinion question, e.g., 'กะเพราโบราณจริงๆ เขาไม่ใส่ซีอิ๊วดำกันนะคะ พี่ๆ ฝั่งไหนกันบ้างคะ?' or 'พี่ๆ คิดว่ายังไงกันบ้างคะ? เมนต์มาบอกหน่อยนะ' and end with 3 relevant hashtags)\n\n"
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
    for model_idx, model in enumerate(TEXT_MODELS):
        if model_idx > 0:
            import time; time.sleep(2)
        try:
            resp = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(data=img_data, mime_type="image/jpeg"),
                    types.Part.from_text(text=prompt),
                ],
            )
            result = resp.text.strip()
            print(f"Trivia Content Generation [{model}]:\n{result[:300]}...\n")
            
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
                return line1, line2, caption, None
        except Exception as e:
            print(f"[{model}] trivia content generation failed: {e}")
            
    print("Using trivia fallback post.")
    fb = random.choice(FALLBACK_POSTS["trivia"])
    return fb["line1"], fb["line2"], fb["caption"], fb.get("url")


def search_pexels_single_image(query, history_urls, block_urls=None):
    if not PEXELS_API_KEY:
        print("PEXELS_API_KEY not set")
        return None
    if block_urls is None:
        block_urls = set()

    history_ids = {extract_pexels_id(url) for url in history_urls if extract_pexels_id(url)}
    block_ids = {extract_pexels_id(url) for url in block_urls if extract_pexels_id(url)}
    last_photos = []

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
            
            last_photos = photos
            
            new_photos = []
            for p in photos:
                url = p["src"].get("large2x") or p["src"]["large"]
                pid = extract_pexels_id(url)
                if pid not in history_ids and pid not in block_ids:
                    new_photos.append(p)
            
            if new_photos:
                photo = random.choice(new_photos)
                img_url = photo["src"].get("large2x") or photo["src"]["large"]
                return img_url
            else:
                print(f"[Pexels] all photos on page {page} for query '{query}' already posted or blocked. Retrying next page...")
        except Exception as e:
            print(f"Pexels search error for '{query}': {e}")

    # Last resort fallback
    if last_photos:
        non_blocked = [p for p in last_photos if extract_pexels_id(p["src"].get("large2x") or p["src"]["large"]) not in block_ids]
        if non_blocked:
            photo = random.choice(non_blocked)
        else:
            photo = random.choice(last_photos)
        img_url = photo["src"].get("large2x") or photo["src"]["large"]
        return img_url
    return None


def main():
    import sys
    dry_run = "--dry-run" in sys.argv
    forced_mode = None
    for arg in sys.argv:
        if arg.startswith("--mode="):
            forced_mode = arg.split("=")[1]

    print("=== พริก 10 เม็ด Bot ===")

    if forced_mode in ["recipe", "contrast_review", "trivia"]:
        mode = forced_mode
    else:
        mode = random.choices(["recipe", "contrast_review", "trivia"], weights=[50, 50, 0])[0]
    print(f"Selected Mode: {mode} (Forced: {forced_mode})")

    os.makedirs("output", exist_ok=True)
    img_path = None
    caption = ""

    if mode == "recipe":
        print("Generating Food Debate Content...")
        history_recipes = load_recipe_history()
        topic, options, question, _, caption, pexels_query = generate_recipe_content(history_recipes)
        print(f"Debate Topic: {topic}")
        print(f"Options: {options}")
        print(f"Question: {question}")
        print(f"Pexels Query: {pexels_query}")
        
        history_urls = load_history()
        bg_url = search_pexels_single_image(pexels_query, history_urls)
        if not bg_url and dry_run:
            print("[Dry-Run] Food Debate Pexels search failed or key missing. Using mock image.")
            bg_url = "https://images.pexels.com/photos/2067423/pexels-photo-2067423.jpeg"
            
        bg_img_path = None
        if bg_url:
            print(f"Downloading background image: {bg_url}")
            bg_img_path = download_image(bg_url)
            
        import tempfile
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        img_path = tmp.name
        tmp.close()
        
        # Segment Thai text for card rendering to ensure correct wrapping behavior
        topic_seg = segment_thai_text(topic, client)
        options_seg = segment_thai_text(options, client)
        question_seg = segment_thai_text(question, client)
        
        try:
            from overlay_utils import create_recipe_card
            img_path = create_recipe_card(topic_seg, options_seg, question_seg, img_path, bg_img_path=bg_img_path)
            print(f"Food Debate Card generated: {img_path}")
        except Exception as e:
            print(f"Food Debate Card generation failed: {e}")
            if os.path.exists(img_path):
                os.unlink(img_path)
            return
        finally:
            if bg_img_path and os.path.exists(bg_img_path):
                try:
                    os.unlink(bg_img_path)
                    print(f"Deleted temporary background image: {bg_img_path}")
                except Exception as ex:
                    print(f"Error deleting temporary background image: {ex}")

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
        line1, line2, caption, fallback_url = generate_contrast_review_content(img_path, image_type, food_name, vibe, reddit_title=reddit_title)
        if fallback_url:
            print(f"API failed, using fallback post. Redownloading matching image: {fallback_url}")
            if os.path.exists(img_path):
                os.unlink(img_path)
            new_img_path = download_image(fallback_url)
            if new_img_path:
                img_path = new_img_path
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

        caption += f"\n📷 ภาพจาก Pexels"

    elif mode == "trivia":
        print("Generating Trivia Content...")
        history_recipes = load_recipe_history()
        query = random.choice(THAI_FOOD_QUERIES)
        history_urls = load_history()
        img_url = search_pexels_single_image(query, history_urls)
        
        if not img_url and dry_run:
            print("[Dry-Run] Pexels search failed or key missing. Using mock image.")
            img_url = "https://images.pexels.com/photos/2067423/pexels-photo-2067423.jpeg"
            
        if not img_url:
            print("No suitable image found for trivia")
            return
            
        img_path = download_image(img_url)
        if not img_path:
            print("Image download failed")
            return
            
        line1, line2, caption, fallback_url = generate_trivia_content(img_path, query, history_recipes)
        if fallback_url:
            print(f"API failed, using fallback post. Redownloading matching image: {fallback_url}")
            if os.path.exists(img_path):
                os.unlink(img_path)
            new_img_path = download_image(fallback_url)
            if new_img_path:
                img_path = new_img_path
        line1 = segment_thai_text(line1, client)
        line2 = segment_thai_text(line2, client)
        print(f"Trivia Hook: {line1} | {line2}")
        
        try:
            from overlay_utils import add_overlay
            overlaid = add_overlay(img_path, line1, line2, ACCENT_COLOR)
            os.unlink(img_path)
            img_path = overlaid
            print(f"Trivia Overlay generated: {img_path}")
        except Exception as e:
            print(f"Overlay failed: {e}")
            
        caption += f"\n📷 ภาพจาก Pexels"

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
                save_recipe_to_history(topic)
                if 'bg_url' in locals() and bg_url:
                    save_to_history(bg_url)
            elif mode == "trivia":
                save_recipe_to_history(line1)
                if 'img_url' in locals() and img_url:
                    save_to_history(img_url)
            print("Successfully posted to Facebook!")
        else:
            print("Post to Facebook FAILED")


if __name__ == "__main__":
    main()
