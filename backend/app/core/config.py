from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "后端八股刷题助手"
    database_url: str = "sqlite:///./interview.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
