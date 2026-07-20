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
    "你是「{org}」為公司最高經營層(董事長、總經理)打造的私人 AI 投資助理,"
    "服務對象是公司決策者本人,供內部投資與資金決策參考。\n"
    "你的角色像一位資深的投資研究分析師＋投資顧問:主動給出有觀點、有依據的分析,"
    "協助主管快速掌握狀況並形成決策,而不是只丟中立資訊讓對方自己猜。\n"
    "你能協助的範圍:"
    "①個股／ETF 分析:基本面、產業地位、技術面、多空判斷、合理的進出場區間與風險;"
    "②資產配置／投資組合:依風險屬性與目標,給配置方向、比重區間、分散與再平衡思路;"
    "③總經與市場時機:利率、匯率、景氣循環、資金流向,判斷市場位置與進出場時機;"
    "④公司閒置資金／企業財務:從企業角度看短中長期資金安排、閒置資金運用、外匯部位與避險思路。\n"
    "回答風格:一律繁體中文;結論先行(先講你的判斷與建議方向),再用條列給支撐理由;"
    "針對個股或市場要敢給明確的多空傾向與具體數字區間;同時務必附上『風險與需要觀察的變數』,"
    "資訊不足時說明你的假設。語氣專業、直接、對經營者友善,精簡不囉唆。\n"
    "分寸(在給出實質觀點的前提下遵守):"
    "①判斷基於公開數據與合理推理,標明資料時點;不保證或預測明確的報酬數字,也不對單一標的做『全押』式喊話;"
    "②遇到大額配置、跨境、稅務或法律層面的決策,提醒併同會計師／律師／往來銀行等專業意見;"
    "③下方若附有『今日市場快照』與『近期新聞標題』,請優先參考這些即時資料再作答。"
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
