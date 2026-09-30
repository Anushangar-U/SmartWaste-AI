from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SmartWaste AI"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    use_mock_agents: bool = True
    allowed_origins: str = "http://localhost:8501,http://localhost:3000,http://127.0.0.1:5500"

    agent1_provider: str = "auto"
    agent1_groq_model: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    agent1_openrouter_api_key: str = ""
    agent1_openrouter_model: str = "nex-agi/nex-n2.5-mini:free"
    openrouter_api_key: str = ""
    openrouter_fallback_api_key: str = ""
    openrouter_model: str = "openrouter/free"
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"

    # Optional citizen photo / vision analysis. Uses the existing OpenRouter key.
    vision_model: str = ""
    vision_max_image_mb: float = Field(default=5, ge=1, le=10)
    vision_max_dimension: int = Field(default=1800, ge=512, le=4096)
    upload_dir: str = "data/uploads"

    admin_username: str = "admin"
    admin_password: str = ""
    database_path: str = "data/smartwaste.sqlite3"
    provider_timeout_seconds: float = Field(default=20, ge=1, le=60)
    provider_max_retries: int = Field(default=1, ge=0, le=2)
    processing_max_attempts: int = Field(default=3, ge=1, le=5)
    processing_lease_seconds: int = Field(default=600, ge=600)
    duplicate_window_days: int = Field(default=7, ge=1, le=30)
    duplicate_similarity_threshold: float = Field(default=0.82, ge=0, le=1)
    public_requests_per_minute: int = Field(default=30, ge=1, le=1000)
    auth_requests_per_minute: int = Field(default=20, ge=1, le=1000)
    max_concurrent_processing: int = Field(default=2, ge=1, le=16)
    retention_days: int = Field(default=90, ge=0)

settings = Settings()
