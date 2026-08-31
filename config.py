import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _get_admin_ids() -> list[int]:
    raw = os.getenv("ADMIN_IDS", "")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: list[int] = field(default_factory=_get_admin_ids)

    # Majburiy obuna uchun kanal (masalan @sizning_kanal)
    required_channel: str = os.getenv("REQUIRED_CHANNEL", "")

    # Yangi qism chiqqanda avtomatik post joylanadigan asosiy kanal
    main_channel: str = os.getenv("MAIN_CHANNEL", "")

    # Videolar saqlanadigan yashirin kanal (bot admin bo'lishi shart), masalan -1001234567890
    storage_channel_id: int = int(os.getenv("STORAGE_CHANNEL_ID", "0") or 0)

    # Local Bot API server manzili (limitlarsiz ishlash uchun)
    bot_api_base: str = os.getenv("BOT_API_BASE", "https://api.telegram.org")

    # Mini App (WebApp) ning ochiq (public) manzili
    webapp_url: str = os.getenv("WEBAPP_URL", "")

    database_path: str = os.getenv("DATABASE_PATH", "anime_bot.db")


config = Config()
