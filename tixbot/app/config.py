import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv


# Load .env from the project root (so `python -m app.bot` works without exporting vars)
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    base_url: str
    admin_link_secret: str
    database_url: str
    # External DB that holds the canonical points balance and other user fields.
    # Example: mysql+asyncmy://user:pass@127.0.0.1:3306/tgbot?charset=utf8mb4
    tgbot_database_url: str
    # Fixed group/supergroup to publish raffles to.
    target_chat_id: int
    # Timezone for display/logic.
    tz_name: str


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()

    admin_ids_raw = os.getenv("ADMIN_IDS", "").strip()
    admin_ids = {int(x) for x in admin_ids_raw.split(",") if x.strip().isdigit()}

    base_url = os.getenv("BASE_URL", "http://127.0.0.1:8000").strip().rstrip("/")
    admin_link_secret = os.getenv("ADMIN_LINK_SECRET", "").strip()
    database_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./tixbot_dev.db").strip()

    # External points DB (tgbot): supports either
    # - TGBOT_DATABASE_URL (preferred)
    # - TG_DATABASE_URL (legacy)
    tgbot_database_url = os.getenv("TGBOT_DATABASE_URL", "").strip()
    legacy_tg_database_url = os.getenv("TG_DATABASE_URL", "").strip()
    if tgbot_database_url and legacy_tg_database_url and (tgbot_database_url != legacy_tg_database_url):
        print(
            "[tixbot][config] WARN: TGBOT_DATABASE_URL and TG_DATABASE_URL are both set and differ. "
            "Using TGBOT_DATABASE_URL."
        )
    if not tgbot_database_url:
        tgbot_database_url = legacy_tg_database_url

    if not tgbot_database_url:
        # Best-effort: replace last path segment (db name) with 'tgbot'
        if "/" in database_url:
            head, tail = database_url.rsplit("/", 1)
            if "?" in tail:
                _, qs = tail.split("?", 1)
                tgbot_database_url = f"{head}/tgbot?{qs}"
            else:
                tgbot_database_url = f"{head}/tgbot"

    if not tgbot_database_url:
        # In dev, fall back so app can start.
        tgbot_database_url = database_url

    target_chat_id_raw = os.getenv("TARGET_CHAT_ID", "2406607330").strip()
    try:
        target_chat_id = int(target_chat_id_raw)
    except Exception:
        target_chat_id = 2406607330

    tz_name = os.getenv("TZ_NAME", "Asia/Shanghai").strip() or "Asia/Shanghai"

    if not admin_link_secret:
        # For dev convenience only. In production, MUST set a strong secret.
        admin_link_secret = "dev_secret_change_me"

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        base_url=base_url,
        admin_link_secret=admin_link_secret,
        database_url=database_url,
        tgbot_database_url=tgbot_database_url,
        target_chat_id=target_chat_id,
        tz_name=tz_name,
    )
