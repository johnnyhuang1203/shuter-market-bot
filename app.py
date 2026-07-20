"""樹德投資助理 —— LINE Messaging API webhook 服務 (Flask)。
- /health          健康檢查
- /webhook         LINE 事件入口(驗簽 → 分流 → reply)
文字/語音問題 → AI 對話(帶記憶,回圖卡);一律用 reply API(免費,不佔推播額度)。
"""
import base64
import hashlib
import hmac
import os

import requests
from flask import Flask, request, jsonify, Response

from config import Config
from bot import handle_text, WELCOME

app = Flask(__name__)

_LIFF_HTML_PATH = os.path.join(os.path.dirname(__file__), "static", "liff.html")


def _valid_signature(req) -> bool:
    """驗證 X-Line-Signature。未設定 secret 時放行(僅供本機測試)。"""
    if not Config.LINE_CHANNEL_SECRET:
        return True
    sig = req.headers.get("X-Line-Signature", "")
    digest = hmac.new(
        Config.LINE_CHANNEL_SECRET.encode(), req.get_data(), hashlib.sha256
    ).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), sig)


def _as_message(m):
    """把字串或 dict 正規化成 LINE message 物件。"""
    if isinstance(m, str):
        return {"type": "text", "text": m[:4900]}
    return m


def _reply(reply_token: str, messages):
    """messages 可為單一(str/dict)或 list。LINE 一次最多 5 則。"""
    if not Config.LINE_CHANNEL_ACCESS_TOKEN:
        print("[webhook] no access token; would reply:", str(messages)[:120], flush=True)
        return
    if not isinstance(messages, list):
        messages = [messages]
    payload = [_as_message(m) for m in messages if m][:5]
    if not payload:
        return
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={"replyToken": reply_token, "messages": payload},
            timeout=10,
        )
    except Exception as e:
        print(f"[webhook] reply failed: {e}", flush=True)


@app.route("/")
@app.route("/health")
def health():
    return jsonify({
        "ok": True,
        "service": Config.BOT_NAME,
        "ai": Config.ai_ready(),
        "stt": Config.stt_ready(),
        "whitelist_active": Config.whitelist_active(),
        "allowed_count": len(Config.ALLOWED_USER_IDS),
    })


def _handle_audio(uid: str, message_id: str) -> list:
    """語音訊息 → 聽打 → 當文字問 AI。前面附一則『我聽到』回饋。"""
    from transcribe import from_message_id
    text, err = from_message_id(message_id)
    if err == "NO_STT":
        return [{"type": "text", "text": (
            "目前尚未開通語音聽打。您可以:\n"
            "① 直接打字問我;或\n"
            "② 用手機鍵盤上的麥克風『口述』(它會把語音變文字送出),一樣能用。"
        )}]
    if err or not text:
        return [{"type": "text", "text": "抱歉,這段語音我沒聽清楚,方便再說一次或改用打字嗎?"}]
    heard = {"type": "text", "text": f"🎙️ 我聽到:「{text}」"}
    return [heard] + handle_text(uid, text)


# ============ LIFF：「AI 請直說」內嵌聊天畫面 ============

@app.route("/liff")
def liff_page():
    """送出聊天網頁(SHUTER AI 投資助理),LIFF_ID 注入給前端 SDK。"""
    try:
        with open(_LIFF_HTML_PATH, encoding="utf-8") as f:
            html = f.read()
    except Exception as e:
        print(f"[liff] page read failed: {e}", flush=True)
        return "LIFF page not available.", 404
    html = html.replace("__LIFF_ID__", Config.LIFF_ID or "")
    html = html.replace("__ORG_NAME__", Config.ORG_NAME)
    html = html.replace("__STT_READY__", "true" if Config.stt_ready() else "false")
    return Response(html, mimetype="text/html; charset=utf-8")


@app.route("/api/ask", methods=["POST"])
def api_ask():
    """LIFF 文字問答 → 結構化卡片。與 LINE 聊天室共用同一 userId 記憶。"""
    data = request.get_json(silent=True) or {}
    uid = (data.get("userId") or "").strip() or "liff-anon"
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"ok": False, "error": "empty"}), 400
    from ai import ask_and_remember
    from flex import card_to_text
    card, err = ask_and_remember(uid, msg)
    if err:
        return jsonify({"ok": False, "error": err}), 200
    return jsonify({"ok": True, "card": card, "text": card_to_text(card)})


@app.route("/api/ask_audio", methods=["POST"])
def api_ask_audio():
    """LIFF 語音錄音 → Groq 聽打 → 問答。回傳逐字稿 + 卡片。"""
    uid = (request.form.get("userId") or "").strip() or "liff-anon"
    f = request.files.get("audio")
    if not f:
        return jsonify({"ok": False, "error": "no_audio"}), 400
    fname = f.filename or "voice.webm"
    ctype = f.mimetype or "audio/webm"
    from transcribe import transcribe
    text, terr = transcribe(f.read(), filename=fname, content_type=ctype)
    if terr == "NO_STT":
        return jsonify({"ok": False, "error": "NO_STT"}), 200
    if terr or not text:
        return jsonify({"ok": False, "error": terr or "empty_transcript"}), 200
    from ai import ask_and_remember
    from flex import card_to_text
    card, err = ask_and_remember(uid, text)
    if err:
        return jsonify({"ok": False, "error": err, "transcript": text}), 200
    return jsonify({"ok": True, "transcript": text, "card": card, "text": card_to_text(card)})


@app.route("/api/reset", methods=["POST"])
def api_reset():
    """LIFF「新對話」→ 清掉該使用者的對話記憶。"""
    data = request.get_json(silent=True) or {}
    uid = (data.get("userId") or "").strip()
    if uid:
        import memory
        memory.clear(uid)
    return jsonify({"ok": True})


@app.route("/webhook", methods=["POST"])
def webhook():
    if not _valid_signature(request):
        return jsonify({"ok": False}), 403
    body = request.get_json(silent=True) or {}

    for ev in body.get("events", []):
        try:
            etype = ev.get("type")
            uid = (ev.get("source") or {}).get("userId", "")
            token = ev.get("replyToken")

            # 加入好友 → 歡迎詞
            if etype == "follow":
                print(f"[webhook] follow from {uid}", flush=True)
                if token:
                    _reply(token, WELCOME.format(org=Config.ORG_NAME))
                continue

            if etype != "message":
                continue

            mtype = (ev.get("message") or {}).get("type")

            if mtype == "text":
                text = ev["message"].get("text", "")
                print(f"[webhook] text from {uid}: {text}", flush=True)
                msgs = handle_text(uid, text)
                if msgs and token:
                    _reply(token, msgs)

            elif mtype == "audio":
                mid = ev["message"].get("id", "")
                print(f"[webhook] audio from {uid}: {mid}", flush=True)
                msgs = _handle_audio(uid, mid)
                if msgs and token:
                    _reply(token, msgs)

            # 其他型別(貼圖/圖片等)略過
        except Exception as e:
            print(f"[webhook] handler error: {e}", flush=True)

    return jsonify({"ok": True})


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
