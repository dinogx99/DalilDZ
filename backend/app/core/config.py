from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dalildz.db")
    redis_url: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "15"))
    max_http_bytes: int = int(os.getenv("MAX_HTTP_BYTES", "2000000"))
    max_redirects: int = int(os.getenv("MAX_REDIRECTS", "4"))
    http_timeout_seconds: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "8"))
    rate_limit_per_minute: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
    ocr_provider: str = os.getenv("OCR_PROVIDER", "none")
    user_agent: str = os.getenv(
        "DALILDZ_USER_AGENT",
        "DalilDZ/1.0 (+https://github.com/dinogx99/DalilDZ)",
    )


settings = Settings()
