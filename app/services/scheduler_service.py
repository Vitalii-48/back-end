# app/services/scheduler_service.py
import logging
from sqlalchemy.ext.asyncio import async_sessionmaker
from app.repositories.scheduler_repository import SchedulerRepository
from app.repositories.notification_repository import NotificationRepository

logger = logging.getLogger(__name__)


class SchedulerService:
    def __init__(self, session_factory: async_sessionmaker):
        # Оскільки APScheduler запускає таски у фоні поза FastAPI-запитом,
        # нам потрібно самостійно створювати сесії через session_factory.
        self.session_factory = session_factory

    async def check_and_notify_missing_quiz_participants(self) -> None:
        """Сканує базу та створює сповіщення-нагадування для користувачів."""
        logger.info("Запуск фонової перевірки проходження квізів...")

        async with self.session_factory() as session:
            scheduler_repo = SchedulerRepository(session)
            notification_repo = NotificationRepository(session)

            # 1. Отримуємо список "боржників"
            missed_records = await scheduler_repo.get_users_who_missed_quizzes()

            if not missed_records:
                logger.info("Усі користувачі вчасно пройшли квізи. Нагадування не потрібні.")
                return

            logger.info(f"Знайдено {len(missed_records)} пропущених квізів. Надсилаємо сповіщення...")

            # 2. Формуємо весь список сповіщень одразу (без циклічних запитів до БД)
            notifications_data = [
                {
                    "user_id": user_id,
                    "message": (
                        f"Нагадування: Ви не пройшли квіз '{quiz_title}' "
                        f"у компанії '{company_name}' за останні 24 години!"
                    ),
                }
                for user_id, company_name, quiz_title in missed_records
            ]

            # 3. Один batch-insert + один commit (усередині create_many)
            await notification_repo.create_many(notifications_data)
            logger.info("Усі сповіщення-нагадування успішно збережено в БД.")