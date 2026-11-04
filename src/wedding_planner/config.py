from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    app_name: str = "EverAfter AI"
    app_env: str = "development"
    secret_key: str = "unsafe-development-key-change-me"
    database_url: str = "sqlite:///./everafter_dev.db"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "granite3.3:8b"
    ollama_temperature: float = 0.2
    tavily_api_key: str = ""
    email_provider: str = "resend"
    resend_api_key: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    email_from: str = ""
    email_max_attachment_mb: int = 15
    app_currency: str = "INR"
    app_max_search_results: int = 6
    generated_dir: str = "generated"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)
settings = Settings()
