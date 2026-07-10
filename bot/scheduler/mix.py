"""Weighted pillar selection to keep the posted mix near the 60/30/10
news/tip/quote target over time. Polls and YouTube posts never go through
this — they're admin-timed only (see bot/services/channel_poster.py and
bot/telegram/handlers/approval.py), so they never distort the ratio.
"""
import random

import asyncpg

from bot.db.repo import drafts as drafts_repo
from bot.db.repo import posts as posts_repo
from bot.db.repo import settings as settings_repo

MIX_WINDOW_SIZE = 20
MIX_PILLARS = ("news", "tip", "quote")


async def get_mix_targets(pool: asyncpg.Pool) -> dict[str, float]:
    return await settings_repo.get_mix_targets(pool)


async def get_recent_pillar_counts(pool: asyncpg.Pool, window: int = MIX_WINDOW_SIZE) -> dict[str, int]:
    return await posts_repo.recent_pillar_counts(pool, window)


def compute_weights(targets: dict[str, float], actual_counts: dict[str, int]) -> dict[str, float]:
    total = sum(actual_counts.values()) or 1
    weights = {}
    for pillar in MIX_PILLARS:
        target = targets.get(pillar, 0.0)
        actual_ratio = actual_counts.get(pillar, 0) / total
        deficit = target - actual_ratio
        weights[pillar] = max(0.05, target + deficit * 2)
    return weights


async def pick_next_draft(pool: asyncpg.Pool) -> asyncpg.Record | None:
    targets = await get_mix_targets(pool)
    actual = await get_recent_pillar_counts(pool)
    weights = compute_weights(targets, actual)

    eligible_by_pillar: dict[str, list[asyncpg.Record]] = {}
    for pillar in MIX_PILLARS:
        rows = await drafts_repo.list_eligible_for_pillar(pool, pillar)
        if rows:
            eligible_by_pillar[pillar] = rows

    if not eligible_by_pillar:
        return None

    pillars = list(eligible_by_pillar.keys())
    pillar_weights = [weights[p] for p in pillars]
    chosen_pillar = random.choices(pillars, weights=pillar_weights, k=1)[0]
    return eligible_by_pillar[chosen_pillar][0]
