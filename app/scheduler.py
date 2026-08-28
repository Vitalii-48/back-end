# app/scheduler.py
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def configure_scheduler(session_factory: async_sessionmaker) -> None:
    """
    Конфігурує та додає фонові завдання до планувальника.
    """
    scheduler_service = SchedulerService(session_factory=session_factory)

    scheduler.add_job(
        scheduler_service.check_and_notify_missing_quiz_participants,
        CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="quiz_reminder_daily",
        replace_existing=True
    )

    logger.info("APScheduler успішно налаштовано. Додано таск: quiz_reminder_daily")