from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', case_sensitive=True)
    SQLALCHEMY_DATABASE_URL: str = 'xxx'
    JWT_SECRET_KEY: str = 'xxx'
    JWT_ALGORITHM: str = 'xxx'
    SKIP_AUTH: bool = False
    FILE_STORAGE_DIR:str = 'xxx'


settings = Settings()
