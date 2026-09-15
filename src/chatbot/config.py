from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM / Embeddings
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    llm_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-small"

    # Retrieval
    retrieval_top_k: int = 5

    # Milvus
    milvus_uri: str = "http://localhost:19530"
    milvus_collection: str = "parking_knowledge"

    # Database
    database_url: str = "sqlite:///./chatbot.db"

    # API
    admin_token: str = "change-me"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Logging
    log_level: str = "INFO"

    # MCP storage
    reservations_file_path: str = "data/reservations.txt"

    # SMTP / Admin notifications
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "chatbot@parking.local"
    admin_email: str = "admin@parking.local"
    approval_timeout_seconds: int = 300


settings = Settings()
