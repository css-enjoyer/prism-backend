from pydantic_settings import BaseSettings, SettingsConfigDict

# to test: uv run python -c "from app.config import settings; print(settings.database_url)"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    app_name: str = "Prism API"
    database_url: str

settings = Settings()
