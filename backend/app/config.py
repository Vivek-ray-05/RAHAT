"""
Central app settings. Loaded once from environment variables / .env.

IMPORTANT: JWT_SECRET has no insecure default — the app refuses to start
without it. This is a deliberate departure from the old prototype, which
shipped with `JWT_SECRET = os.environ.get(..., "adeo_default_secret_change_in_prod")`.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str

    # Auth
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8h, matches old zone_admin/coordinator session length

    # Dev-mode toggle: when True, allows a fixed OTP for local testing.
    # Must default to False so a forgotten env var never ships an OTP bypass.
    DEV_MODE: bool = False

    # CORS — comma-separated list of allowed origins, no wildcard in prod
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Notification providers (Phase 6)
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    RESEND_API_KEY: str | None = None

    # LLM providers (optional, used only for explanation/summary text)
    GROK_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    OLLAMA_BASE_URL: str | None = None


settings = Settings()
