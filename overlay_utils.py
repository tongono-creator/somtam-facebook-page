# overlay_utils.py â€” PIL text overlay for Facebook bot images

import os
import re
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", "Sarabun-ExtraBold.ttf")

_LEADING_VOWELS  = set('เแโใไ')
_COMBINING_CHARS = set('่้๊๋์ิีึืุูัํ็')


def _wrap_text(draw, text, font, max_width):
    """แบ่ง text เป็นหลาย line ให้พอดีกับ max_width (รองรับภาษาไทยที่ไม่มี space)"""
    if draw.textbbox((0, 0), text, font=font)[2] <= max_width:
        return [text]
    if '\u200b' in text or '\\u200b' in text:
        text = text.replace('\\u200b', '\u200b')
        tokens = text.split('\u200b')
        lines, current = [], ""
        for token in tokens:
            test = current + token
            if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                    current = token
                else:
                    current = token
        if current:
            lines.append(current)
        return lines

    if " " in text.strip():
        lines = _wrap_words(draw, text, font, max_width)
        if getattr(font, "size", 99) <= 75:
            new_lines = []
            for l in lines:
                if draw.textbbox((0, 0), l, font=font)[2] > max_width:
                    new_lines.extend(_wrap_text(draw, l, font, max_width))
                else:
                    new_lines.append(l)
            lines = new_lines
        return lines
    if getattr(font, "size", 99) > 75:
        return [text]

    lines = []
    current = ""
    for char in text:
        test = current + char
        fits = draw.textbbox((0, 0), test, font=font)[2] <= max_width
        if fits or char in _COMBINING_CHARS:
            current = test
        else:
            if current:
                if current[-1] in _LEADING_VOWELS:
                    orphan  = current[-1]
                    current = current[:-1]
                    if current:
                        lines.append(current)
                    current = orphan + char
                else:
                    lines.append(current)
                    current = char
            else:
                current = char
    if current:
        lines.append(current)
    return lines or [text]


def _wrap_words(draw, text, font, max_width):
    words = [w for w in text.split(" ") if w]
    if not words:
        return [text]
    lines, current = [], ""
    for word in words:
        test = word if not current else current + " " + word
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines


def _fit_wrapped(draw, text, max_width, max_total_h, start=88, min_size=24):
    """à¸«à¸² font size + wrapped lines à¸—à¸µà¹ˆà¸žà¸­à¸”à¸µà¸à¸±à¸š max_total_h"""
    size = start
    while size >= min_size:
        font  = ImageFont.truetype(FONT_PATH, size)
        lines = _wrap_text(draw, text, font, max_width)
        lines = _balance_wrap(draw, lines, font, max_width)  # à¸›à¹‰à¸­à¸‡à¸à¸±à¸™ orphan
        line_h = draw.textbbox((0, 0), "à¸A", font=font)[3]
        gap    = max(6, size // 8)
        total  = line_h * len(lines) + gap * (len(lines) - 1)
        width_ok = all(draw.textbbox((0, 0), l, font=font)[2] <= max_width for l in lines)
        if total <= max_total_h and width_ok:
            return font, size, lines, line_h, gap
        size -= 2
    font   = ImageFont.truetype(FONT_PATH, min_size)
    lines  = _wrap_text(draw, text, font, max_width)
    lines  = _balance_wrap(draw, lines, font, max_width)
    line_h = draw.textbbox((0, 0), "à¸A", font=font)[3]
    gap    = max(6, min_size // 8)
    return font, min_size, lines, line_h, gap


def _balance_wrap(draw, lines, font, max_width, min_ratio=0.42):
    """à¸–à¹‰à¸² line à¸ªà¸¸à¸”à¸—à¹‰à¸²à¸¢à¸ªà¸±à¹‰à¸™à¹€à¸à¸´à¸™ (orphan) â€” merge 2 à¸šà¸£à¸£à¸—à¸±à¸”à¸ªà¸¸à¸”à¸—à¹‰à¸²à¸¢à¹à¸¥à¹‰à¸§ re-wrap à¹ƒà¸«à¹‰à¸ªà¸¡à¸”à¸¸à¸¥"""
    if len(lines) <= 1:
        return lines
    last_text = lines[-1].strip()
    last_w    = draw.textbbox((0, 0), last_text, font=font)[2]
    prev_w    = draw.textbbox((0, 0), lines[-2], font=font)[2]
    # trigger à¸–à¹‰à¸²: pixel ratio à¸•à¹ˆà¸³ à¸«à¸£à¸·à¸­ char à¸™à¹‰à¸­à¸¢à¸¡à¸²à¸  (à¹€à¸¥à¸‚à¹€à¸”à¸µà¹ˆà¸¢à¸§ %, 0, à¸šà¸²à¸— à¸¯à¸¥à¸¯)
    is_orphan = (last_w < prev_w * min_ratio) or (len(last_text) <= 4)
    if not is_orphan:
        return lines  # à¸ªà¸¡à¸”à¸¸à¸¥à¹ à¸¥à¹‰à¸§
    # merge 2 à¸šà¸£à¸£à¸—à¸±à¸”à¸ªà¸¸à¸”à¸—à¹‰à¸²à¸¢ â†’ re-wrap à¸”à¹‰à¸§à¸¢ target_w à¸—à¸µà¹ˆà¹ à¸„à¸šà¸¥à¸‡
    merged   = lines[-2] + " " + lines[-1]
    total_w  = draw.textbbox((0, 0), merged, font=font)[2]
    target_w = min(max_width, int(total_w * 0.55))  # à¸—à¸³à¹ƒà¸«à¹‰à¹ à¸•à¸ à¹€à¸›à¹‡à¸™ ~2 à¸šà¸£à¸£à¸—à¸±à¸”à¸—à¸µà¹ˆà¹€à¸—à¹ˆà¸²à¹† à¸ à¸±à¸™
    rebalanced = _wrap_text(draw, merged, font, target_w)
    # à¸•à¸£à¸§à¸ˆà¸§à¹ˆà¸²à¸—à¸¸à¸  line à¹„à¸¡à¹ˆà¹€à¸ à¸´à¸™ max_width (à¹„à¸¡à¹ˆ overflow)
    if all(draw.textbbox((0, 0), l, font=font)[2] <= max_width for l in rebalanced):
        return lines[:-2] + rebalanced
    return lines  # rebalance à¹„à¸¡à¹ˆà¹„à¸”à¹‰ â€” à¸„à¸·à¸™à¸„à¹ˆà¸²à¹€à¸”à¸´à¸¡


def _draw_lines(draw, lines, font, line_h, gap, y_start, W, fill, shadow=(0, 0, 0)):
    """วาด wrapped lines กึ่งกลาง พร้อม 8-direction outline (อ่านได้ทุกพื้นหลัง)"""
    y = y_start
    for line in lines:
        clean_line = line.replace('\u200b', '').replace('\\u200b', '')
        bw = draw.textbbox((0, 0), clean_line, font=font)[2]
        x  = (W - bw) // 2
        # 8-direction outline â€” à¸—à¸³à¹ƒà¸«à¹‰à¸­à¹ˆà¸²à¸™à¹„à¸”à¹‰à¹à¸¡à¹‰à¸žà¸·à¹‰à¸™à¸«à¸¥à¸±à¸‡à¸ªà¸µà¹ƒà¸à¸¥à¹‰à¹€à¸„à¸µà¸¢à¸‡à¸•à¸±à¸§à¸­à¸±à¸à¸©à¸£
        for dx, dy in [(-3,-3),(-3,0),(-3,3),(0,-3),(0,3),(3,-3),(3,0),(3,3)]:
            draw.text((x + dx, y + dy), line, font=font, fill=shadow)
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h + gap
    return y  # y à¸«à¸¥à¸±à¸‡à¸šà¸£à¸£à¸—à¸±à¸”à¸ªà¸¸à¸”à¸—à¹‰à¸²à¸¢


def _remove_black_bars(img, threshold=20):
    """Remove solid black pillarbox/letterbox borders from image"""
    gray = img.convert("L")
    mask = gray.point(lambda p: 255 if p > threshold else 0)
    bbox = mask.getbbox()
    if bbox and (bbox[0] > 5 or bbox[1] > 5 or
                 img.width - bbox[2] > 5 or img.height - bbox[3] > 5):
        return img.crop(bbox)
    return img


def _apply_bottom_gradient(img, start_y, end_y, max_alpha=230):
    w, h = img.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(start_y, end_y):
        t = (y - start_y) / (end_y - start_y)
        alpha = int(max_alpha * t)
        draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

def add_overlay(img_path, line1, line2, accent_color, out_path=None):
    """
    Overlays text directly on the image with a smooth black gradient at the bottom.
    No solid black bar is appended, maximizing image visual space (Matichon Style).
    """
    W, H = 1080, 1080
    
    if img_path and os.path.exists(img_path):
        img = Image.open(img_path).convert("RGB")
        img = _remove_black_bars(img)
        w, h = img.size
        # Crop to square
        side = min(w, h)
        img = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
        img = img.resize((W, H), Image.LANCZOS)
    else:
        # Fallback to solid dark background
        img = Image.new("RGB", (W, H), (15, 15, 20))

    # Apply bottom gradient overlay (from y=650 to y=1080)
    start_y = 650
    img = _apply_bottom_gradient(img, start_y, H)

    draw = ImageDraw.Draw(img)
    PAD_X = 60
    PAD_Y = 40
    max_w = W - PAD_X * 2  # 960px
    text_zone_h = H - start_y - PAD_Y * 2  # 350px
    BLOCK_GAP = 12

    # Start size fitting proportionally (line2 is ~70% of line1 size)
    # 110px starting size allows extremely large headlines!
    size1 = 110
    size2 = 76 if line2 else 0

    while size1 >= 40:
        font1 = ImageFont.truetype(FONT_PATH, size1)
        font2 = ImageFont.truetype(FONT_PATH, size2) if line2 else None

        # Wrap lines for line1
        lines1 = _wrap_text(draw, line1, font1, max_w)
        lines1 = _balance_wrap(draw, lines1, font1, max_w)
        lh1 = draw.textbbox((0, 0), "ก A", font=font1)[3]
        gap1 = max(6, size1 // 8)
        total_h1 = lh1 * len(lines1) + gap1 * (len(lines1) - 1)

        # Wrap lines for line2
        if line2:
            lines2 = _wrap_text(draw, line2, font2, max_w)
            lines2 = _balance_wrap(draw, lines2, font2, max_w)
            lh2 = draw.textbbox((0, 0), "ก A", font=font2)[3]
            gap2 = max(6, size2 // 8)
            total_h2 = lh2 * len(lines2) + gap2 * (len(lines2) - 1)
            total_h = total_h1 + BLOCK_GAP + total_h2
        else:
            total_h = total_h1
            total_h2 = 0

        # Check if text fits inside boundaries
        width_ok = all(draw.textbbox((0, 0), l, font=font1)[2] <= max_w for l in lines1)
        if line2:
            width_ok = width_ok and all(draw.textbbox((0, 0), l, font=font2)[2] <= max_w for l in lines2)

        if total_h <= text_zone_h and width_ok:
            break

        # Decrement size proportionally
        size1 -= 4
        if line2:
            size2 = max(24, int(size1 * 0.7))

    y_start = start_y + (H - start_y - total_h) // 2

    # Draw line1 — accent color
    _draw_lines(draw, lines1, font1, lh1, gap1, y_start, W, fill=accent_color)

    # Draw line2 — white (pixel-exact gap: BLOCK_GAP px between bottom of line1 and top of line2)
    if line2:
        n1 = len(lines1)
        b1 = draw.textbbox((0, 0), lines1[-1], font=font1)
        pixel_bottom1 = y_start + lh1 * (n1 - 1) + gap1 * (n1 - 1) + b1[3]
        b2 = draw.textbbox((0, 0), lines2[0], font=font2)
        y2 = pixel_bottom1 + BLOCK_GAP - b2[1]
        _draw_lines(draw, lines2, font2, lh2, gap2, y2, W, fill=(255, 255, 255))

    if not out_path:
        base     = img_path.rsplit(".", 1)[0] if img_path else "overlay"
        out_path = base + "_overlay.jpg"

    img.save(out_path, "JPEG", quality=92)
    return out_path


def clean_image_text(text):
    # Keep only ASCII, Latin-1, Thai characters, and common punctuation. Strip emojis to prevent tofu boxes.
    allowed_chars = []
    for c in text:
        o = ord(c)
        if (0 <= o <= 127) or (0x0E00 <= o <= 0x0E7F) or (o in [0x2013, 0x2014, 0x2026]):
            allowed_chars.append(c)
    return "".join(allowed_chars).strip()


def create_diagonal_gradient(width, height, color1, color2):
    size = 128
    img = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(img)
    for i in range(size * 2):
        t = i / (size * 2)
        r = int(color1[0] + (color2[0] - color1[0]) * t)
        g = int(color1[1] + (color2[1] - color1[1]) * t)
        b = int(color1[2] + (color2[2] - color1[2]) * t)
        draw.line([(x, i - x) for x in range(i + 1) if x < size and (i - x) < size], fill=(r, g, b))
    return img.resize((width, height), Image.Resampling.BILINEAR)


def draw_capsule(draw, x_center, y_center, text, font, fill_color, text_color):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    pad_x = 24
    pad_y = 12
    
    x1 = x_center - tw // 2 - pad_x
    y1 = y_center - th // 2 - pad_y
    x2 = x_center + tw // 2 + pad_x
    y2 = y_center + th // 2 + pad_y
    
    draw.rounded_rectangle([x1, y1, x2, y2], radius=(y2 - y1) // 2, fill=fill_color)
    tx = x_center - tw // 2 - bbox[0]
    ty = y_center - th // 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill=text_color)


def create_acid_debate_card(line1, line2, out_path):
    """
    Generates a premium text status card with an Acid Lime & Yellow gradient background,
    dotted grid, L-brackets, branding capsule, and clean non-overlapping text.
    """
    W, H = 1080, 1080
    color_lime = (174, 243, 89)
    color_yellow = (255, 215, 0)
    
    # 1. Background Gradient
    img = create_diagonal_gradient(W, H, color_lime, color_yellow)
    
    # Create transparent overlay layer for grid and decorations
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ol = ImageDraw.Draw(overlay)
    
    # 2. Dotted Grid (6% opacity)
    grid_color = (40, 40, 40, 15)
    for gx in range(120, 960, 40):
        for gy in range(120, 960, 40):
            draw_ol.ellipse([gx-2, gy-2, gx+2, gy+2], fill=grid_color)
            
    # 3. Outer Border & L-brackets
    dark_gray = (40, 40, 40, 255)
    border_inset = 60
    # Inner border line
    draw_ol.rectangle([border_inset, border_inset, W - border_inset, H - border_inset], outline=(40, 40, 40, 80), width=1)
    
    # L-bracket Corner decorations
    bracket_len = 60
    bracket_thick = 6
    x_min, y_min = border_inset, border_inset
    x_max, y_max = W - border_inset, H - border_inset
    
    # Corner drawing
    draw_ol.line([x_min, y_min, x_min + bracket_len, y_min], fill=dark_gray, width=bracket_thick)
    draw_ol.line([x_min, y_min, x_min, y_min + bracket_len], fill=dark_gray, width=bracket_thick)
    draw_ol.line([x_max, y_min, x_max - bracket_len, y_min], fill=dark_gray, width=bracket_thick)
    draw_ol.line([x_max, y_min, x_max, y_min + bracket_len], fill=dark_gray, width=bracket_thick)
    draw_ol.line([x_min, y_max, x_min + bracket_len, y_max], fill=dark_gray, width=bracket_thick)
    draw_ol.line([x_min, y_max, x_min, y_max - bracket_len], fill=dark_gray, width=bracket_thick)
    draw_ol.line([x_max, y_max, x_max - bracket_len, y_max], fill=dark_gray, width=bracket_thick)
    draw_ol.line([x_max, y_max, x_max, y_max - bracket_len], fill=dark_gray, width=bracket_thick)
    
    # Merge overlay
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    # 4. Top Branding Capsule
    capsule_font = ImageFont.truetype(FONT_PATH, 28)
    capsule_text = clean_image_text("พริก 10 เม็ด")
    draw_capsule(
        draw=draw,
        x_center=W // 2,
        y_center=110,
        text=capsule_text,
        font=capsule_font,
        fill_color=(40, 40, 40),
        text_color=(255, 255, 255)
    )
    
    # 5. Main Text wrapping and rendering
    full_text = f"{line1}\n{line2}" if line2 else line1
    cleaned_text = clean_image_text(full_text)
    
    sz = 76 if len(cleaned_text) < 60 else (66 if len(cleaned_text) < 100 else 56)
    main_font = ImageFont.truetype(FONT_PATH, sz)
    
    wrapped_lines = []
    for line in cleaned_text.split("\n"):
        wrapped_lines.extend(_wrap_text(draw, line, main_font, W - 200))
        
    line_h = int(main_font.size * 1.35)
    line_gap = 15
    total_text_h = len(wrapped_lines) * line_h + (len(wrapped_lines) - 1) * line_gap
    
    y = (H - total_text_h) // 2 + 30
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=main_font)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        # Drop shadow
        draw.text((tx + 2, y + 2), line, font=main_font, fill=(0, 0, 0, 40))
        # Main text
        draw.text((tx, y), line, font=main_font, fill=(40, 40, 40))
        y += line_h + line_gap
        
    img.save(out_path, "JPEG", quality=92)
    return out_path


def _crop_to_size(img, target_w, target_h):
    w, h = img.size
    scale = max(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)
    img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    right = left + target_w
    bottom = top + target_h
    return img_resized.crop((left, top, right, bottom))


def _draw_lines_centered(draw, lines, font, line_h, gap, y_start, x_center, fill, shadow=(0, 0, 0)):
    y = y_start
    for line in lines:
        bw = draw.textbbox((0, 0), line, font=font)[2]
        x  = x_center - bw // 2
        for dx, dy in [(-3,-3),(-3,0),(-3,3),(0,-3),(0,3),(3,-3),(3,0),(3,3)]:
            draw.text((x + dx, y + dy), line, font=font, fill=shadow)
        draw.text((x, y), line, font=font, fill=fill)
        y += line_h + gap
    return y


def create_split_debate_card(left_img_path, right_img_path, left_label, right_label, out_path):
    """
    Crops two images to 540x1080, stitches them side-by-side,
    draws a divider line, a circular central 'VS' badge, and labels at the bottom.
    """
    W, H = 1080, 1080
    left_w = 540
    right_w = 540

    if left_img_path and os.path.exists(left_img_path):
        left_img = Image.open(left_img_path).convert("RGB")
        left_img = _remove_black_bars(left_img)
        left_cropped = _crop_to_size(left_img, left_w, H)
    else:
        left_cropped = Image.new("RGB", (left_w, H), (40, 30, 30))

    if right_img_path and os.path.exists(right_img_path):
        right_img = Image.open(right_img_path).convert("RGB")
        right_img = _remove_black_bars(right_img)
        right_cropped = _crop_to_size(right_img, right_w, H)
    else:
        right_cropped = Image.new("RGB", (right_w, H), (30, 30, 40))

    img = Image.new("RGB", (W, H))
    img.paste(left_cropped, (0, 0))
    img.paste(right_cropped, (left_w, 0))

    start_y = 650
    img = _apply_bottom_gradient(img, start_y, H, max_alpha=230)

    draw = ImageDraw.Draw(img)

    divider_color = (255, 255, 255)
    divider_width = 6
    draw.line([(left_w, 0), (left_w, H)], fill=divider_color, width=divider_width)

    vs_r = 60
    vs_cx, vs_cy = W // 2, H // 2
    draw.ellipse([vs_cx - vs_r - 2, vs_cy - vs_r - 2, vs_cx + vs_r + 2, vs_cy + vs_r + 2], fill=(40, 40, 40))
    draw.ellipse([vs_cx - vs_r, vs_cy - vs_r, vs_cx + vs_r, vs_cy + vs_r], fill=(255, 107, 53))
    draw.ellipse([vs_cx - vs_r + 4, vs_cy - vs_r + 4, vs_cx + vs_r - 4, vs_cy + vs_r - 4], outline=(255, 255, 255), width=2)
    
    vs_font = ImageFont.truetype(FONT_PATH, 38)
    vs_text = "ปะทะ"
    vs_bbox = draw.textbbox((0, 0), vs_text, font=vs_font)
    vs_tw = vs_bbox[2] - vs_bbox[0]
    vs_th = vs_bbox[3] - vs_bbox[1]
    vs_tx = vs_cx - vs_tw // 2 - vs_bbox[0]
    vs_ty = vs_cy - vs_th // 2 - vs_bbox[1]
    draw.text((vs_tx, vs_ty), vs_text, font=vs_font, fill=(255, 255, 255))

    left_label_clean = clean_image_text(left_label)
    right_label_clean = clean_image_text(right_label)

    label_max_w = 460
    
    def fit_label_text(text, max_w, max_h):
        size = 54
        while size >= 24:
            font = ImageFont.truetype(FONT_PATH, size)
            lines = _wrap_text(draw, text, font, max_w)
            lines = _balance_wrap(draw, lines, font, max_w)
            line_h = draw.textbbox((0, 0), "ก A", font=font)[3]
            gap = max(4, size // 8)
            total_h = line_h * len(lines) + gap * (len(lines) - 1)
            if total_h <= max_h and all(draw.textbbox((0, 0), l, font=font)[2] <= max_w for l in lines):
                return font, lines, line_h, gap, total_h
            size -= 2
        font = ImageFont.truetype(FONT_PATH, 24)
        lines = _wrap_text(draw, text, font, max_w)
        line_h = draw.textbbox((0, 0), "ก A", font=font)[3]
        gap = 4
        total_h = line_h * len(lines) + gap * (len(lines) - 1)
        return font, lines, line_h, gap, total_h

    l_font, l_lines, l_lh, l_gap, l_total_h = fit_label_text(left_label_clean, label_max_w, 200)
    r_font, r_lines, r_lh, r_gap, r_total_h = fit_label_text(right_label_clean, label_max_w, 200)

    y_start_l = 650 + (430 - l_total_h) // 2
    y_start_r = 650 + (430 - r_total_h) // 2

    _draw_lines_centered(draw, l_lines, l_font, l_lh, l_gap, y_start_l, 270, fill=(255, 255, 255))
    _draw_lines_centered(draw, r_lines, r_font, r_lh, r_gap, y_start_r, 810, fill=(255, 255, 255))

    img.save(out_path, "JPEG", quality=92)
    return out_path


def create_recipe_card(title, desc, ingredients, steps, out_path):
    """
    Draws a beautiful dark-mode recipe card with a grid, an orange/gold border,
    a branding capsule, and two columns: ingredients list (left) and steps list (right).
    """
    W, H = 1080, 1080
    bg_color1 = (18, 18, 24)
    bg_color2 = (28, 28, 38)
    
    img = create_diagonal_gradient(W, H, bg_color1, bg_color2)
    
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ol = ImageDraw.Draw(overlay)
    
    grid_color = (255, 255, 255, 10)
    for gx in range(100, 980, 40):
        for gy in range(100, 980, 40):
            draw_ol.ellipse([gx-1.5, gy-1.5, gx+1.5, gy+1.5], fill=grid_color)
            
    border_color = (255, 107, 53)
    border_inset = 45
    draw_ol.rectangle([border_inset, border_inset, W - border_inset, H - border_inset], outline=border_color, width=4)
    
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    capsule_font = ImageFont.truetype(FONT_PATH, 24)
    draw_capsule(
        draw=draw,
        x_center=W // 2,
        y_center=95,
        text=clean_image_text("พริก 10 เม็ด • สูตรแซ่บ"),
        font=capsule_font,
        fill_color=(255, 107, 53),
        text_color=(255, 255, 255)
    )
    
    title_clean = clean_image_text(title)
    title_sz = 60
    while title_sz >= 32:
        t_font = ImageFont.truetype(FONT_PATH, title_sz)
        t_lines = _wrap_text(draw, title_clean, t_font, W - 160)
        t_lh = draw.textbbox((0, 0), "ก A", font=t_font)[3]
        t_gap = max(4, title_sz // 8)
        t_h = t_lh * len(t_lines) + t_gap * (len(t_lines) - 1)
        if t_h <= 120:
            break
        title_sz -= 4
        
    y = 140
    for line in t_lines:
        t_bbox = draw.textbbox((0, 0), line, font=t_font)
        tw = t_bbox[2] - t_bbox[0]
        tx = (W - tw) // 2 - t_bbox[0]
        draw.text((tx + 2, y + 2), line, font=t_font, fill=(0, 0, 0, 80))
        draw.text((tx, y), line, font=t_font, fill=(255, 180, 50))
        y += t_lh + t_gap
        
    desc_clean = clean_image_text(desc) if desc else ""
    desc_lines = []
    desc_lh = 0
    desc_gap = 0
    desc_h = 0
    if desc_clean:
        desc_font = ImageFont.truetype(FONT_PATH, 26)
        desc_lines = _wrap_text(draw, desc_clean, desc_font, W - 160)
        desc_lh = draw.textbbox((0, 0), "ก A", font=desc_font)[3]
        desc_gap = 6
        desc_h = desc_lh * len(desc_lines) + desc_gap * (len(desc_lines) - 1)
        
    y_desc = y + 10
    for line in desc_lines:
        d_bbox = draw.textbbox((0, 0), line, font=desc_font)
        dw = d_bbox[2] - d_bbox[0]
        dx = (W - dw) // 2 - d_bbox[0]
        draw.text((dx, y_desc), line, font=desc_font, fill=(220, 220, 220))
        y_desc += desc_lh + desc_gap
        
    y_content_start = max(310, y_desc + 20)
    
    # Column divider line
    draw.line([(540, y_content_start + 10), (540, 1000)], fill=(255, 107, 53, 150), width=2)
    
    hdr_font = ImageFont.truetype(FONT_PATH, 34)
    lh_text = "วัตถุดิบ"
    lh_bbox = draw.textbbox((0, 0), lh_text, font=hdr_font)
    lh_tw = lh_bbox[2] - lh_bbox[0]
    lh_th = lh_bbox[3] - lh_bbox[1]
    
    # Rounded rectangles for headers
    overlay_hdr = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_oh = ImageDraw.Draw(overlay_hdr)
    draw_oh.rounded_rectangle([295 - lh_tw//2 - 20, y_content_start - 6, 295 + lh_tw//2 + 20, y_content_start + lh_th + 10], radius=8, fill=(255, 107, 53, 50), outline=(255, 107, 53), width=2)
    
    rh_text = "ขั้นตอนการทำ"
    rh_bbox = draw.textbbox((0, 0), rh_text, font=hdr_font)
    rh_tw = rh_bbox[2] - rh_bbox[0]
    rh_th = rh_bbox[3] - rh_bbox[1]
    draw_oh.rounded_rectangle([785 - rh_tw//2 - 20, y_content_start - 6, 785 + rh_tw//2 + 20, y_content_start + rh_th + 10], radius=8, fill=(255, 180, 50, 50), outline=(255, 180, 50), width=2)
    
    img = Image.alpha_composite(img.convert("RGBA"), overlay_hdr).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    draw.text((295 - lh_tw//2 - lh_bbox[0], y_content_start - lh_bbox[1]), lh_text, font=hdr_font, fill=(255, 255, 255))
    draw.text((785 - rh_tw//2 - rh_bbox[0], y_content_start - rh_bbox[1]), rh_text, font=hdr_font, fill=(255, 255, 255))
    
    y_list_start = y_content_start + lh_th + 30
    list_h = 1000 - y_list_start
    
    if isinstance(ingredients, str):
        ingredients_list = [line.strip() for line in ingredients.split("\n") if line.strip()]
    else:
        ingredients_list = [str(i).strip() for i in ingredients if str(i).strip()]

    if isinstance(steps, str):
        steps_list = [line.strip() for line in steps.split("\n") if line.strip()]
    else:
        steps_list = [str(s).strip() for s in steps if str(s).strip()]
        
    cleaned_ingredients = []
    for ing in ingredients_list:
        ing_text = re.sub(r'^[•\-\*\s]+', '', ing).strip()
        cleaned_ingredients.append(f"• {ing_text}")
        
    cleaned_steps = []
    for idx, step in enumerate(steps_list, 1):
        step_text = re.sub(r'^\d+[\.\-\s\u2013]+', '', step).strip()
        cleaned_steps.append(f"{idx}. {step_text}")
        
    item_sz = 26
    col_w = 400
    
    while item_sz >= 16:
        font = ImageFont.truetype(FONT_PATH, item_sz)
        line_h = draw.textbbox((0, 0), "ก A", font=font)[3]
        item_gap = max(4, item_sz // 4)
        line_gap = max(2, item_sz // 8)
        
        left_h = 0
        left_wrapped = []
        for ing in cleaned_ingredients:
            lines = _wrap_text(draw, ing, font, col_w)
            left_wrapped.append(lines)
            ing_h = len(lines) * line_h + (len(lines) - 1) * line_gap
            left_h += ing_h + item_gap
        left_h -= item_gap
        
        right_h = 0
        right_wrapped = []
        for step in cleaned_steps:
            lines = _wrap_text(draw, step, font, col_w)
            right_wrapped.append(lines)
            step_h = len(lines) * line_h + (len(lines) - 1) * line_gap
            right_h += step_h + item_gap
        right_h -= item_gap
        
        if left_h <= list_h and right_h <= list_h:
            break
        item_sz -= 2
        
    font = ImageFont.truetype(FONT_PATH, max(16, item_sz))
    line_h = draw.textbbox((0, 0), "ก A", font=font)[3]
    item_gap = max(4, font.size // 4)
    line_gap = max(2, font.size // 8)
    
    y = y_list_start
    for lines in left_wrapped:
        for line in lines:
            draw.text((85, y), line, font=font, fill=(245, 245, 245))
            y += line_h + line_gap
        y += item_gap - line_gap

    y = y_list_start
    for lines in right_wrapped:
        for line in lines:
            draw.text((575, y), line, font=font, fill=(245, 245, 245))
            y += line_h + line_gap
        y += item_gap - line_gap
        
    img.save(out_path, "JPEG", quality=92)
    return out_path

