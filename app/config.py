import os
from pydantic import BaseModel
from typing import Optional

# Automatically load .env if present
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip().strip('"').strip("'")


class Settings(BaseModel):
    APP_NAME: str = "Enterprise AI Orchestrator"
    APP_VERSION: str = "1.0.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DATA_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super-secret-hackathon-key-2026-enterprise-orchestrator-jwt-token")
    # Google Cloud Firestore / Firebase settings
    FIRESTORE_PROJECT_ID: Optional[str] = os.getenv("FIRESTORE_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    FIREBASE_CREDENTIALS_PATH: Optional[str] = os.getenv("FIREBASE_CREDENTIALS_PATH", os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))
    FIRESTORE_EMULATOR_HOST: Optional[str] = os.getenv("FIRESTORE_EMULATOR_HOST", "")
    FIRESTORE_USE_LOCAL_FALLBACK: bool = os.getenv("FIRESTORE_USE_LOCAL_FALLBACK", "true").lower() in ("true", "1")

settings = Settings()
os.makedirs(settings.DATA_DIR, exist_ok=True)

