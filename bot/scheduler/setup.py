"""Builds and starts the AsyncIOScheduler with all recurring jobs."""
import logging

import pytz
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from bot.config import settings
from bot.scheduler import jobs

logger = logging.getLogger(__name__)


def build_scheduler(bot: Bot) -> AsyncIOScheduler:
    tz = pytz.timezone(settings.TIMEZONE)
    scheduler = AsyncIOScheduler(timezone=tz)

    scheduler.add_job(
        jobs.job_ingest_and_draft,
        trigger=IntervalTrigger(hours=settings.FETCH_INTERVAL_HOURS),
        args=[bot],
        id="ingest_and_draft",
        max_instances=1,
        coalesce=True,
    )

    for window in settings.POSTING_WINDOWS:
        try:
            hour, minute = (int(x) for x in window.split(":"))
        except ValueError:
            logger.warning("Skipping invalid POSTING_WINDOWS entry: %r", window)
            continue
        scheduler.add_job(
            jobs.job_post_from_queue,
            trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
            args=[bot],
            id=f"posting_window_{window.replace(':', '')}",
            max_instances=1,
            coalesce=True,
        )

    scheduler.add_job(
        jobs.job_post_scheduled_due,
        trigger=IntervalTrigger(minutes=5),
        args=[bot],
        id="scheduled_due_sweep",
        max_instances=1,
        coalesce=True,
    )

    scheduler.add_job(
        jobs.job_reminder_stale,
        trigger=CronTrigger(hour=8, minute=0, timezone=tz),
        args=[bot],
        id="stale_draft_reminder",
        max_instances=1,
        coalesce=True,
    )

    return scheduler
