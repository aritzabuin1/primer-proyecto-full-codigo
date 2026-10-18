from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Primer Proyecto Full Código"
    env: str = "dev"
    host: str = "0.0.0.0"
    port: int = 8000

    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db: str = "wa_rag"

    qdrant_url: str = "http://qdrant:6333"
    qdrant_api_key: str | None = None  # en local normalmente None

    groq_api_key: SecretStr | None = Field(default=None, alias="GROQ_API_KEY")

    sentry_dsn: str | None = None
    allow_origins: str = "*"

    # (campos que ya tienes...)
    # ── Guardrails / límites ─────────────────────────────────────────────
    use_mock_llm: bool = Field(default=False, alias="USE_MOCK_LLM")
    use_inmemory_store: bool = Field(default=False, alias="USE_INMEMORY_STORE")  # NUEVO
    max_input_chars: int = Field(default=2000, alias="MAX_INPUT_CHARS")
    enable_moderation: bool = Field(default=True, alias="ENABLE_MODERATION")

    # Rate limiting (por usuario)
    rate_limit_per_min: int = Field(default=20, alias="RATE_LIMIT_PER_MIN")

    # RAG
    enable_rag: bool = Field(default=False, alias="ENABLE_RAG")
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )
    qdrant_collection: str = Field(default="scientists", alias="QDRANT_COLLECTION")

    # Whatspp Cloud API
    whatsapp_access_token: SecretStr | None = Field(
        default=None, alias="WHATSAPP_ACCESS_TOKEN"
    )
    whatsapp_phone_number_id: str | None = Field(
        default=None, alias="WHATSAPP_PHONE_NUMBER_ID"
    )
    whatsapp_verify_token: str | None = Field(
        default=None, alias="WHATSAPP_VERIFY_TOKEN"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        populate_by_name=True,
        extra="ignore",
    )


settings = Settings()
