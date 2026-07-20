# -*- coding: utf-8 -*-
"""樹德投資助理 Rich Menu(2500x1686):
上方大按鈕「AI 請直說」→ 開 LIFF/聊天頁;下方三格 即時大盤/最新研報/使用說明。
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

NAVY = (16, 27, 45)
NAVY2 = (24, 40, 66)
RED = (200, 24, 40)
RED_D = (150, 16, 28)
GOLD = (222, 170, 92)
WHITE = (245, 248, 252)
GREY = (150, 165, 185)

FONT_BLACK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_MED = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"


def font(p, s):
    return ImageFont.truetype(p, s)


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


def hgrad(w, h, left, right):
    base = Image.new("RGB", (w, h), left)
    r_img = Image.new("RGB", (w, h), right)
    mask = Image.new("L", (w, h))
    md = mask.load()
    for x in range(w):
        v = int(255 * x / max(1, w - 1))
        for y in range(h):
            md[x, y] = v
    base.paste(r_img, (0, 0), mask)
    return base


def _icon_chart(d, cx, cy, s, color):
    barw = s * 0.18
    gap = s * 0.14
    base = cy + s * 0.42
    x0 = cx - (barw * 1.5 + gap)
    for i, hh in enumerate([s * 0.4, s * 0.62, s * 0.86]):
        x = x0 + i * (barw + gap)
        d.rounded_rectangle([x, base - hh, x + barw, base], radius=int(barw * 0.3), fill=color)
    d.line([(cx - s * 0.5, cy + s * 0.1), (cx + s * 0.5, cy - s * 0.5)], fill=WHITE, width=int(s * 0.06))
    ah = s * 0.22
    tip = (cx + s * 0.5, cy - s * 0.5)
    d.polygon([(tip[0] + ah * 0.1, tip[1] - ah * 0.1),
               (tip[0] - ah, tip[1] - ah * 0.1),
               (tip[0] + ah * 0.1, tip[1] + ah)], fill=WHITE)


def _icon_doc(d, cx, cy, s, color):
    w = s * 0.78
    h = s * 1.02
    x0, y0 = cx - w / 2, cy - h / 2
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=int(s * 0.08), outline=color, width=int(s * 0.06))
    for i in range(4):
        ly = y0 + h * (0.24 + i * 0.19)
        d.line([(x0 + w * 0.16, ly), (x0 + w * 0.84, ly)], fill=color, width=int(s * 0.045))


def _icon_help(d, cx, cy, s, color):
    r = s * 0.52
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=int(s * 0.06))
    d.text((cx, cy - s * 0.02), "?", font=font(FONT_BLACK, int(s * 0.9)), fill=color, anchor="mm")


def _icon_chat_mic(d, cx, cy, s, color):
    """對話泡泡 + 麥克風(語音/文字問答)。"""
    # 對話泡泡
    w, h = s * 1.15, s * 0.9
    x0, y0 = cx - w / 2, cy - h / 2 - s * 0.08
    d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=int(s * 0.22), fill=color)
    # 泡泡小尾巴
    d.polygon([(x0 + w * 0.22, y0 + h - 2), (x0 + w * 0.12, y0 + h + s * 0.22),
               (x0 + w * 0.42, y0 + h - 2)], fill=color)
    # 麥克風(白,泡泡內)
    mcx, mcy = cx, y0 + h * 0.44
    mw, mh = s * 0.2, s * 0.34
    d.rounded_rectangle([mcx - mw / 2, mcy - mh / 2, mcx + mw / 2, mcy + mh / 2],
                        radius=int(mw / 2), fill=NAVY)
    d.arc([mcx - mw * 0.85, mcy - mh * 0.35, mcx + mw * 0.85, mcy + mh * 0.75],
          start=20, end=160, fill=NAVY, width=int(s * 0.045))
    d.line([(mcx, mcy + mh * 0.75), (mcx, mcy + mh * 0.98)], fill=NAVY, width=int(s * 0.045))


def make():
    W, H = 2500, 1686
    SS = 2
    Wf, Hf = W * SS, H * SS
    img = vgrad(Wf, Hf, NAVY, NAVY2).convert("RGBA")
    d = ImageDraw.Draw(img)

    # 頂部品牌紅條
    d.rectangle([0, 0, Wf, int(Hf * 0.028)], fill=RED)

    # ===== 上方大按鈕:AI 請直說 =====
    top_h = int(Hf * 0.60)
    pad = int(Wf * 0.035)
    btn = [pad, int(Hf * 0.075), Wf - pad, top_h - int(Hf * 0.03)]
    bw, bh = btn[2] - btn[0], btn[3] - btn[1]
    # 紅色漸層圓角按鈕
    btn_img = hgrad(bw, bh, RED, RED_D)
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw, bh], radius=int(bh * 0.16), fill=255)
    img.paste(btn_img, (btn[0], btn[1]), mask)

    bcx = (btn[0] + btn[2]) // 2
    bcy = (btn[1] + btn[3]) // 2
    # icon 在左
    icon_cx = btn[0] + int(bw * 0.16)
    _icon_chat_mic(d, icon_cx, bcy, int(bh * 0.42), WHITE)
    # 文字在右
    tx = btn[0] + int(bw * 0.30)
    f_big = font(FONT_BLACK, int(bh * 0.30))
    f_sub = font(FONT_MED, int(bh * 0.115))
    d.text((tx, bcy - int(bh * 0.10)), "AI 請直說", font=f_big, fill=WHITE, anchor="lm")
    d.text((tx, bcy + int(bh * 0.20)), "打字或語音 · 問我任何市場方向", font=f_sub, fill=(255, 226, 226), anchor="lm")

    # ===== 下方三格 =====
    base_y = top_h
    cells = [
        (_icon_chart, "即時大盤", "六大指數行情", GOLD),
        (_icon_doc, "最新研報", "研報 / 晨訊摘要", WHITE),
        (_icon_help, "使用說明", "怎麼問、能問什麼", GOLD),
    ]
    cw = Wf // 3
    region_h = Hf - base_y
    f_title = font(FONT_BLACK, int(region_h * 0.19))
    f_desc = font(FONT_MED, int(region_h * 0.098))
    icon_s = region_h * 0.30
    for i, (icon_fn, title, desc, accent) in enumerate(cells):
        cx = cw * i + cw // 2
        if i > 0:
            d.line([(cw * i, base_y + int(region_h * 0.18)), (cw * i, Hf - int(region_h * 0.18))],
                   fill=(60, 78, 108), width=3)
        icon_fn(d, cx, base_y + int(region_h * 0.34), icon_s, accent)
        d.text((cx, base_y + int(region_h * 0.62)), title, font=f_title, fill=WHITE, anchor="mm")
        d.text((cx, base_y + int(region_h * 0.80)), desc, font=f_desc, fill=GREY, anchor="mm")

    out = img.resize((W, H), Image.LANCZOS).convert("RGB")
    p = os.path.join(HERE, "richmenu_ai_2500x1686.png")
    out.save(p, quality=95)
    print("richmenu ->", p, os.path.getsize(p), "bytes")


if __name__ == "__main__":
    make()
