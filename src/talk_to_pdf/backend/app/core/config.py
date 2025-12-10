from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env',case_sensitive=True)
    SQLALCHEMY_DATABASE_URL: str = 'xxx'


settings = Settings()