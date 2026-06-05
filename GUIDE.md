# คู่มือระบบ somtam-facebook-page (เพจ พริก 10 เม็ด)

## ภาพรวม

ระบบโพสต์เนื้อหาของเพจ **"พริก 10 เม็ด"** อัตโนมัติ ทำงานผ่าน GitHub Actions ทุกวัน โดยแบ่งออกเป็น 3 ส่วนหลัก:

```
GitHub Actions (cron)
├── somtam.py       → โพสต์เนื้อหาแซ่บๆ (สูตรอาหาร, รีวิวจิกกัด, สาระอาหาร) + รูปและข้อความพาดหัว
├── review.py       → โพสต์รีวิวสินค้าสไตล์เพจแซ่บ + แนะนำสินค้า
└── lotto_poster.py → โพสต์ผลสลากกินแบ่งรัฐบาลไทยอัตโนมัติ (เฉพาะวันที่ 1 และ 16)
         ↓
   affiliate_utils.py → ใส่คอมเมนต์ลิงก์สินค้า Affiliate อัตโนมัติ (ดึงจาก affiliate_products.xlsx)
```

---

## ฟังก์ชันเด่นและความสำเร็จล่าสุด (Success Features)

### 1. ระบบสูตรอาหารอ้างอิงข้อมูลจริงจากแหล่งน่าเชื่อถือ (Grounded Recipe Search)
* **การปรับปรุง**: ป้องกันปัญหาการสร้างสูตรอาหารแบบมโนขึ้นมาเอง (Hallucination) โดยการเชื่อมโยงระบบค้นหา **Google Search Grounding** ร่วมกับ Gemini API
* **การทำงาน**: บอทจะค้นหาข้อมูลสูตรอาหารคลาสสิก/สตรีทฟู้ดของไทยจากเว็บอาหารชั้นนำที่น่าเชื่อถือ เช่น **Wongnai, Krua.co, Kapook** จากนั้นจะดึงวัตถุดิบและขั้นตอนการทำที่ถูกต้องมาเขียนใหม่เป็นสไตล์แซ่บๆ ของเพจ โดยลงท้ายด้วยน้ำเสียงผู้หญิงอันอบอุ่นเป็นกันเอง (ค่ะ/คะ/หนู/เรา) พร้อมระบุแหล่งที่มาในแคปชั่นอย่างแนบเนียน

### 2. ระบบป้องกันรูปภาพไม่ตรงกับโพสต์สำรอง (Fallback Image Redirection)
* **การปรับปรุง**: ป้องกันปัญหาการโพสต์รูปภาพกับข้อความไม่ตรงกัน (เช่น รูปภาพเป็นต้มยำกุ้งแต่เขียนแคปชั่นกะเพรา) เมื่อระบบ API ของ Gemini ขัดข้องชั่วคราวและต้องสลับไปใช้โพสต์สำรอง (Fallback Posts)
* **การทำงาน**: ผูกรูปภาพที่ถูกต้องตรงกับข้อความโพสต์สำรองแต่ละตัวไว้ในชุดข้อมูล หาก API ขัดข้องและต้องใช้งานแผนสำรอง บอทจะทำการ**ลบรูปสุ่มที่ดาวน์โหลดมาตอนแรกทิ้งทันที** แล้วทำการดาวน์โหลดรูปภาพที่ถูกต้องของเมนูสำรองนั้นมาใช้งานทดแทน ทำให้ภาพและข้อความของเพจมีความตรงกัน 100% เสมอ

### 3. ระบบตรวจผลสลากกินแบ่งรัฐบาลไทยอัตโนมัติ (Thai Lottery Auto Poster)
* **การปรับปรุง**: เพิ่มบอทรายงานผลหวยอัตโนมัติ ทุกวันที่ 1 และ 16 ของเดือน ดึงข้อมูล Real-time ทันทีหลังจากประกาศผล
* **การทำงาน**: สคริปต์ `lotto_poster.py` จะถูกเรียกทำงานและสแกงผลรางวัลจาก Sanook Lotto และโพสต์ลง Facebook เพจพร้อมแคปชั่นแซ่บๆ ในโทนเพจทันที ช่วยให้เพจมีทราฟฟิกสูงในช่วงวันหวยออก

---

## โครงสร้างของสคริปต์หลัก

### 1. `somtam.py` — บอทหลักของเพจ (รันทุกวัน เวลา 09:00 น. และ 19:00 น. ตามเวลาไทย)
บอทจะสุ่มเลือกโหมดการทำงานออกเป็น 3 ประเภทดังนี้:
* **recipe (35%)**: ดึงสูตรอาหารผ่านการค้นหา Google Search Grounding สลักข้อความทับลงการ์ดวัตถุดิบและวิธีทำที่สร้างขึ้นใหม่ด้วยโปรแกรม
* **contrast_review (35%)**: ดาวน์โหลดรูปภาพอาหารสตรีทฟู้ดไทยจาก Pexels วิเคราะห์ภาพ แล้วสร้างข้อความรีวิวเชิงเปรียบเทียบตลกๆ หรือความแซ่บในชีวิตประจำวัน (เช่น สั่งเผ็ดน้อยแต่แดงทั้งครก) สลักข้อความสไตล์พาดหัวข่าวลงบนภาพ
* **trivia (30%)**: ดาวน์โหลดรูปภาพอาหาร วิเคราะห์ภาพ แล้วสร้างเกร็ดความรู้ประวัติศาสตร์หรือสาระน่ารู้เกี่ยวกับอาหารจานนั้นๆ พร้อมสลักข้อความพาดหัวน่าสนใจลงบนภาพ

### 2. `lotto_poster.py` — บอทรายงานผลหวยรัฐบาลไทย (รันเฉพาะวันที่ 1 และ 16 ของเดือน)
* ดึงข้อมูลผลสลากกินแบ่งรัฐบาลไทยจากหน้าผลหวยแบบ Real-time
* ตรวจสอบความถูกต้องของเลขรางวัลที่ 1, เลขหน้า 3 ตัว, เลขท้าย 3 ตัว และเลขท้าย 2 ตัวอย่างรัดกุมก่อนโพสต์
* โพสต์รายงานผลบน Facebook พร้อมข้อความยินดีต้อนรับเศรษฐีใหม่ในโทนเพจ

### 3. `review.py` — บอทโพสต์รีวิวสินค้าและป้ายยา (รันทุกวันจันทร์ พุธ ศุกร์ เวลา 08:00 น. ตามเวลาไทย)
* โพสต์ป้ายยาสินค้าแนวอาหาร วัตถุดิบ และอุปกรณ์ครัว โดยดึงข้อมูลจาก `review_products.xlsx`
* นำมาสร้างเป็นภาพรีวิวพร้อมสลักข้อความดึงดูด และแนบลิงก์สำหรับกดสั่งซื้อเพื่อสร้างรายได้จากค่าคอมมิชชัน

---

## วิธีการตั้งค่าและการรันแบบ Manual

หากต้องการรันเพื่อทดสอบในระบบ Local หรือเปลี่ยนบอททำงานแบบบังคับโหมด:

```bash
# รันโพสต์หลักแบบสุ่มโหมด (Recipe / Contrast Review / Trivia)
python somtam.py --dry-run

# บังคับรันเฉพาะสูตรอาหาร (Recipe) แบบแห้ง (ไม่โพสต์จริง) เพื่อดูตัวอย่างภาพการ์ดและการค้นหาข้อมูลสูตร
python somtam.py --dry-run --mode=recipe

# บังคับรันเฉพาะรีวิวจิกกัดเปรียบเทียบ (Contrast Review)
python somtam.py --dry-run --mode=contrast_review

# บังคับรันเฉพาะสาระอาหาร (Trivia)
python somtam.py --dry-run --mode=trivia

# รันตรวจผลสลากกินแบ่งรัฐบาลไทย
python lotto_poster.py
```

### การตั้งค่า Environment Variables
ตรวจสอบว่าได้กำหนดค่าคีย์ในระบบหรือไฟล์ `config.py` (หากรัน Local) หรือ GitHub Secrets (หากรันบนระบบคลาวด์):
* `GEMINI_API_KEY`: คีย์สำหรับใช้งานโมเดลภาษาและการวิเคราะห์รูปภาพ
* `SOMTAM_PAGE_ACCESS_TOKEN`: คีย์การเข้าถึง (Access Token) ของเพจ Facebook พริก 10 เม็ด
* `PEXELS_API_KEY`: คีย์สำหรับดาวน์โหลดรูปภาพอาหารไทยคุณภาพสูง

---

## พรอมต์สร้างภาพรีวิวสินค้าจาก AI (AI Product Review Prompt Template)

พรอมต์ที่ได้รับอนุมัติสำหรับการเจนรูปภาพรีวิวสินค้า:

```plaintext
Act as a professional e-commerce visual content creator. Create a high-quality promotional image for [PRODUCT NAME] inspired by the combined composition and text aesthetic of images_1.png through images_5.png. 

Key Visual Elements:
- Background: Minimalist, clean desk setup or styled nook with soft, bright light, and a shallow depth of field (blurred background elements).
- Subject: A prominent, central placement of [PRODUCT NAME] based on the photo you provided.
- Graphics: Incorporate playful, stylized *Thai* text overlays using both free-floating text and text within outlined boxes (similar to the examples in the reference images). 
- Decorative Elements: Include floating sparkles, small ingredient-relevant icons (like tiny fruits, flowers, clouds), and subtle sizing indicators, but NO prices.

Text Content Strategy (Generate ONE unique Thai perspective per render):
1. "Problem Solver/Result-Focused": Focus on a key problem the product solves (e.g., dry skin, messy desk). Use clean, professional Thai fonts.
2. "Lifestyle/Emotional Benefit": Focus on how the product makes you feel (e.g., "Elevate Your Space", "Feel Luxurious"). Use playful Thai fonts.
3. "Functional/Tech Feature Callout": Pick ONE unique benefit (e.g., specific sizing, a technology). Use bold Thai fonts.

[PASTE DETAILED PRODUCT DESCRIPTION HERE]
```

