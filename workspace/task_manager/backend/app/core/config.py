"""Application Configuration"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Task_Manager"
    DATABASE_URL: str = "sqlite:///./task_manager.db"
    SECRET_KEY: str = "change-me-in-production-use-secrets"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        env_file = ".env"


settings = Settings()
