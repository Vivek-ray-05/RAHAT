"""
Central app settings. Loaded once from environment variables / .env.

IMPORTANT: JWT_SECRET has no insecure default — the app refuses to start
without it. This is a deliberate departure from the old prototype, which
shipped with `JWT_SECRET = os.environ.get(..., "adeo_default_secret_change_in_prod")`.
"""
from pydantic import model_validator
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

    @model_validator(mode="after")
    def _guard_dev_mode_against_real_deployments(self) -> "Settings":
        """DEV_MODE unlocks a fixed OTP code -- anyone can log in as
        anyone. Cheap safety net: if it's on, every CORS origin must
        look like local dev, or the app refuses to start. A real
        deployment's CORS_ORIGINS points at a real domain, so this
        catches DEV_MODE=true accidentally surviving into one."""
        if self.DEV_MODE:
            looks_local = all(
                "localhost" in origin or "127.0.0.1" in origin
                for origin in self.cors_origins_list
            )
            if not looks_local:
                raise ValueError(
                    "DEV_MODE=true but CORS_ORIGINS doesn't look like local dev "
                    f"({self.CORS_ORIGINS!r}). Refusing to start -- DEV_MODE allows "
                    "a fixed OTP code that lets anyone log in as anyone. Set "
                    "DEV_MODE=false for any real deployment."
                )
        return self

    # Notification provider (Phase 6) -- Brevo (formerly Sendinblue),
    # chosen over Twilio/Resend for its free tier: 300 emails/day, no
    # credit card, and no domain-verification requirement to reach an
    # arbitrary recipient (Resend's free tier only reaches your own
    # account email without a verified domain).
    BREVO_API_KEY: str | None = None
    BREVO_FROM_EMAIL: str | None = None

    # LLM providers (optional, used only for explanation/summary text)
    GROK_API_KEY: str | None = None
    OPENROUTER_API_KEY: str | None = None
    OLLAMA_BASE_URL: str | None = None


settings = Settings()
