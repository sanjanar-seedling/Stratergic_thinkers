from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Find .env in current dir or project root
_env_file = Path(".env")
if not _env_file.exists():
    _env_file = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    # Application
    app_name: str = "Seedlings API"
    debug: bool = True
    api_prefix: str = "/api"

    # Database
    database_url: str = "postgresql+asyncpg://seedlings:seedlings_dev_2024@localhost:5432/seedlings"
    database_schema: str = "seedlings"

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_stream_name: str = "seedlings:events"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # LLM Provider: "ollama" (local/free), "openai" (cloud), or "groq" (fast cloud)
    llm_provider: str = "groq"

    # OpenAI (used when llm_provider = "openai")
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

    # Groq (used when llm_provider = "groq")
    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.3-70b-versatile"
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # Ollama (used when llm_provider = "ollama")
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "tinyllama"
    ollama_embed_model: str = "nomic-embed-text"

    # MinIO / S3
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "seedlings"
    s3_secret_key: str = "seedlings_dev_2024"
    s3_bucket: str = "seedlings-uploads"

    # OAuth — Slack
    slack_client_id: str = ""
    slack_client_secret: str = ""
    slack_redirect_uri: str = "https://localhost:5173/oauth/callback"
    slack_user_token: str = ""  # Local dev token for DM access
    slack_bot_token: str = ""   # Local dev bot token

    # OAuth — Google (Calendar + Gmail)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "https://localhost:5173/oauth/callback"

    # Email Ingestion
    imap_server: str = "imap.gmail.com"
    email_address: str = ""
    email_password: str = ""

    # Voice Transcription: "groq", "openai", or "local"
    whisper_provider: str = "groq"

    class Config:
        env_file = str(_env_file)
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields in .env


@lru_cache()
def get_settings() -> Settings:
    return Settings()
