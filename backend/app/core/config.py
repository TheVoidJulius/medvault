import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "MedVault AI — Medical Record Database"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite:///./medical_records.db"
    JWT_SECRET_KEY: str = "btech-project-2501730022-2501730270-super-secret-jwt-key-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    # "mimic": real de-identified patients from the MIMIC-IV demo (default).
    # "synthetic": hand-written storylines plus the generated Indian cohort (used by the test suite).
    DATA_SOURCE: str = "mimic"
    AI_PROVIDER: str = "grounded_hybrid"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1"
    ALLOW_EXTERNAL_PHI: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

if (os.getenv("VERCEL") == "1" or os.getenv("VERCEL_ENV") is not None) and (
    settings.DATABASE_URL == "sqlite:///./medical_records.db"
):
    settings.DATABASE_URL = "sqlite:////tmp/medical_records.db"
