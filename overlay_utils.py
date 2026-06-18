# overlay_utils.py â€” PIL text overlay for Facebook bot images

import os
import re
from PIL import Image, ImageDraw, ImageFont, ImageFilter

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
            draw.text((x + dx, y + dy), clean_line, font=font, fill=shadow)
        draw.text((x, y), clean_line, font=font, fill=fill)
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

def _draw_soft_shadow(image_size, box_coords, radius, shadow_color=(0, 0, 0), shadow_alpha=80, shadow_offset=(0, 8), blur_radius=16):
    """Draw a soft drop shadow using Gaussian blur on an alpha mask layer"""
    shadow_layer = Image.new("RGBA", image_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(shadow_layer, "RGBA")
    
    x1, y1, x2, y2 = box_coords
    dx, dy = shadow_offset
    s_rect = [x1 + dx, y1 + dy, x2 + dx, y2 + dy]
    
    fill_rgba = (*shadow_color, int(shadow_alpha))
    try:
        draw.rounded_rectangle(s_rect, radius=radius, fill=fill_rgba)
    except Exception:
        draw.rectangle(s_rect, fill=fill_rgba)
        
    if blur_radius > 0:
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        
    return shadow_layer


def _draw_supersampled_card(card_size, radius, fill_color, border_color=None, border_width=0, ss=4):
    """Draw a card with high-res supersampling to ensure perfectly smooth anti-aliased corners"""
    w, h = card_size
    ss_w, ss_h = w * ss, h * ss
    ss_radius = radius * ss
    ss_border_width = border_width * ss
    
    ss_img = Image.new("RGBA", (ss_w, ss_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(ss_img, "RGBA")
    
    rect = [0, 0, ss_w, ss_h]
    try:
        draw.rounded_rectangle(rect, radius=ss_radius, fill=fill_color)
        if border_color and ss_border_width > 0:
            draw.rounded_rectangle(rect, radius=ss_radius, outline=border_color, width=ss_border_width)
    except Exception:
        draw.rectangle(rect, fill=fill_color)
        if border_color and ss_border_width > 0:
            draw.rectangle(rect, outline=border_color, width=ss_border_width)
            
    return ss_img.resize((w, h), Image.Resampling.LANCZOS)


def _draw_discount_badge(img, text, accent_color):
    """
    Draws a tilted, circular e-commerce sticker/badge in the top-right corner of the image.
    Uses 4x supersampling to ensure clean, smooth anti-aliased corners and text.
    """
    W, H = img.size
    # Size of the badge: 180x180 px
    bw = 180
    bh = 180
    
    # Supersampled dimensions
    ss = 4
    ss_w, ss_h = bw * ss, bh * ss
    
    badge_img = Image.new("RGBA", (ss_w, ss_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge_img, "RGBA")
    
    # 1. Circle color: Convert accent_color to RGB tuple
    if isinstance(accent_color, str):
        if accent_color.startswith("#"):
            accent_rgb = tuple(int(accent_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        else:
            accent_rgb = (255, 69, 0) # Fallback to red-orange
    else:
        accent_rgb = accent_color
        
    fill_color = (*accent_rgb, 255)
    
    # Draw circle on supersampled canvas
    draw.ellipse([0, 0, ss_w, ss_h], fill=fill_color)
    # Add a thin white border
    draw.ellipse([8, 8, ss_w - 8, ss_h - 8], outline=(255, 255, 255, 255), width=8)
    
    # 2. Draw text
    font_size = 40 * ss # Start with size 160
    
    lines = []
    if " " in text:
        lines = [w.strip() for w in text.split(" ") if w.strip()]
    elif len(text) > 4:
        if text.startswith("ลด") and len(text) > 2:
            lines = ["ลด", text[2:]]
        else:
            lines = [text]
    else:
        lines = [text]
        
    while font_size >= 12 * ss:
        font = ImageFont.truetype(FONT_PATH, font_size)
        lh = draw.textbbox((0, 0), "ก A", font=font)[3]
        gap = 4 * ss
        total_h = lh * len(lines) + gap * (len(lines) - 1)
        
        width_ok = all(draw.textbbox((0, 0), l, font=font)[2] <= (bw - 30) * ss for l in lines)
        if total_h <= (bh - 30) * ss and width_ok:
            break
        font_size -= 4 * ss
        
    font = ImageFont.truetype(FONT_PATH, font_size)
    lh = draw.textbbox((0, 0), "ก A", font=font)[3]
    gap = 4 * ss
    total_h = lh * len(lines) + gap * (len(lines) - 1)
    
    y = (ss_h - total_h) // 2
    for line in lines:
        tw = draw.textbbox((0, 0), line, font=font)[2]
        x = (ss_w - tw) // 2
        draw.text((x + 2, y + 2), line, font=font, fill=(0, 0, 0, 60))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += lh + gap
        
    badge_img = badge_img.resize((bw, bh), Image.Resampling.LANCZOS)
    badge_img = badge_img.rotate(10, resample=Image.Resampling.BICUBIC, expand=True)
    
    bw_new, bh_new = badge_img.size
    bx = W - bw_new - 40
    by = 40
    
    shadow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    badge_alpha = badge_img.split()[3]
    shadow_mask = Image.new("RGBA", badge_img.size, (0, 0, 0, 80))
    shadow_mask.putalpha(badge_alpha)
    shadow_layer.paste(shadow_mask, (bx + 4, by + 8))
    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=8))
    
    img = Image.alpha_composite(img.convert("RGBA"), shadow_layer)
    badge_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    badge_layer.paste(badge_img, (bx, by))
    img = Image.alpha_composite(img, badge_layer)
    
    return img


def _draw_watermark_capsule(img, text, accent_color):
    """
    Draws a small, elegant branding watermark capsule in the top-left corner.
    """
    W, H = img.size
    
    temp_img = Image.new("RGBA", (100, 100))
    temp_draw = ImageDraw.Draw(temp_img)
    
    font_size = 20
    font = ImageFont.truetype(FONT_PATH, font_size)
    bbox = temp_draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    
    pad_x = 20
    pad_y = 10
    
    bw = tw + pad_x * 2
    bh = th + pad_y * 2
    
    bx = 40
    by = 40
    
    ss = 4
    ss_w, ss_h = bw * ss, bh * ss
    ss_cr = (bh // 2) * ss
    
    capsule_img = Image.new("RGBA", (ss_w, ss_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(capsule_img, "RGBA")
    
    draw.rounded_rectangle([0, 0, ss_w, ss_h], radius=ss_cr, fill=(15, 15, 20, 190))
    
    if isinstance(accent_color, str):
        if accent_color.startswith("#"):
            accent_rgb = tuple(int(accent_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        else:
            accent_rgb = (0, 191, 255)
    else:
        accent_rgb = accent_color
        
    draw.rounded_rectangle([0, 0, ss_w, ss_h], radius=ss_cr, outline=(*accent_rgb, 200), width=2 * ss)
    
    ss_font = ImageFont.truetype(FONT_PATH, font_size * ss)
    ss_bbox = draw.textbbox((0, 0), text, font=ss_font)
    ss_tw = ss_bbox[2] - ss_bbox[0]
    ss_th = ss_bbox[3] - ss_bbox[1]
    
    tx = (ss_w - ss_tw) // 2 - ss_bbox[0]
    ty = (ss_h - ss_th) // 2 - ss_bbox[1]
    
    draw.text((tx, ty), text, font=ss_font, fill=(255, 255, 255, 240))
    
    capsule_img = capsule_img.resize((bw, bh), Image.Resampling.LANCZOS)
    
    capsule_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    capsule_layer.paste(capsule_img, (bx, by))
    img = Image.alpha_composite(img.convert("RGBA"), capsule_layer)
    
    return img


def add_overlay(img_path, line1, line2, accent_color, out_path=None, font_name=None, style="premium_card", badge_text=None, watermark="พริก 10 เม็ด"):
    """
    Overlays text directly on the image.
    Supports two styles:
      - "gradient": Matichon Style bottom dark gradient overlay.
      - "premium_card": Modern rounded card sticker at the bottom with soft drop shadow.
    """
    global FONT_PATH
    if font_name:
        FONT_PATH = os.path.join(os.path.dirname(__file__), "fonts", font_name)

    W, H = 1080, 1080
    
    # 1. Prepare Base Image
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

    if style == "premium_card":
        # ── PREMIUM CARD STYLE ───────────────────────────────────────────────
        draw = ImageDraw.Draw(img)
        
        # Dimensions & Coordinates
        bw = 980
        bx = (W - bw) // 2 # 50
        
        # Check text structure
        if line2:
            # Two-panel card (colored header, white body)
            header_h = 100
            body_h = 220
            card_h = header_h + body_h
            by = 700
            cr = 24
            
            # Prepare header (colored) and body (white) colors
            if isinstance(accent_color, str):
                accent_rgb = tuple(int(accent_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
            else:
                accent_rgb = accent_color
                
            header_color = (*accent_rgb, 255)
            body_color = (255, 255, 255, 242) # 95% white
            
            # Render supersampled card parts
            card_img = Image.new("RGBA", (bw, card_h), (0, 0, 0, 0))
            
            # Header panel (top rounded)
            header_panel = _draw_supersampled_card((bw, header_h + cr), cr, header_color)
            card_img.paste(header_panel.crop((0, 0, bw, header_h)), (0, 0))
            
            # Body panel (bottom rounded)
            body_panel = _draw_supersampled_card((bw, body_h + cr), cr, body_color)
            card_img.paste(body_panel.crop((0, cr, bw, body_h + cr)), (0, header_h))
            
            # Draw shadow layer
            shadow_layer = _draw_soft_shadow((W, H), [bx, by, bx + bw, by + card_h], cr)
            img = Image.alpha_composite(img.convert("RGBA"), shadow_layer)
            
            # Composite card onto image
            card_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            card_layer.paste(card_img, (bx, by))
            img = Image.alpha_composite(img, card_layer).convert("RGB")
            
            # Draw Text
            draw_ctx = ImageDraw.Draw(img)
            
            # Fit line1 in header
            font1, size1, lines1, lh1, gap1 = _fit_wrapped(draw_ctx, line1, bw - 60, header_h - 20, start=48, min_size=24)
            h_text1 = lh1 * len(lines1) + gap1 * (len(lines1) - 1)
            y_start1 = by + (header_h - h_text1) // 2
            
            # Contrast text color for header
            r, g, b = accent_rgb
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            h_text_fill = (40, 40, 40) if brightness > 128 else (255, 255, 255)
            
            _draw_lines(draw_ctx, lines1, font1, lh1, gap1, y_start1, W, fill=h_text_fill, shadow=None)
            
            # Fit line2 in body
            font2, size2, lines2, lh2, gap2 = _fit_wrapped(draw_ctx, line2, bw - 60, body_h - 40, start=44, min_size=22)
            h_text2 = lh2 * len(lines2) + gap2 * (len(lines2) - 1)
            y_start2 = by + header_h + (body_h - h_text2) // 2
            
            _draw_lines(draw_ctx, lines2, font2, lh2, gap2, y_start2, W, fill=(40, 40, 40), shadow=None)
            
        else:
            # Single-panel card (white body)
            card_h = 240
            by = 780
            cr = 24
            body_color = (255, 255, 255, 242)
            
            # Draw shadow layer
            shadow_layer = _draw_soft_shadow((W, H), [bx, by, bx + bw, by + card_h], cr)
            img = Image.alpha_composite(img.convert("RGBA"), shadow_layer)
            
            # Render and composite card
            card_img = _draw_supersampled_card((bw, card_h), cr, body_color)
            card_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            card_layer.paste(card_img, (bx, by))
            img = Image.alpha_composite(img, card_layer).convert("RGB")
            
            # Draw Text
            draw_ctx = ImageDraw.Draw(img)
            
            # Fit line1 in card
            font1, size1, lines1, lh1, gap1 = _fit_wrapped(draw_ctx, line1, bw - 60, card_h - 40, start=54, min_size=24)
            h_text1 = lh1 * len(lines1) + gap1 * (len(lines1) - 1)
            y_start1 = by + (card_h - h_text1) // 2
            
            _draw_lines(draw_ctx, lines1, font1, lh1, gap1, y_start1, W, fill=(40, 40, 40), shadow=None)
            
    else:
        # ── CLASSIC GRADIENT STYLE ───────────────────────────────────────────
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
        _draw_lines(draw, lines1, font1, lh1, gap1, y_start, W, fill=accent_color, shadow=(0, 0, 0))

        # Draw line2 — white
        if line2:
            n1 = len(lines1)
            b1 = draw.textbbox((0, 0), lines1[-1], font=font1)
            pixel_bottom1 = y_start + lh1 * (n1 - 1) + gap1 * (n1 - 1) + b1[3]
            b2 = draw.textbbox((0, 0), lines2[0], font=font2)
            y2 = pixel_bottom1 + BLOCK_GAP - b2[1]
            _draw_lines(draw, lines2, font2, lh2, gap2, y2, W, fill=(255, 255, 255), shadow=(0, 0, 0))

    # ── BADGES & WATERMARKS ───────────────────────────────────────────────
    if badge_text:
        img = _draw_discount_badge(img, badge_text, accent_color)
    if watermark:
        img = _draw_watermark_capsule(img, watermark, accent_color)
    # ──────────────────────────────────────────────────────────────────────

    img = img.convert("RGB")

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
        clean_line = line.replace('\u200b', '').replace('\\u200b', '')
        bbox = draw.textbbox((0, 0), clean_line, font=main_font)
        tw = bbox[2] - bbox[0]
        tx = (W - tw) // 2 - bbox[0]
        # Drop shadow
        draw.text((tx + 2, y + 2), clean_line, font=main_font, fill=(0, 0, 0, 40))
        # Main text
        draw.text((tx, y), clean_line, font=main_font, fill=(40, 40, 40))
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


def create_recipe_card(topic, options, question, out_path, bg_img_path=None):
    """
    Draws a beautiful food debate card (ศาลอาหารไทย) with a background food image (60% dark overlay),
    an orange/gold border, a branding capsule, and centered debate text (Topic, Options, Question).
    """
    W, H = 1080, 1080
    bg_color1 = (18, 18, 24)
    bg_color2 = (28, 28, 38)
    
    if bg_img_path and os.path.exists(bg_img_path):
        try:
            bg_raw = Image.open(bg_img_path).convert("RGBA")
            # Crop to 1:1 ratio
            w_raw, h_raw = bg_raw.size
            min_side = min(w_raw, h_raw)
            left = (w_raw - min_side) // 2
            top = (h_raw - min_side) // 2
            right = left + min_side
            bottom = top + min_side
            bg_crop = bg_raw.crop((left, top, right, bottom))
            bg_resized = bg_crop.resize((W, H), Image.Resampling.LANCZOS)
            
            # Apply a moderate dark overlay so the food is visible but text is readable
            dark_overlay = Image.new("RGBA", (W, H), (15, 15, 20, 160)) # ~63% opacity
            img = Image.alpha_composite(bg_resized, dark_overlay).convert("RGB")
        except Exception as e:
            print(f"Error loading background image {bg_img_path}: {e}")
            img = create_diagonal_gradient(W, H, bg_color1, bg_color2)
    else:
        img = create_diagonal_gradient(W, H, bg_color1, bg_color2)
    
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_ol = ImageDraw.Draw(overlay)
    
    # Dotted grid decoration
    grid_color = (255, 255, 255, 10)
    for gx in range(100, 980, 40):
        for gy in range(100, 980, 40):
            draw_ol.ellipse([gx-1.5, gy-1.5, gx+1.5, gy+1.5], fill=grid_color)
            
    # Orange border
    border_color = (255, 107, 53)
    border_inset = 45
    draw_ol.rectangle([border_inset, border_inset, W - border_inset, H - border_inset], outline=border_color, width=4)
    
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img)
    
    # Top Branding Capsule
    capsule_font = ImageFont.truetype(FONT_PATH, 24)
    draw_capsule(
        draw=draw,
        x_center=W // 2,
        y_center=95,
        text=clean_image_text("พริก 10 เม็ด • ศาลอาหารไทย"),
        font=capsule_font,
        fill_color=(255, 107, 53),
        text_color=(255, 255, 255)
    )
    
    # Load fonts
    topic_font = ImageFont.truetype(FONT_PATH, 76)
    options_font = ImageFont.truetype(FONT_PATH, 62)
    question_font = ImageFont.truetype(FONT_PATH, 46)
    
    # Clean text to remove tofu chars and other garbage
    topic_clean = clean_image_text(topic).replace('\u200b', '').replace('\\u200b', '')
    options_clean = clean_image_text(options).replace('\u200b', '').replace('\\u200b', '')
    question_clean = clean_image_text(question).replace('\u200b', '').replace('\\u200b', '')
    
    # Wrap text lines
    topic_lines = _wrap_text(draw, topic_clean, topic_font, W - 180)
    options_lines = _wrap_text(draw, options_clean, options_font, W - 180)
    question_lines = _wrap_text(draw, question_clean, question_font, W - 180)
    
    # Calculate heights and spacing
    topic_lh = draw.textbbox((0, 0), "ก A", font=topic_font)[3]
    options_lh = draw.textbbox((0, 0), "ก A", font=options_font)[3]
    question_lh = draw.textbbox((0, 0), "ก A", font=question_font)[3]
    
    line_gap = 10
    sec_gap = 42
    
    h_topic = topic_lh * len(topic_lines) + line_gap * (len(topic_lines) - 1)
    h_options = options_lh * len(options_lines) + line_gap * (len(options_lines) - 1)
    h_question = question_lh * len(question_lines) + line_gap * (len(question_lines) - 1)
    
    total_h = h_topic + sec_gap + h_options + sec_gap + h_question
    
    # Center vertically
    y = (H - total_h) // 2 + 30
    
    # Draw Topic lines
    for line in topic_lines:
        line_clean = line.replace('\u200b', '').replace('\\u200b', '')
        t_bbox = draw.textbbox((0, 0), line_clean, font=topic_font)
        tw = t_bbox[2] - t_bbox[0]
        tx = (W - tw) // 2 - t_bbox[0]
        # Shadow
        draw.text((tx + 2, y + 2), line_clean, font=topic_font, fill=(0, 0, 0, 150))
        # Main text
        draw.text((tx, y), line_clean, font=topic_font, fill=(255, 180, 50)) # Gold
        y += topic_lh + line_gap
    y += sec_gap - line_gap
    
    # Draw Options lines
    for line in options_lines:
        line_clean = line.replace('\u200b', '').replace('\\u200b', '')
        t_bbox = draw.textbbox((0, 0), line_clean, font=options_font)
        tw = t_bbox[2] - t_bbox[0]
        tx = (W - tw) // 2 - t_bbox[0]
        # Shadow
        draw.text((tx + 2, y + 2), line_clean, font=options_font, fill=(0, 0, 0, 150))
        # Main text
        draw.text((tx, y), line_clean, font=options_font, fill=(255, 255, 255)) # White
        y += options_lh + line_gap
    y += sec_gap - line_gap
    
    # Draw Question lines
    for line in question_lines:
        line_clean = line.replace('\u200b', '').replace('\\u200b', '')
        t_bbox = draw.textbbox((0, 0), line_clean, font=question_font)
        tw = t_bbox[2] - t_bbox[0]
        tx = (W - tw) // 2 - t_bbox[0]
        # Shadow
        draw.text((tx + 2, y + 2), line_clean, font=question_font, fill=(0, 0, 0, 150))
        # Main text
        draw.text((tx, y), line_clean, font=question_font, fill=(220, 220, 220)) # Light Gray
        y += question_lh + line_gap
        
    img.save(out_path, "JPEG", quality=92)
    return out_path

