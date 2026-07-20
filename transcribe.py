"""LINE 語音訊息 → 文字 —— 樹德投資助理。

流程:webhook 收到 audio 訊息 → 用 messageId 下載音檔(LINE content API)→
送 Groq Whisper 聽打成文字 → 交給 AI 當一般問題處理。

Groq 提供免費的 whisper-large-v3(申請免費金鑰即可,無需綁卡):
  https://console.groq.com/keys
未設定 GROQ_API_KEY 時,語音會回一句友善提示,請主管改用打字或手機口述。

註:主管用「手機鍵盤的麥克風口述」本來就會送出文字訊息,不經過這裡,永遠可用。
"""
import requests

from config import Config

_LINE_CONTENT = "https://api-data.line.me/v2/bot/message/{mid}/content"
_GROQ_STT = "https://api.groq.com/openai/v1/audio/transcriptions"


def fetch_audio(message_id: str) -> bytes:
    """從 LINE 下載語音原始位元組(通常為 m4a)。"""
    r = requests.get(
        _LINE_CONTENT.format(mid=message_id),
        headers={"Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}"},
        timeout=30,
    )
    r.raise_for_status()
    return r.content


def transcribe(audio_bytes: bytes):
    """回傳 (文字, None) 或 (None, error_code)。"""
    if not Config.stt_ready():
        return None, "NO_STT"
    try:
        r = requests.post(
            _GROQ_STT,
            headers={"Authorization": f"Bearer {Config.GROQ_API_KEY}"},
            files={"file": ("voice.m4a", audio_bytes, "audio/m4a")},
            data={
                "model": Config.GROQ_STT_MODEL,
                "language": "zh",
                "temperature": "0",
                "response_format": "json",
            },
            timeout=60,
        )
        if r.status_code != 200:
            print(f"[stt] {r.status_code}: {r.text[:200]}", flush=True)
            return None, f"STT_{r.status_code}"
        return (r.json().get("text") or "").strip(), None
    except Exception as e:
        print(f"[stt] exception: {e}", flush=True)
        return None, str(e)[:120]


def from_message_id(message_id: str):
    """一步到位:下載 + 聽打。回傳 (文字, None) 或 (None, error_code)。"""
    if not Config.stt_ready():
        return None, "NO_STT"
    try:
        audio = fetch_audio(message_id)
    except Exception as e:
        print(f"[stt] download failed: {e}", flush=True)
        return None, "DOWNLOAD_FAIL"
    return transcribe(audio)
