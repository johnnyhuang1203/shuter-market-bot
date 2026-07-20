"""樹德市場觀察室 —— LINE Messaging API webhook 服務 (Flask)。
- /health          健康檢查
- /webhook         LINE 事件入口(驗簽 → 分流 → reply)
文字訊息一律用 reply API 回覆(免費,不佔用推播額度)。
"""
import base64
import hashlib
import hmac

import requests
from flask import Flask, request, jsonify

from config import Config
from bot import handle_text, WELCOME

app = Flask(__name__)


def _valid_signature(req) -> bool:
    """驗證 X-Line-Signature。未設定 secret 時放行(僅供本機測試)。"""
    if not Config.LINE_CHANNEL_SECRET:
        return True
    sig = req.headers.get("X-Line-Signature", "")
    digest = hmac.new(
        Config.LINE_CHANNEL_SECRET.encode(), req.get_data(), hashlib.sha256
    ).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), sig)


def _reply(reply_token: str, text: str):
    if not Config.LINE_CHANNEL_ACCESS_TOKEN:
        print("[webhook] no access token; would reply:", text[:100], flush=True)
        return
    try:
        requests.post(
            "https://api.line.me/v2/bot/message/reply",
            headers={
                "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}",
                "Content-Type": "application/json",
            },
            json={
                "replyToken": reply_token,
                "messages": [{"type": "text", "text": text[:4900]}],
            },
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
        "whitelist_active": Config.whitelist_active(),
        "allowed_count": len(Config.ALLOWED_USER_IDS),
    })


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
                    _reply(token, WELCOME.format(bot=Config.BOT_NAME, org=Config.ORG_NAME))
                continue

            # 只處理文字訊息
            if etype != "message" or (ev.get("message") or {}).get("type") != "text":
                continue

            text = ev["message"].get("text", "")
            # 這行會印在 Render 的 Logs,方便你日後查任何使用者的 userId
            print(f"[webhook] text from {uid}: {text}", flush=True)

            reply = handle_text(uid, text)
            if reply and token:
                _reply(token, reply)
        except Exception as e:
            print(f"[webhook] handler error: {e}", flush=True)

    return jsonify({"ok": True})


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")))
