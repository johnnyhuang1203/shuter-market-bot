"""訊息路由 —— 樹德市場觀察室。
自然語言問題 → Claude 市場諮詢;另保留幾個快速指令。
所有回覆用 reply API(免費,不耗推播額度)。
"""
import re

from config import Config

_SYM_RE = re.compile(r"^[\^A-Za-z0-9=.\-]{1,12}$")

WELCOME = (
    "您好,歡迎使用「{bot}」。\n"
    "我是 {org} 為經營層準備的市場觀察助理,可以隨時為您解讀市場方向。\n"
    "───────────\n"
    "您可以直接用口語問我,例如:\n"
    "・「最近台股怎麼看?」\n"
    "・「美股這波修正的原因是什麼?」\n"
    "・「半導體產業現在的趨勢?」\n"
    "・「新台幣升值對出口的影響?」\n"
    "───────────\n"
    "也可以用快速指令(輸入「幫助」看全部)。\n"
    "※本助理提供市場資訊與趨勢參考,非投資建議。"
)

HELP = (
    "📌 {bot} 使用說明\n"
    "───────────\n"
    "【直接問我(建議)】\n"
    "用口語問市場方向、總經、產業趨勢、匯率利率,例如:\n"
    "「台股接下來要注意什麼?」\n"
    "\n【快速指令】\n"
    "大盤 → 六大指數即時行情\n"
    "分析 2330 → 個股七指標多空判讀\n"
    "2330 → 查個股即時報價(台股直接輸代號)\n"
    "報告 → 最新財經研報/晨訊\n"
    "我的ID → 顯示您的 LINE ID\n"
    "───────────\n"
    "※市場資訊與趨勢僅供參考,非投資建議。"
)

DENY = (
    "您好,「{bot}」目前為 {org} 指定主管專用。\n"
    "如需開通,請將以下您的 ID 提供給管理者:\n{uid}"
)


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
    lines += ["", "※技術指標僅供參考,非投資建議。"]
    return "\n".join(lines)


def _fmt_indices() -> str:
    from market import data as mkt
    rows = mkt.indices()
    if not rows:
        return "指數資料暫時取不到,請稍後再試。"
    out = ["🌏 今日大盤"]
    for r in rows:
        arrow = "▲" if r["change_pct"] > 0 else ("▼" if r["change_pct"] < 0 else "–")
        out.append(f"{r['name']} {r['price']:,} {arrow}{r['change_pct']:+.2f}%")
    out.append("\n想聽方向解讀,直接問我即可。")
    return "\n".join(out)


def _fmt_research() -> str:
    from market import research as rsh
    rows = rsh.fetch_cnyes("stock_report", limit=5)
    if not rows:
        return "研報暫時取不到,請稍後再試。"
    out = ["📑 最新研報 / 晨訊"]
    for r in rows[:5]:
        out.append(f"・{r['title']}\n{r['url']}")
    return "\n".join(out)


def _ai_answer(msg: str) -> str:
    from ai import ask
    ans, err = ask(msg)
    if err == "AI_DISABLED":
        return "市場諮詢功能尚未啟用(需設定 ANTHROPIC_API_KEY)。您仍可使用「大盤」「分析 代號」等指令。"
    if err:
        return "抱歉,剛剛連線市場資料時出了點狀況,請稍後再問一次。"
    return ans


def handle_text(user_id: str, text: str) -> str:
    """回傳要回覆的文字。白名單、指令、AI 都在這裡分流。"""
    text = (text or "").strip()

    # 取自己的 ID(任何人都能用,方便收集白名單)
    if text.lower() in ("我的id", "myid", "id", "我的 id"):
        return f"您的 LINE ID:\n{user_id}"

    # 白名單(未設定時放行;設定後只放行名單內)
    if not Config.is_allowed(user_id):
        return DENY.format(bot=Config.BOT_NAME, org=Config.ORG_NAME, uid=user_id)

    up = text.upper()

    if text in ("幫助", "說明", "help", "?", "指令") or up == "HELP":
        return HELP.format(bot=Config.BOT_NAME)
    if text in ("報告", "晨訊", "研報"):
        return _fmt_research()
    if text in ("大盤", "指數", "行情"):
        return _fmt_indices()
    if up.startswith("分析"):
        sym = up.replace("分析", "", 1).strip()
        if sym and _SYM_RE.match(sym):
            return _fmt_analysis(sym)
        return "用法:分析 2330(台股代號直接輸入)"
    # 純代號(數字或英文代號)→ 報價;但太短的中文不會落這裡
    if _SYM_RE.match(up) and (up.isdigit() or up.isascii()):
        return _fmt_quote(up)

    # 其餘一律交給 AI 做市場方向諮詢
    return _ai_answer(text)
