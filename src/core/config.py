from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import ClassVar



class Settings(BaseSettings):
    # -----------------------------
    # Database
    # -----------------------------
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    DATABASE_URL: str
    SQL_ECHO: bool = False

    # -----------------------------
    # NeoGate / Orange Money Config
    # -----------------------------
    NEOGATE_BASE_URL: str
    NEOGATE_API_USERNAME: str
    NEOGATE_API_PASSWORD: str
    ORANGE_MONEY_PIN: str
    MOBILE_MONEY_SIMS: ClassVar[dict] = {
        'orange_money_1': ('orange_money_1', 1),
        'orange_money_2': ('orange_money_2', 2),
    }
    SIM_CONFIG: dict = {
        'primary_sim': 'orange_money_1',
        'secondary_sim': 'orange_money_2',
    }

    # -----------------------------
    # Gmail API Config
    # -----------------------------
    GMAIL_AIRTIME_CREDENTIALS: str
    GMAIL_WITHDRAWAL_CREDENTIALS: str
    GMAIL_AIRTIME_TOKEN: str
    GMAIL_WITHDRAWAL_TOKEN: str
    GMAIL_FETCH_INTERVAL: int
    GMAIL_AIRTIME_INTERVAL: int

    # -----------------------------
    # Message broker
    # -----------------------------
    REDIS_URL: str

    SECRET_KEY: str

    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@cashmoov.net"
    EMAIL_FROM_NAME: str = "CashMoov"

    # -----------------------------
    # App Environment
    # -----------------------------
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "info"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance to avoid reloading .env repeatedly"""
    return Settings()


settings = get_settings()


