from pydantic_settings import BaseSettings, SettingsConfigDict

# to test: uv run python -c "from app.config import settings; print(settings.database_url)"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    app_name: str = "Prism API"
    database_url: str
    webhook_secret: str
    prism_api_key: str
    openrouter_api_key: str
    openrouter_base_url: str
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct"
    gh_token: str


settings = Settings()
