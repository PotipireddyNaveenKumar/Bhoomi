import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "BHOOMI V2"
    APP_ENV: str = "development"
    ENVIRONMENT: Optional[str] = None
    DEBUG: bool = True

    @property
    def effective_env(self) -> str:
        return (self.ENVIRONMENT or self.APP_ENV or "development").lower()

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
    SECRET_KEY: str = "bhoomi_v2_super_secure_jwt_secret_key_change_in_production_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./bhoomi.db"
    DATABASE_SYNC_URL: str = "sqlite:///./bhoomi.db"
    
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

settings = Settings()
