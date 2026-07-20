"""Anthropic Claude 封裝 —— 樹德企業經營層「市場方向諮詢」用。
定位與 wealthbot 的理專助理不同:服務對象是公司高階主管(總經理/董事長),
提供台股與全球市場方向、總經、產業趨勢的『參考資訊』,不是投資建議。
合規護欄寫在 system prompt。
"""
import datetime as _dt
import requests

from config import Config

_API = "https://api.anthropic.com/v1/messages"

# 市場諮詢的系統角色與合規底線
SYSTEM = (
    "你是「{org}」為經營層打造的市場觀察助理,服務對象是公司高階主管(總經理、董事長)。"
    "你的任務:用清楚、精簡、決策者看得懂的語言,協助他們掌握台股與全球金融市場的方向、"
    "總體經濟趨勢、產業動態、以及利率與匯率變化,作為經營與資產決策時的『參考資訊』。\n"
    "回答風格:一律用繁體中文;先給重點結論(1-2 句),再用 2-4 點條列支撐;"
    "語氣專業、沉穩、對經營者友善;必要時點出目前的不確定性與後續要觀察的變數。\n"
    "重要界線(務必遵守):"
    "①你提供的是市場資訊與趨勢判讀,不是投資建議;不得叫人買賣特定個股或金融商品、"
    "不承諾或預測明確報酬率;"
    "②涉及個別公司或個人的實際投資決策時,提醒『實際決策請依自身情況並諮詢專業人士』;"
    "③若被問到你沒有即時數據的細節(例如盤中即時價格),說明你手上資料的時點、給趨勢性判讀,"
    "不要編造精確數字。\n"
    "下方可能會附上『今日市場快照』與『近期新聞標題』,若有,請優先參考這些即時資料再作答。"
)


def available() -> bool:
    return Config.ai_ready()


def _tpe_now():
    return _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=8)))


def build_market_context(include_news: bool = True) -> str:
    """組出給 AI 參考的即時市場快照(六大指數 + 近期新聞標題)。
    任何一段抓失敗都容忍跳過,不影響主流程。"""
    lines = []
    lines.append(f"資料時點:{_tpe_now():%Y-%m-%d %H:%M} (台北時間)")

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


def ask(user_msg: str, inject_market: bool = True, max_tokens: int = 1400):
    """呼叫 Claude 回答市場方向問題。回傳 (文字, None) 或 (None, error_code)。"""
    if not available():
        return None, "AI_DISABLED"

    system = SYSTEM.format(org=Config.ORG_NAME)
    content = user_msg
    if inject_market:
        ctx = build_market_context()
        if ctx:
            content = f"{ctx}\n\n【主管的問題】\n{user_msg}"

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
                "messages": [{"role": "user", "content": content}],
            },
            timeout=45,
        )
        if r.status_code != 200:
            print(f"[ai] {r.status_code}: {r.text[:300]}", flush=True)
            return None, f"HTTP_{r.status_code}"
        data = r.json()
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        return "".join(parts).strip(), None
    except Exception as e:
        print(f"[ai] exception: {e}", flush=True)
        return None, str(e)[:120]
