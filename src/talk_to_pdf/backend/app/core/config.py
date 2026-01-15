from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', case_sensitive=True)
    SQLALCHEMY_DATABASE_URL: str = 'xxx'
    TEST_SQLALCHEMY_DATABASE_URL: str = 'xxx'
    JWT_SECRET_KEY: str = 'xxx'
    JWT_ALGORITHM: str = 'xxx'
    SKIP_AUTH: bool = False
    FILE_STORAGE_DIR:str = 'xxx'
    OPENAI_API_KEY: str = 'xxx'
    EMBED_PROVIDER: str = 'xxx'
    EMBED_MODEL: str = 'xxx'
    EMBED_BATCH_SIZE: int = 0
    EMBED_DIMENSIONS: Optional[int] = 0
    CHUNKER_KIND: str = "xxx"
    CHUNKER_MAX_CHARS: int = 0
    CHUNKER_OVERLAP: int = 0
    MAX_TOP_K: int = 0
    MAX_TOP_N: int = 0


settings = Settings()
