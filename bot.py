"""訊息路由 —— 樹德投資助理。

以「對話」為主:主管用口語(打字或語音)直接問,AI 帶記憶回答並以圖卡呈現。
另保留幾個快速指令。所有回覆用 reply API(免費,不佔推播額度)。

handle_text() 回傳「LINE 訊息物件的 list」(每則是 text 或 flex),由 app.py 送出。
"""
import re

from config import Config
import memory

_SYM_RE = re.compile(r"^[\^A-Za-z0-9=.\-]{1,12}$")

WELCOME = (
    "您好,我是 {org} 為經營層準備的 AI 投資助理 🤝\n"
    "把我當隨身的投資研究顧問 —— 用口語直接問就好,打字或按語音都行,我會記得我們剛聊到哪,答覆用圖卡呈現。\n"
    "───────────\n"
    "可以這樣問我:\n"
    "・「現在適合布局哪個市場、哪個商品?」\n"
    "・「這筆閒置資金該怎麼配置?」\n"
    "・「台積電現在可以進場嗎?」\n"
    "・(接著追問)「那風險呢?」\n"
    "───────────\n"
    "輸入「幫助」看更多用法;想重新開始一個話題輸入「重新開始」。\n"
    "※內部決策參考;實際交易與大額配置請併專業意見。"
)

HELP = (
    "📌 {org} · AI 投資助理 使用說明\n"
    "───────────\n"
    "【直接問我(主要用法)】\n"
    "打字或按語音,用口語問市場、個股、資產配置、公司資金安排。\n"
    "我會記得前後文,可以直接追問「那這個呢?」「風險?」\n"
    "「現在該做什麼市場/商品」這類問題,我會給你一張建議圖卡。\n"
    "\n【快速指令】\n"
    "大盤 → 六大指數即時行情(圖卡)\n"
    "分析 2330 → 個股七指標多空判讀\n"
    "2330 → 查個股即時報價(台股直接輸代號)\n"
    "報告 → 最新財經研報/晨訊\n"
    "重新開始 → 清掉目前對話記憶,換新話題\n"
    "我的ID → 顯示您的 LINE ID\n"
    "───────────\n"
    "※內部決策參考;實際交易與大額配置請併專業意見。"
)

DENY = (
    "您好,「{org} AI 投資助理」目前為指定主管專用。\n"
    "如需開通,請將以下您的 ID 提供給管理者:\n{uid}"
)


def _text(s: str) -> dict:
    return {"type": "text", "text": (s or "")[:4900]}


def _fmt_quote(sym: str) -> str:
    from market import data as mkt
    d = mkt.quote(sym)
    if not d:
        return f"查無 {sym} 的報價。台股請直接輸入代號(不用 .TW),日股加 .T,美股用英文代號。"
    arrow = "▲" if d["change_pct"] > 0 else ("▼" if d["change_pct"] < 0 else "–")
    return f"📈 {d['symbol']}\n{d['price']:,} {arrow} {d['change_pct']:+.2f}%"


def _fmt_analysis(sym: str) -> str:
    from market import analysis as ana
    r = ana.analyze(sym)
    if not r:
        return f"查無 {sym} 的資料,無法分析。"
    ic = {"bull": "🔴", "bear": "🟢", "neutral": "⚪"}  # 台股慣例:紅多綠空
    lines = [
        f"📊 {r['symbol']} · {r['price']:,}",
        f"綜合判讀:{r['summary']['verdict']} "
        f"(多 {r['summary']['bulls']} / 空 {r['summary']['bears']})",
        "",
    ]
    lines += [f"{ic.get(x['signal'], '⚪')} {x['name']}:{x['note']}" for x in r["indicators"]]
    lines += ["", "想聽多空觀點與進出場思路,直接問我這檔即可。"]
    return "\n".join(lines)


def _indices_message():
    from market import data as mkt
    rows = mkt.indices()
    if not rows:
        return _text("指數資料暫時取不到,請稍後再試。")
    from flex import indices_message
    return indices_message(rows)


def _fmt_research() -> str:
    from market import research as rsh
    rows = rsh.fetch_cnyes("stock_report", limit=5)
    if not rows:
        return "研報暫時取不到,請稍後再試。"
    out = ["📑 最新研報 / 晨訊"]
    for r in rows[:5]:
        out.append(f"・{r['title']}\n{r['url']}")
    return "\n".join(out)


def _ai_messages(user_id: str, msg: str) -> list:
    from ai import ask_and_remember
    from flex import card_to_flex
    card, err = ask_and_remember(user_id, msg)
    if err == "AI_DISABLED":
        return [_text("投資助理功能尚未啟用(需設定 ANTHROPIC_API_KEY)。您仍可使用「大盤」「分析 代號」等指令。")]
    if err:
        return [_text("抱歉,剛剛連線市場資料時出了點狀況,請稍後再問一次。")]
    return [card_to_flex(card)]


def handle_text(user_id: str, text: str) -> list:
    """回傳要送出的 LINE 訊息物件 list。白名單、指令、AI 都在這裡分流。"""
    text = (text or "").strip()

    # 取自己的 ID(任何人都能用,方便收集白名單)
    if text.lower() in ("我的id", "myid", "id", "我的 id"):
        return [_text(f"您的 LINE ID:\n{user_id}")]

    # 白名單(未設定時放行;設定後只放行名單內)
    if not Config.is_allowed(user_id):
        return [_text(DENY.format(org=Config.ORG_NAME, uid=user_id))]

    if not text:
        return [_text("請直接用口語問我,或輸入「幫助」看用法。")]

    up = text.upper()

    if text in ("幫助", "說明", "help", "?", "指令") or up == "HELP":
        return [_text(HELP.format(org=Config.ORG_NAME))]
    if text in ("重新開始", "清除記憶", "清除", "忘記", "重來", "reset", "RESET"):
        memory.clear(user_id)
        return [_text("好的,已清掉目前的對話記憶,我們重新開始。要聊哪個市場或標的?")]
    if text in ("報告", "晨訊", "研報"):
        return [_text(_fmt_research())]
    if text in ("大盤", "指數", "行情"):
        return [_indices_message()]
    if up.startswith("分析"):
        sym = up.replace("分析", "", 1).strip()
        if sym and _SYM_RE.match(sym):
            return [_text(_fmt_analysis(sym))]
        return [_text("用法:分析 2330(台股代號直接輸入)")]
    # 純代號(數字或英文代號)→ 報價
    if _SYM_RE.match(up) and (up.isdigit() or up.isascii()):
        return [_text(_fmt_quote(up))]

    # 其餘一律交給 AI 做對話式諮詢(帶記憶,回圖卡)
    return _ai_messages(user_id, text)
