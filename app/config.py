from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    OPENAI_API_KEY: str
    DATABASE_URL: str
    OPENAI_MODEL: str = "gpt-6-luna"
    AGENT_MAX_STEPS: int = 5


settings = Settings()  # type: ignore
