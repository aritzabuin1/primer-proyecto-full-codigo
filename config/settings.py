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

    sentry_dsn: str | None = None
    allow_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
