 # app/repositories/quiz_cache_repository.py
import json
from uuid import UUID
from datetime import datetime, timezone

import redis.asyncio as redis

TTL_48_HOURS = 48 * 60 * 60

class QuizCacheRepository:
    def __init__(self, redis: redis.Redis):
        self._redis = redis

    async def save_quiz_attempt(
        self,
        user_id: UUID,
        company_id: UUID,
        quiz_id: UUID,
        answers: list[dict],
    ) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()

        # key — унікальний ідентифікатор запису в Redis
        key = f"quiz_attempt:{user_id}:{company_id}:{quiz_id}:{timestamp}"

        # payload (дані) — те що зберігаємо
        payload = {
            "user_id": str(user_id),
            "company_id": str(company_id),
            "quiz_id": str(quiz_id),
            "completed_at": timestamp,
            "answers": answers,
        }

        # json.dumps — серіалізація dict → рядок (string)
        # ex — expiration (час життя), після якого Redis сам видаляє запис
        await self._redis.set(key, json.dumps(payload), ex=TTL_48_HOURS)

    async def get_user_attempts(
        self,
        user_id: UUID,
        company_id: UUID | None = None,
        quiz_id: UUID | None = None,
    ) -> list[dict]:
        # Будуємо pattern (шаблон) для пошуку — * означає "будь-що"
        if company_id and quiz_id:
            pattern = f"quiz_attempt:{user_id}:{company_id}:{quiz_id}:*"
        elif company_id:
            pattern = f"quiz_attempt:{user_id}:{company_id}:*"
        else:
            pattern = f"quiz_attempt:{user_id}:*"

        keys = await self._redis.keys(pattern)

        results = []
        for key in keys:
            raw = await self._redis.get(key)  # raw — сирі дані (raw data)
            if raw:
                results.append(json.loads(raw))  # json.loads — str → dict

        return results