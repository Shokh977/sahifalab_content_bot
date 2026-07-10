"""Rotating soft CTAs appended to channel posts.

Edit CTA_POOL to point at real Sahifalab course/app URLs — these are
placeholders. Rotation state (which index is next) persists in
bot_settings so it survives restarts/deploys.
"""
import asyncpg

from bot.cta.utm import build_utm_link
from bot.db.repo import settings as settings_repo

CTA_POOL = [
    {"text": "📱 Sahifalab ilovasini yuklab oling", "path": "/app", "campaign": "cta_app"},
    {"text": "🎓 Sahifalab kurslarini ko'ring", "path": "/courses", "campaign": "cta_courses"},
]


async def next_cta(pool: asyncpg.Pool) -> tuple[str, str | None]:
    """Returns (cta_line, utm_campaign), advancing the rotation. cta_line is
    "" and utm_campaign is None if CTA_POOL is empty."""
    if not CTA_POOL:
        return "", None
    index = await settings_repo.get_cta_rotation_index(pool)
    cta = CTA_POOL[index % len(CTA_POOL)]
    await settings_repo.set(pool, "cta_rotation_index", (index + 1) % len(CTA_POOL))
    link = build_utm_link(cta["path"], campaign=cta["campaign"])
    return f"{cta['text']}: {link}", cta["campaign"]
