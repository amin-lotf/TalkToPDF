from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', case_sensitive=True,env_parse_none_str='None')
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
    CHUNKER_KIND: str = "block"
    CHUNKER_MAX_CHARS: int = 1200
    CHUNKER_OVERLAP: int = 0
    MAX_TOP_K: int = 0
    MAX_TOP_N: int = 0
    REPLY_PROVIDER: str = 'xxx'
    REPLY_TEMPERATURE: float = 0.2
    REPLY_MODEL: str = 'xxx'
    REPLY_MAX_OUTPUT_TOKENS: Optional[int] = None
    REPLY_MAX_CONTEXT_CHARS: int = 20000
    QUERY_REWRITER_PROVIDER: str = 'xxx'
    QUERY_REWRITER_TEMPERATURE: float = 0.2
    QUERY_REWRITER_MODEL: str = 'xxx'
    QUERY_REWRITER_MAX_TURN: int = 6
    QUERY_REWRITER_MAX_HISTORY_CHARS: int = 6000
    GROBID_URL: str = "http://localhost:8070"


settings = Settings()
