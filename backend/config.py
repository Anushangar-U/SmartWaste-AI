from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SmartWaste AI"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    use_mock_agents: bool = True
    allowed_origins: str = "http://localhost:8501,http://localhost:3000,http://127.0.0.1:5500"

    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    admin_username: str = "admin"
    admin_password: str = ""
    database_path: str = "data/smartwaste.sqlite3"
    provider_timeout_seconds: float = 20
    provider_max_retries: int = 1
    processing_max_attempts: int = 3
    processing_lease_seconds: int = 600

settings = Settings()
