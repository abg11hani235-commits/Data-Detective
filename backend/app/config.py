from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = DATA_DIR / "uploads"
    SAMPLES_DIR: Path = DATA_DIR / "samples"
    ARTIFACTS_DIR: Path = DATA_DIR / "artifacts"
    SANDBOX_DIR: Path = DATA_DIR / "sandbox_tmp"

    # Application settings
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # LLM Providers
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    PRIMARY_LLM_PROVIDER: str = "groq"
    GEMINI_MODEL: str = "models/gemini-3.1-flash-lite"
    GROQ_MODEL: str = "openai/gpt-oss-20b"
    ALLOW_MOCK_FALLBACK: bool = True

    # Database
    DATABASE_URL: Optional[str] = None

    # Authentication & Security
    JWT_SECRET_KEY: str = "data-detective-super-secret-key-change-in-production-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    AUTH_REQUIRED: bool = False

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            # If standard postgres:// or postgresql:// is provided, normalize to postgresql+asyncpg://
            url = self.DATABASE_URL
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return f"sqlite+aiosqlite:///{self.DATA_DIR.as_posix()}/data_detective.db"

    # Ingestion constraints
    MAX_UPLOAD_SIZE_MB: int = 25
    MAX_DATASET_ROWS: int = 250_000
    MAX_DATASET_COLS: int = 200

    # Sandbox Security
    SANDBOX_ENABLED: bool = True
    SANDBOX_BACKEND: str = "subprocess"  # "subprocess" or "docker"
    SANDBOX_TIMEOUT_SECONDS: int = 15
    SANDBOX_MAX_MEMORY_MB: int = 512
    SANDBOX_ALLOW_NETWORK: bool = False
    MAX_GENERATED_CODE_SIZE_BYTES: int = 50 * 1024  # 50 KB
    MAX_STDOUT_BYTES: int = 256 * 1024  # 256 KB

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def ensure_directories(self) -> None:
        """Create necessary data storage directories if they do not exist."""
        for path in [
            self.DATA_DIR,
            self.UPLOADS_DIR,
            self.SAMPLES_DIR,
            self.ARTIFACTS_DIR,
            self.SANDBOX_DIR,
        ]:
            path.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
