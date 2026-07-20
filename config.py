"""環境變數集中管理(樹德市場諮詢 Bot)。"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ---- LINE Messaging API ----
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET", "")

    # ---- AI (Anthropic Claude) ----
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    # 沿用 wealthbot 的預設模型;可在環境變數覆寫成更新版本
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    # ---- 語音轉文字 (Groq Whisper,可選) ----
    # 有填才會處理 LINE 語音訊息;留空則語音會請使用者改用打字/手機口述。
    # 免費申請:https://console.groq.com/keys
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
    GROQ_STT_MODEL = os.environ.get("GROQ_STT_MODEL", "whisper-large-v3")

    # ---- 多輪對話記憶 ----
    # 每位使用者在記憶體中保留最近 N 輪(一問一答為一輪)。程序重啟即清空。
    MEMORY_TURNS = int(os.environ.get("MEMORY_TURNS", "8"))

    # ---- LIFF(內嵌聊天畫面「AI 請直說」)----
    # 在 LINE 主控台建立 LIFF app 後取得的 ID,注入到 /liff 網頁供 LIFF SDK 初始化。
    LIFF_ID = os.environ.get("LIFF_ID", "")

    # ---- 使用者白名單 ----
    # 逗號分隔的 LINE userId。留空 = 尚未設定(setup 模式,所有人可用且會在 log 印出 userId,
    # 方便你日後收集主管的 ID 後填回來)。填了之後就只有名單內的人能用。
    ALLOWED_USER_IDS = [
        u.strip() for u in os.environ.get("ALLOWED_USER_IDS", "").split(",") if u.strip()
    ]

    # 服務對象顯示名(僅用於文案)
    ORG_NAME = os.environ.get("ORG_NAME", "樹德企業")
    BOT_NAME = os.environ.get("BOT_NAME", "樹德市場觀察室")

    APP_ENV = os.environ.get("APP_ENV", "prod")

    @classmethod
    def ai_ready(cls) -> bool:
        return bool(cls.ANTHROPIC_API_KEY)

    @classmethod
    def stt_ready(cls) -> bool:
        return bool(cls.GROQ_API_KEY)

    @classmethod
    def whitelist_active(cls) -> bool:
        return len(cls.ALLOWED_USER_IDS) > 0

    @classmethod
    def is_allowed(cls, user_id: str) -> bool:
        # 白名單未設定時一律放行(setup 模式);設定後只放行名單內
        if not cls.whitelist_active():
            return True
        return user_id in cls.ALLOWED_USER_IDS
