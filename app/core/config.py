import os
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Перевірка середовища ---
    is_in_docker: bool = Field(
        default_factory=lambda: os.path.exists('/.dockerenv')
    )

    # PostgreSQL
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "secret"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "mydb"

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    @model_validator(mode="after")
    def adjust_hosts_for_local_development(self) -> "Settings":
        if not self.is_in_docker:
            self.REDIS_HOST = "localhost"

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

settings = Settings()