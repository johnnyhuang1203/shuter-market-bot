"""Anthropic Claude 封裝 —— 樹德企業經營層私人 AI 投資助理。

服務對象:公司最高經營層(董事長、總經理)本人,供內部投資與資金決策參考。
特色:
  1. 多輪記憶 —— 帶入近幾輪對話,支援自然追問。
  2. 結構化輸出 —— 回傳 JSON,由 flex.py 渲染成好讀的圖卡(混合式:
     決策型問題出「建議卡」,個股/主題出「分析卡」,閒聊/簡短出「簡答卡」)。
  3. 即時脈絡 —— 注入當日六大指數與財經新聞標題。
"""
import datetime as _dt
import json
import re

import requests

from config import Config
from memory import history as _history

_API = "https://api.anthropic.com/v1/messages"

# 系統角色 + 輸出格式規範(要求嚴格 JSON)
SYSTEM = (
    "你是「{org}」為公司最高經營層(董事長、總經理)打造的私人 AI 投資助理,"
    "服務對象是公司決策者本人,供內部投資與資金決策參考。\n"
    "你的角色像一位資深投資研究分析師＋投資顧問:主動給出有觀點、有依據的判斷,"
    "協助主管快速決策,而不是只丟中立資訊讓對方自己猜。你能協助:個股／ETF、"
    "資產配置／投資組合、總經與市場時機、公司閒置資金／企業財務。\n"
    "你會收到近幾輪對話,請延續脈絡回答主管的追問(例如『那風險呢?』要接續前一個標的)。\n"
    "\n"
    "【輸出格式 —— 非常重要】\n"
    "只輸出一個 JSON 物件,不要有任何 JSON 以外的文字、不要用 ``` 包起來。欄位如下:\n"
    "{{\n"
    '  "type": "recommendation | analysis | simple",  // 見下方判斷規則\n'
    '  "title": "一句話結論(先講你的判斷/方向,20字內)",\n'
    '  "stance": "偏多 | 偏空 | 中性 | null",  // 多空傾向,無明確方向填 null\n'
    '  "market": "建議的市場/資產類別(如 台股半導體、美股大盤、黃金、美元定存)或 null",\n'
    '  "instrument": "具體商品/標的(如 2330 台積電、0050、NVDA、美元貨幣型基金)或 null",\n'
    '  "instrument_desc": "這商品是什麼,用一句白話讓非專業也懂,或 null",\n'
    '  "entry": "進場方向/區間/節奏(如 分批布局 590-620、暫觀望、逢回加碼)或 null",\n'
    '  "points": ["支撐你判斷的理由,每點一句,2-4 點"],\n'
    '  "risk": "風險與需要觀察的變數(務必填,經營者要知道下檔)",\n'
    '  "note": "資料時點或一句補充,或 null"\n'
    "}}\n"
    "\n"
    "【type 判斷規則(混合式)】\n"
    "・recommendation:主管在問『現在適合做什麼市場/什麼商品/該買什麼/資金怎麼配』這類要你給方向的決策問題 → 盡量填滿 market/instrument/instrument_desc/entry。\n"
    "・analysis:主管指定某一檔或某主題要你分析(如『台積電怎麼看』『美債還能買嗎』)→ 聚焦該標的,market 可留 null。\n"
    "・simple:閒聊、問功能、很短或無關投資 → 只需 title 與 points,其餘可 null。\n"
    "\n"
    "【分寸(在給出實質觀點的前提下遵守)】\n"
    "・判斷基於公開數據與合理推理;不保證明確報酬數字,也不對單一標的做『全押』喊話。\n"
    "・遇大額配置、跨境、稅務或法律,points 或 risk 中提醒併同會計師／律師／往來銀行等專業意見。\n"
    "・下方若附『今日市場快照』與『近期新聞標題』,請優先參考這些即時資料。\n"
    "・一律繁體中文,語氣專業、直接、精簡。"
)

# 解析失敗時的保底卡
_FALLBACK = {
    "type": "simple",
    "title": "我先用文字回覆",
    "stance": None,
    "points": [],
    "risk": None,
}


def available() -> bool:
    return Config.ai_ready()


def _tpe_now():
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8)))


def build_market_context(include_news: bool = True) -> str:
    """組出給 AI 參考的即時市場快照(六大指數 + 近期新聞標題)。
    任何一段抓失敗都容忍跳過,不影響主流程。"""
    lines = [f"資料時點:{_tpe_now():%Y-%m-%d %H:%M} (台北時間)"]

    try:
        from market import data as mkt
        rows = mkt.indices()
        if rows:
            lines.append("\n【今日市場快照(六大指數/匯率)】")
            for r in rows:
                arrow = "▲" if r["change_pct"] > 0 else ("▼" if r["change_pct"] < 0 else "–")
                lines.append(f"- {r['name']}:{r['price']:,} {arrow}{r['change_pct']:+.2f}%")
    except Exception as e:
        print(f"[ai] market snapshot failed: {e}", flush=True)

    if include_news:
        try:
            from market import research as rsh
            heads = []
            for cat in ("tw_macro", "stock_report", "tw_stock"):
                for it in rsh.fetch_cnyes(cat, limit=4):
                    heads.append(f"- [{it['category']}] {it['title']}")
            if heads:
                lines.append("\n【近期財經新聞標題(僅標題,供你掌握輿情方向)】")
                lines.extend(heads[:12])
        except Exception as e:
            print(f"[ai] news headlines failed: {e}", flush=True)

    return "\n".join(lines)


def _parse_card(raw: str) -> dict:
    """從模型輸出抽出 JSON 卡片;容忍 ``` 包裹或前後雜訊。"""
    if not raw:
        return dict(_FALLBACK)
    txt = raw.strip()
    # 去掉 ```json ... ``` 包裹
    if txt.startswith("```"):
        txt = re.sub(r"^```[a-zA-Z]*\n?", "", txt)
        txt = re.sub(r"\n?```$", "", txt).strip()
    # 抓第一個 { 到最後一個 }
    i, j = txt.find("{"), txt.rfind("}")
    if i != -1 and j != -1 and j > i:
        txt = txt[i : j + 1]
    try:
        card = json.loads(txt)
        if not isinstance(card, dict):
            raise ValueError("not an object")
    except Exception as e:
        print(f"[ai] JSON parse failed: {e}; raw head: {raw[:160]}", flush=True)
        fb = dict(_FALLBACK)
        fb["title"] = raw.strip()[:120] or fb["title"]
        return fb
    # 正規化欄位
    card.setdefault("type", "simple")
    if card["type"] not in ("recommendation", "analysis", "simple"):
        card["type"] = "simple"
    pts = card.get("points")
    if isinstance(pts, str):
        card["points"] = [pts]
    elif not isinstance(pts, list):
        card["points"] = []
    for k in ("title", "stance", "market", "instrument", "instrument_desc",
              "entry", "risk", "note"):
        v = card.get(k)
        if v is not None and not isinstance(v, str):
            card[k] = str(v)
    card.setdefault("title", "")
    return card


def ask(user_id: str, user_msg: str, inject_market: bool = True, max_tokens: int = 1500):
    """呼叫 Claude 回答。帶入該使用者的對話記憶。
    回傳 (card_dict, None) 或 (None, error_code)。"""
    if not available():
        return None, "AI_DISABLED"

    system = SYSTEM.format(org=Config.ORG_NAME)
    if inject_market:
        ctx = build_market_context()
        if ctx:
            system = f"{system}\n\n===== 即時參考資料 =====\n{ctx}"

    messages = list(_history(user_id))  # 記憶(不含本次)
    messages.append({"role": "user", "content": user_msg})

    try:
        r = requests.post(
            _API,
            headers={
                "x-api-key": Config.ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": Config.ANTHROPIC_MODEL,
                "max_tokens": max_tokens,
                "system": system,
                "messages": messages,
            },
            timeout=45,
        )
        if r.status_code != 200:
            print(f"[ai] {r.status_code}: {r.text[:300]}", flush=True)
            return None, f"HTTP_{r.status_code}"
        data = r.json()
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        return _parse_card("".join(parts).strip()), None
    except Exception as e:
        print(f"[ai] exception: {e}", flush=True)
        return None, str(e)[:120]
