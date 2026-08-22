from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:5173"]

    # Database
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # JWT
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Brevo SMTP
    BREVO_SMTP_LOGIN: str
    BREVO_SMTP_PASSWORD: str
    BREVO_SENDER_EMAIL: str = "noreply@lootlooto.com"
    BREVO_SENDER_NAME: str = "LootLooto"
    FRONTEND_URL: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        extra = "ignore"
        case_sensitive = False


settings = Settings()