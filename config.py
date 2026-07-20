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
    def whitelist_active(cls) -> bool:
        return len(cls.ALLOWED_USER_IDS) > 0

    @classmethod
    def is_allowed(cls, user_id: str) -> bool:
        # 白名單未設定時一律放行(setup 模式);設定後只放行名單內
        if not cls.whitelist_active():
            return True
        return user_id in cls.ALLOWED_USER_IDS
