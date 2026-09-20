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
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    admin_username: str = "admin"
    admin_password: str = ""

settings = Settings()