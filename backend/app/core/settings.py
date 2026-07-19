from pathlib import Path
from typing import Optional, Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Centralized application configuration.
    
    Reads configuration from a .env file or environment variables.
    Uses pydantic-settings for validation and type safety.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        frozen=True,
    )

    #Environment Config

    # Application Config
    APP_NAME: str = "GuardFlow"
    APP_VERSION: str = "0.1.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False

    # Database Config
    DATABASE_URL: str = "sqlite:///./data/guardflow.db"

    # Logging Config
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_DIR: Path = Path("logs")

    # AI Config (legacy Ollama values are retained for compatibility)
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3:latest"
    # Local LLM calls (especially cold model loads) routinely take longer
    # than a typical HTTP timeout. Configurable here instead of hardcoded
    # in llm_service.py so it can be tuned per machine via .env.
    OLLAMA_TIMEOUT: float = 30.0

    # Local semantic-analysis model served by Qualcomm GenieX.  The LLM is
    # never a scoring authority; it supplies validated semantic flags to the
    # deterministic risk engine.  All values can be overridden in .env.
    LLM_ENABLED: bool = True
    LLM_BASE_URL: str = "http://127.0.0.1:18181"
    LLM_MODEL: str = "Qwen/Qwen2.5-3B-Instruct-GGUF:Q4_0"
    LLM_TIMEOUT: float = 45.0
    LLM_MAX_TOKENS: int = 320

    SERIAL_PORT: Optional[str] = None
    SERIAL_BAUDRATE: int = 9600
    SERIAL_TIMEOUT: float = 1.0

    SECRET_KEY: str = "change-me"
    
    ENVIRONMENT: Literal["development","testing","production"] = "development"
    #CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    # Serial Config


# Singleton settings object
settings = Settings()
