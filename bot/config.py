import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    CHANNEL_ID: int = 0
    ADMIN_TELEGRAM_IDS: list[int] = field(default_factory=list)

    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    SCRIPT: str = os.getenv("SCRIPT", "latin")  # latin | cyrillic
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Tashkent")

    POSTING_WINDOWS: list[str] = field(default_factory=list)  # ["09:00", "19:00"]
    FETCH_INTERVAL_HOURS: float = float(os.getenv("FETCH_INTERVAL_HOURS", "4"))
    RELEVANCE_THRESHOLD: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.15"))
    QUOTE_DRAFT_COOLDOWN_HOURS: float = float(os.getenv("QUOTE_DRAFT_COOLDOWN_HOURS", "20"))

    UTM_BASE_URL: str = os.getenv("UTM_BASE_URL", "https://sahifalab.uz")
    UTM_SOURCE: str = os.getenv("UTM_SOURCE", "telegram")
    UTM_MEDIUM: str = os.getenv("UTM_MEDIUM", "channel_post")

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    def __post_init__(self):
        channel_id_raw = os.getenv("CHANNEL_ID", "0").strip()
        try:
            self.CHANNEL_ID = int(channel_id_raw)
        except ValueError:
            self.CHANNEL_ID = 0

        admin_raw = os.getenv("ADMIN_TELEGRAM_IDS", "")
        self.ADMIN_TELEGRAM_IDS = [
            int(x.strip()) for x in admin_raw.split(",") if x.strip().isdigit()
        ]

        windows_raw = os.getenv("POSTING_WINDOWS", "09:00,19:00")
        self.POSTING_WINDOWS = [w.strip() for w in windows_raw.split(",") if w.strip()]

        self.SCRIPT = self.SCRIPT.strip().lower()
        if self.SCRIPT not in ("latin", "cyrillic"):
            self.SCRIPT = "latin"


settings = Settings()
