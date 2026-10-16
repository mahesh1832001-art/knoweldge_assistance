
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "knowledge_assistant"
    CHROMA_PATH: str = "./chroma_data"
    OPENAI_API_KEY: str = ""
    ALLOWED_TOKEN_COUNT: int = 20
    REFILL_RATE: float = 20 / 60
    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

MAX_COSINE_DISTANCE = 0.75
DEFAULT_TOP_K = 3
