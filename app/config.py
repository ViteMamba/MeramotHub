import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # PostgreSQL via Supabase
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # Supabase Client (for Storage, Realtime, etc.)
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback-secret-key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

    # Groq AI
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")


settings = Settings()
