"""LINE Flex 圖卡渲染 —— 樹德投資助理。

把 ai.py 產出的結構化卡片(dict)渲染成好看好讀的 LINE Flex Message。
混合式:
  - recommendation → 建議卡(市場/商品/這是什麼/方向 + 理由 + 風險)
  - analysis       → 分析卡(聚焦標的 + 理由 + 風險)
  - simple         → 簡答卡(標題 + 重點)
另提供 indices_message() 做大盤指數卡。

品牌色取自 SHUTER 形象(深色底 + 紅)。台股慣例:紅漲綠跌。
"""

# ---- 品牌與語意色 ----
BRAND_DARK = "#1B2340"   # 深藍(近黑,呼應頭像底)
BRAND_RED = "#C8102E"    # 樹德紅
INK = "#2B2F3A"          # 主文字
MUTED = "#8A93A6"        # 次要文字
BULL = "#D81E27"         # 偏多(紅)
BEAR = "#12A150"         # 偏空(綠)
FLAT = "#7A8699"         # 中性(灰)
RISK_BG = "#FBF0F1"
RISK_TITLE = "#B0242E"
RISK_TEXT = "#6B5257"

_DISCLAIMER = "內部決策參考;實際交易與大額配置請併會計師／律師／往來銀行等專業意見。"


def _stance_color(stance: str) -> str:
    if not stance:
        return FLAT
    if "多" in stance:
        return BULL
    if "空" in stance:
        return BEAR
    return FLAT


def _txt(text, **kw):
    o = {"type": "text", "text": str(text), "wrap": True}
    o.update(kw)
    return o


def _row(label, value):
    return {
        "type": "box", "layout": "horizontal", "spacing": "md",
        "contents": [
            _txt(label, size="sm", color=MUTED, flex=2, wrap=False),
            _txt(value, size="sm", color=INK, weight="bold", flex=5),
        ],
    }


def _bullets(points):
    out = []
    for p in points:
        if not p:
            continue
        out.append({
            "type": "box", "layout": "horizontal", "spacing": "sm",
            "contents": [
                _txt("・", size="sm", color=BRAND_RED, flex=0, wrap=False),
                _txt(p, size="sm", color=INK, flex=1),
            ],
        })
    return out


def _stance_pill(stance):
    color = _stance_color(stance)
    return {
        "type": "box", "layout": "horizontal", "spacing": "sm",
        "contents": [
            {
                "type": "box", "layout": "vertical", "flex": 0,
                "backgroundColor": color, "cornerRadius": "md",
                "paddingAll": "6px", "paddingStart": "12px", "paddingEnd": "12px",
                "contents": [_txt(f"傾向 {stance}", color="#FFFFFF", size="sm",
                                  weight="bold", align="center", wrap=False)],
            },
            {"type": "filler"},
        ],
    }


def _risk_box(risk):
    return {
        "type": "box", "layout": "vertical", "backgroundColor": RISK_BG,
        "cornerRadius": "md", "paddingAll": "12px", "spacing": "xs",
        "contents": [
            _txt("⚠ 風險與觀察重點", size="xs", weight="bold", color=RISK_TITLE, wrap=False),
            _txt(risk, size="sm", color=RISK_TEXT),
        ],
    }


def _header(label, title):
    return {
        "type": "box", "layout": "vertical", "backgroundColor": BRAND_DARK,
        "paddingAll": "16px", "spacing": "sm",
        "contents": [
            _txt(label, color="#FFFFFFCC", size="xs", weight="bold", wrap=False),
            _txt(title or "—", color="#FFFFFF", size="lg", weight="bold"),
        ],
    }


def _footer(note):
    text = note or _DISCLAIMER
    if note and note.strip() != _DISCLAIMER:
        text = f"{note}\n{_DISCLAIMER}"
    return {
        "type": "box", "layout": "vertical", "paddingAll": "12px",
        "contents": [_txt(text, size="xxs", color=MUTED, align="center")],
    }


def _decision_bubble(card, header_label):
    body = []
    if card.get("stance"):
        body.append(_stance_pill(card["stance"]))

    rows = []
    if card.get("market"):
        rows.append(_row("市場", card["market"]))
    if card.get("instrument"):
        rows.append(_row("商品", card["instrument"]))
    if card.get("instrument_desc"):
        rows.append(_row("這是什麼", card["instrument_desc"]))
    if card.get("entry"):
        rows.append(_row("方向", card["entry"]))
    if rows:
        if body:
            body.append({"type": "separator", "margin": "md"})
        body.append({"type": "box", "layout": "vertical", "spacing": "sm", "contents": rows})

    pts = _bullets(card.get("points", []))
    if pts:
        body.append({"type": "separator", "margin": "md"})
        body.append({"type": "box", "layout": "vertical", "spacing": "sm",
                     "contents": [_txt("為什麼", size="xs", color=MUTED, weight="bold", wrap=False)] + pts})

    if card.get("risk"):
        body.append(_risk_box(card["risk"]))

    if not body:
        body.append(_txt(card.get("title") or "—", size="sm", color=INK))

    return {
        "type": "bubble", "size": "mega",
        "header": _header(header_label, card.get("title")),
        "body": {"type": "box", "layout": "vertical", "spacing": "md",
                 "paddingAll": "16px", "contents": body},
        "footer": _footer(card.get("note")),
    }


def _simple_bubble(card):
    body = [_txt(card.get("title") or "—", size="md", weight="bold", color=INK)]
    pts = _bullets(card.get("points", []))
    if pts:
        body.append({"type": "box", "layout": "vertical", "spacing": "sm", "margin": "md",
                     "contents": pts})
    if card.get("risk"):
        body.append(_risk_box(card["risk"]))
    return {
        "type": "bubble", "size": "kilo",
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm", "paddingAll": "16px",
            "contents": [_txt("樹德投資助理", size="xs", color=BRAND_RED, weight="bold", wrap=False)] + body,
        },
        "footer": _footer(card.get("note")),
    }


def card_to_flex(card: dict) -> dict:
    """把 AI 卡片 dict 包成 LINE flex message(含 altText)。"""
    t = (card or {}).get("type", "simple")
    if t == "recommendation":
        bubble = _decision_bubble(card, "AI 投資建議")
    elif t == "analysis":
        bubble = _decision_bubble(card, "個股／主題分析")
    else:
        bubble = _simple_bubble(card)
    return {"type": "flex", "altText": _alt_text(card), "contents": bubble}


def _alt_text(card: dict) -> str:
    parts = [card.get("title") or "投資助理回覆"]
    if card.get("instrument"):
        parts.append(card["instrument"])
    if card.get("stance"):
        parts.append(card["stance"])
    return " · ".join(parts)[:390]


def card_to_text(card: dict) -> str:
    """把卡片壓成純文字,供:①記憶儲存 ②極端情況的文字保底。"""
    c = card or {}
    lines = [c.get("title", "").strip()]
    if c.get("stance"):
        lines.append(f"傾向:{c['stance']}")
    if c.get("market"):
        lines.append(f"市場:{c['market']}")
    if c.get("instrument"):
        d = f"商品:{c['instrument']}"
        if c.get("instrument_desc"):
            d += f"({c['instrument_desc']})"
        lines.append(d)
    if c.get("entry"):
        lines.append(f"方向:{c['entry']}")
    for p in c.get("points", [])[:4]:
        lines.append(f"・{p}")
    if c.get("risk"):
        lines.append(f"風險:{c['risk']}")
    return "\n".join([x for x in lines if x]).strip()


# ---- 大盤指數卡 ----
def indices_message(rows: list) -> dict:
    body = []
    for r in rows:
        pct = r["change_pct"]
        color = BULL if pct > 0 else (BEAR if pct < 0 else FLAT)
        arrow = "▲" if pct > 0 else ("▼" if pct < 0 else "–")
        body.append({
            "type": "box", "layout": "horizontal", "spacing": "sm",
            "contents": [
                _txt(r["name"], size="sm", color=INK, flex=5),
                _txt(f"{r['price']:,}", size="sm", color=INK, align="end", flex=4, wrap=False),
                _txt(f"{arrow}{pct:+.2f}%", size="sm", color=color, weight="bold",
                     align="end", flex=4, wrap=False),
            ],
        })
    bubble = {
        "type": "bubble", "size": "mega",
        "header": _header("今日大盤", "六大指數 / 匯率"),
        "body": {"type": "box", "layout": "vertical", "spacing": "md", "paddingAll": "16px",
                 "contents": body + [
                     {"type": "separator", "margin": "md"},
                     _txt("想聽方向解讀,直接問我即可。", size="xs", color=MUTED, align="center")]},
    }
    return {"type": "flex", "altText": "今日大盤 · 六大指數", "contents": bubble}
