import os
from typing import List, Optional, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator

class Settings(BaseSettings):
    APP_NAME: str = "BHOOMI V2"
    APP_ENV: str = "development"
    ENVIRONMENT: Optional[str] = None
    DEBUG: Optional[bool] = None
    DEMO_MODE: bool = False

    @property
    def effective_env(self) -> str:
        return (os.environ.get("ENVIRONMENT") or os.environ.get("APP_ENV") or self.ENVIRONMENT or self.APP_ENV or "development").lower()

    @property
    def is_production(self) -> bool:
        return self.effective_env in ("production", "prod")
    
    ROOT_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    MODELS_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "models"))
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: Optional[str] = None
    DATABASE_SYNC_URL: Optional[str] = None
    
    # Redis
    REDIS_URL: Optional[str] = None
    
    # Voice Provider
    VOICE_PROVIDER: str = "mock"  # sarvam | whisper | mock | bhashini
    SARVAM_API_KEY: Optional[str] = None
    SARVAM_STT_MODEL: str = "saaras:v3"
    SARVAM_TTS_MODEL: str = "bulbul:v3"
    
    # LLM Provider
    LLM_PROVIDER: str = "mock"  # openai | gemini | groq | mock
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    
    # Vector DB & Embeddings
    VECTOR_DB_PROVIDER: str = "chroma"
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    EMBEDDING_PROVIDER: str = "sentence_transformers"  # sentence_transformers | tfidf | openai | gemini
    EMBEDDING_API_KEY: Optional[str] = None
    SEARCH_API_KEY: Optional[str] = None
    RAG_KNOWLEDGE_PATH: str = "./data/rag/verified_knowledge.json"
    
    # Weather & Market
    WEATHER_PROVIDER: str = "openmeteo"  # openmeteo | openweathermap | mock
    WEATHER_API_KEY: Optional[str] = None
    MARKET_PROVIDER: str = "mock"  # data_gov | agmarknet | mock
    DATA_GOV_API_KEY: Optional[str] = None
    
    # Object Storage
    OBJECT_STORAGE_PROVIDER: str = "local"
    STORAGE_LOCAL_DIR: str = "./uploads"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple, set)):
            return list(v)
        return ["*"]

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return v
        url_str = v.strip()
        # Normalize PostgreSQL schemes to asyncpg
        if url_str.startswith("postgres://"):
            url_str = "postgresql+asyncpg://" + url_str[len("postgres://"):]
        elif url_str.startswith("postgresql://"):
            url_str = "postgresql+asyncpg://" + url_str[len("postgresql://"):]
        elif url_str.startswith("postgresql+psycopg2://"):
            url_str = "postgresql+asyncpg://" + url_str[len("postgresql+psycopg2://"):]
        return url_str

    @model_validator(mode="after")
    def validate_production_and_defaults(self) -> "Settings":
        # Resolve DEBUG: if not explicitly configured, default to False in production, True in dev
        if self.DEBUG is None:
            self.DEBUG = False if self.is_production else True

        # Database URL resolution
        if not self.DATABASE_URL:
            if self.is_production:
                raise ValueError(
                    "Production configuration error: DATABASE_URL must be provided from the environment in production."
                )
            self.DATABASE_URL = "sqlite+aiosqlite:///./bhoomi.db"
        elif self.is_production and "sqlite" in self.DATABASE_URL.lower():
            raise ValueError(
                "Production configuration error: SQLite is not permitted in production. DATABASE_URL must point to a PostgreSQL instance."
            )

        # Database Sync URL fallback (optional development compatibility setting)
        if not self.DATABASE_SYNC_URL and not self.is_production:
            self.DATABASE_SYNC_URL = "sqlite:///./bhoomi.db"

        # SECRET_KEY resolution
        dev_secret = "bhoomi_dev_jwt_secret_key_only_non_production_2026"
        if self.is_production:
            if (
                not self.SECRET_KEY
                or self.SECRET_KEY in (
                    "bhoomi_v2_super_secure_jwt_secret_key_change_in_production_2026",
                    dev_secret,
                    "your_secret_key_here",
                    "secret",
                    "changeme",
                )
                or len(self.SECRET_KEY) < 16
            ):
                raise ValueError(
                    "Production security violation: A secure, non-default SECRET_KEY (min 16 characters) must be provided in production."
                )
        else:
            if not self.SECRET_KEY:
                self.SECRET_KEY = dev_secret

        return self

settings = Settings()
