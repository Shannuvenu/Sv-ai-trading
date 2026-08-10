from pydantic_settings import BaseSettings
from functools import lru_cache
from decimal import Decimal
import json


def _decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class Settings(BaseSettings):
    APP_NAME: str = "SV AI Trading Platform"
    DEBUG: bool = True

    DATABASE_URL: str = "postgresql://svuser:svpass@localhost:5432/svtrading"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "change-me-in-production-use-a-strong-random-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # Market data provider
    MARKET_DATA_PROVIDER: str = "simulated"  # "simulated" | "upstox"

    # Upstox API
    UPSTOX_ACCESS_TOKEN: str = ""
    UPSTOX_CLIENT_ID: str = ""
    UPSTOX_CLIENT_SECRET: str = ""
    UPSTOX_REDIRECT_URI: str = "http://localhost:8000/upstox/callback"

    # Gemini AI
    GEMINI_API_KEY: str = ""
    FINNHUB_API_KEY: str = ""
    MARKETAUX_API_KEY: str = ""

    class Config:
        env_file = ".env"
        json_encoders = {Decimal: lambda v: float(v)}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
