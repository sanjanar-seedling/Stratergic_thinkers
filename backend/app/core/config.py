from pydantic_settings import BaseSettings
from functools import lru_cache


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

    # LLM Provider: "ollama" (local/free) or "openai" (cloud)
    llm_provider: str = "ollama"

    # OpenAI (used when llm_provider = "openai")
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    chat_model: str = "gpt-4o-mini"

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
    slack_redirect_uri: str = "http://localhost:5173/oauth/callback"

    # OAuth — Discord
    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_redirect_uri: str = "http://localhost:5173/oauth/callback"

    # OAuth — Google (Calendar + Gmail)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:5173/oauth/callback"

    # Email Ingestion
    imap_server: str = "imap.gmail.com"
    email_address: str = ""
    email_password: str = ""

    # Voice Transcription
    whisper_provider: str = "openai"  # "openai" or "local"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra fields in .env


@lru_cache()
def get_settings() -> Settings:
    return Settings()
