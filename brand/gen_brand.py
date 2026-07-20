# -*- coding: utf-8 -*-
"""產生樹德市場觀察室的品牌視覺:LINE OA 頭像 + Rich Menu。
SHUTER 品牌紅 + 財經深藍。若有官方 logo 檔,可替換 emblem 區塊。
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SS = 3  # 超取樣,邊緣更平滑

# ---- 品牌色 ----
NAVY = (16, 27, 45)        # 深藍底(財經沉穩)
NAVY2 = (24, 40, 66)
RED = (200, 24, 40)        # SHUTER 品牌紅
RED_D = (150, 16, 28)
GOLD = (222, 170, 92)      # 市場上揚金
WHITE = (245, 248, 252)
GREY = (150, 165, 185)

FONT_BLACK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_MED = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"


def font(path, size):
    return ImageFont.truetype(path, size)


def vgrad(w, h, top, bottom):
    base = Image.new("RGB", (w, h), top)
    top_img = Image.new("RGB", (w, h), bottom)
    mask = Image.new("L", (w, h))
    md = mask.load()
    for y in range(h):
        v = int(255 * y / max(1, h - 1))
        for x in range(w):
            md[x, y] = v
    base.paste(top_img, (0, 0), mask)
    return base


def center_text(d, cx, y, text, ft, fill, anchor="mm"):
    d.text((cx, y), text, font=ft, fill=fill, anchor=anchor)


def draw_emblem(d, cx, cy, r):
    """紅色圓環 + 上揚柱狀 + 箭頭(市場向上)。r = 半徑。"""
    # 紅環
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=RED, width=int(r * 0.13))
    # 三根上升柱(金)
    barw = r * 0.22
    gap = r * 0.14
    base_y = cy + r * 0.42
    x0 = cx - (barw * 1.5 + gap)
    heights = [r * 0.42, r * 0.62, r * 0.86]
    tops = []
    for i, hgt in enumerate(heights):
        x = x0 + i * (barw + gap)
        top = base_y - hgt
        d.rounded_rectangle([x, top, x + barw, base_y], radius=int(barw * 0.3), fill=GOLD)
        tops.append((x + barw / 2, top))
    # 上揚折線 + 箭頭(白)
    p1 = (tops[0][0], tops[0][1] - r * 0.04)
    p3 = (tops[2][0], tops[2][1] - r * 0.12)
    d.line([p1, (tops[1][0], tops[1][1] - r * 0.08), p3], fill=WHITE, width=int(r * 0.055))
    ah = r * 0.16
    d.polygon([
        (p3[0] + ah * 0.15, p3[1] - ah * 0.15),
        (p3[0] - ah * 0.9, p3[1] - ah * 0.15),
        (p3[0] + ah * 0.15, p3[1] + ah * 0.8),
    ], fill=WHITE)


def make_avatar():
    S = 640 * SS
    img = vgrad(S, S, NAVY, NAVY2).convert("RGBA")
    d = ImageDraw.Draw(img)
    cx = S // 2
    # emblem
    draw_emblem(d, cx, int(S * 0.34), int(S * 0.20))
    # 主字標:樹德SHUTER
    f_tw = font(FONT_BLACK, int(S * 0.135))
    f_en = font(FONT_BLACK, int(S * 0.115))
    tw = "樹德"
    en = " SHUTER"
    # 量測寬度置中
    bb1 = d.textbbox((0, 0), tw, font=f_tw)
    bb2 = d.textbbox((0, 0), en, font=f_en)
    w1 = bb1[2] - bb1[0]
    w2 = bb2[2] - bb2[0]
    total = w1 + w2
    y_word = int(S * 0.62)
    x_start = cx - total // 2
    d.text((x_start, y_word), tw, font=f_tw, fill=WHITE, anchor="lm")
    d.text((x_start + w1, y_word), en, font=f_en, fill=RED, anchor="lm")
    # 副標
    f_sub = font(FONT_MED, int(S * 0.072))
    center_text(d, cx, int(S * 0.78), "市 場 觀 察 室", f_sub, GOLD)
    # 底線
    d.rectangle([cx - int(S * 0.18), int(S * 0.855), cx + int(S * 0.18), int(S * 0.862)], fill=RED)

    out = img.resize((640, 640), Image.LANCZOS).convert("RGB")
    p = os.path.join(HERE, "oa_avatar_640.png")
    out.save(p)
    print("avatar ->", p)


def _icon_chart(d, cx, cy, s, color):
    """柱狀圖 + 上揚箭頭。s = 圖示高度基準。"""
    barw = s * 0.18
    gap = s * 0.14
    base = cy + s * 0.42
    x0 = cx - (barw * 1.5 + gap)
    for i, h in enumerate([s * 0.4, s * 0.62, s * 0.86]):
        x = x0 + i * (barw + gap)
        d.rounded_rectangle([x, base - h, x + barw, base], radius=int(barw * 0.3), fill=color)
    # 箭頭
    d.line([(cx - s * 0.5, cy + s * 0.1), (cx + s * 0.5, cy - s * 0.5)], fill=WHITE, width=int(s * 0.06))
    ah = s * 0.22
    tip = (cx + s * 0.5, cy - s * 0.5)
    d.polygon([(tip[0] + ah * 0.1, tip[1] - ah * 0.1),
               (tip[0] - ah, tip[1] - ah * 0.1),
               (tip[0] + ah * 0.1, tip[1] + ah)], fill=WHITE)


def _icon_doc(d, cx, cy, s, color):
    """文件 + 內文線條。"""
    w = s * 0.78
    h = s * 1.02
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=int(s * 0.08),
                        outline=color, width=int(s * 0.06))
    for i in range(4):
        ly = y0 + h * (0.24 + i * 0.19)
        d.line([(x0 + w * 0.16, ly), (x0 + w * 0.84, ly)], fill=color, width=int(s * 0.045))


def _icon_bulb(d, cx, cy, s, color):
    """問號圓圈(使用說明)。"""
    r = s * 0.52
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=int(s * 0.06))
    f_q = font(FONT_BLACK, int(s * 0.9))
    d.text((cx, cy - s * 0.02), "?", font=f_q, fill=color, anchor="mm")


def make_richmenu():
    """2500x843 compact,三格:即時大盤 / 最新研報 / 使用說明。"""
    W, H = 2500 * 1, 843 * 1
    SSf = 2
    Wf, Hf = W * SSf, H * SSf
    img = vgrad(Wf, Hf, NAVY, NAVY2).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 頂部品牌條
    d.rectangle([0, 0, Wf, int(Hf * 0.055)], fill=RED)

    cells = [
        (_icon_chart, "即時大盤", "六大指數行情", GOLD),
        (_icon_doc, "最新研報", "研報 / 晨訊摘要", WHITE),
        (_icon_bulb, "使用說明", "怎麼問、能問什麼", GOLD),
    ]
    cw = Wf // 3
    f_title = font(FONT_BLACK, int(Hf * 0.115))
    f_desc = font(FONT_MED, int(Hf * 0.058))
    icon_s = Hf * 0.26

    for i, (icon_fn, title, desc, accent) in enumerate(cells):
        cx = cw * i + cw // 2
        # 分隔線
        if i > 0:
            d.line([(cw * i, int(Hf * 0.18)), (cw * i, int(Hf * 0.85))], fill=(60, 78, 108), width=3)
        icon_fn(d, cx, int(Hf * 0.35), icon_s, accent)
        center_text(d, cx, int(Hf * 0.62), title, f_title, WHITE)
        center_text(d, cx, int(Hf * 0.77), desc, f_desc, GREY)

    out = img.resize((W, H), Image.LANCZOS).convert("RGB")
    p = os.path.join(HERE, "richmenu_2500x843.png")
    out.save(p)
    print("richmenu ->", p)


if __name__ == "__main__":
    make_avatar()
    make_richmenu()
    print("done")
