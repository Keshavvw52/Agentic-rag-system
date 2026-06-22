from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_NAME: str = "Agentic RAG System"
    DEBUG: bool = False
    API_V1_STR: str = "/api"

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "agentic_rag"

    # JWT
    JWT_SECRET: str = "change-me-in-production-very-long-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Groq LLM
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./data/chroma"
    CHROMA_COLLECTION_PREFIX: str = "user_"

    # Embeddings
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Web Search Fallback
    TAVILY_API_KEY: str = ""
    USE_TAVILY: bool = False  # Falls back to DuckDuckGo if False

    # RAG Config
    TOP_K_RETRIEVAL: int = 20
    TOP_K_RERANK: int = 5
    MAX_RETRIES: int = 3
    MAX_ITERATIONS: int = 3
    HALLUCINATION_THRESHOLD: float = 0.2
    CONFIDENCE_THRESHOLD_HIGH: float = 0.90
    CONFIDENCE_THRESHOLD_MEDIUM: float = 0.70
    CONFIDENCE_THRESHOLD_LOW: float = 0.50
    ROUTING_CONFIDENCE_MIN: float = 0.70

    # Chunk config
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://frontend:5173",
    ]

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:5173"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return value

settings = Settings()
