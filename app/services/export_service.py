# app/services/export_service.py
import csv
import io
import uuid
from typing import Literal

from fastapi import HTTPException, status

from app.models.enums import CompanyRole


class ExportService:
    def __init__(self, redis_repository, company_repository, membership_repository):
        self.redis_repository = redis_repository
        self.company_repository = company_repository
        self.membership_repository = membership_repository

    @staticmethod
    def _build_pattern(
        user_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        quiz_id: uuid.UUID | None = None,
    ) -> str:
        """
        Будує Redis pattern (шаблон пошуку ключів).
        "*" означає "будь-яке значення тут" (wildcard, символ-заміна).
        """
        user_part = str(user_id) if user_id else "*"
        company_part = str(company_id) if company_id else "*"
        quiz_part = str(quiz_id) if quiz_id else "*"
        return f"quiz_attempt:{user_part}:{company_part}:{quiz_part}:*"

    async def export_company_quiz_results(
        self,
        company_id: uuid.UUID,
        requester_id: uuid.UUID,
        target_user_id: uuid.UUID | None,
        quiz_id: uuid.UUID | None,
        export_format: Literal["json", "csv"],
    ):
        # 1. Компанія існує? (404 — Not Found, "не знайдено")
        company = await self.company_repository.get_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company not found",
            )

        # 2. Якщо вказаний target_user_id — він член компанії? (теж 404)
        if target_user_id:
            membership = await self.membership_repository.get_member(
                company_id=company_id, user_id=target_user_id
            )
            if not membership:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User is not a member of this company",
                )

        # 3. Перевіряємо права (403 — Forbidden, "заборонено")
        requester_mem = await self.membership_repository.get_member(
            company_id=company_id, user_id=requester_id
        )
        if not requester_mem or requester_mem.role not in (
            CompanyRole.OWNER,
            CompanyRole.ADMIN,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )

        # 4. Формуємо pattern і забираємо дані з Redis
        pattern = self._build_pattern(
            user_id=target_user_id, company_id=company_id, quiz_id=quiz_id
        )
        data = await self.redis_repository.get_attempts_by_pattern(pattern)

        # 5. Конвертуємо у потрібний формат
        if export_format == "json":
            return data
        return self._to_csv(data)

    async def export_my_results(
        self,
        requester_id: uuid.UUID,
        company_id: uuid.UUID | None,
        quiz_id: uuid.UUID | None,
        export_format: Literal["json", "csv"],
    ):
        """Користувач експортує ОСОБИСТІ дані. Перевірка ролей не потрібна."""
        pattern = self._build_pattern(
            user_id=requester_id, company_id=company_id, quiz_id=quiz_id
        )
        data = await self.redis_repository.get_attempts_by_pattern(pattern)

        if export_format == "json":
            return data
        return self._to_csv(data)

    @staticmethod
    def _to_csv(data: list[dict]) -> io.StringIO:
        output = io.StringIO()
        writer = csv.writer(output)

        # Робимо плоску структуру (flat structure), зручну для аналізу даних
        writer.writerow(
            [
                "user_id",
                "company_id",
                "quiz_id",
                "completed_at",
                "question_id",
                "selected_option_ids",
                "is_correct",
            ]
        )

        for attempt in data:
            for ans in attempt.get("answers", []):
                options_str = ",".join(
                    str(opt) for opt in ans.get("selected_option_ids", [])
                )
                writer.writerow(
                    [
                        attempt.get("user_id"),
                        attempt.get("company_id"),
                        attempt.get("quiz_id"),
                        attempt.get("completed_at"),
                        ans.get("question_id"),
                        options_str,
                        ans.get("is_correct"),
                    ]
                )

        output.seek(0)
        return output