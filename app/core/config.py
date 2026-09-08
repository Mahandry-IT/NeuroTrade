"""Configuration applicative — variables d'environnement (pydantic-settings)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──
    database_url: str = "postgresql://user:password@localhost:5432/trading_bot"

    # ── Gemini AI ──
    gemini_api_key: str = ""
    gemini_rpm_limit: int = 10  # free-tier requests per minute
    gemini_rpd_limit: int = 1500  # free-tier requests per day

    # ── Security ──
    encryption_key: str = ""  # Fernet key for API key encryption
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24h

    # ── SMTP ──
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    # ── Trading Platform ──
    trading_platform_api_key: str = ""
    trading_platform_api_secret: str = ""

    # ── Kraken Spot API ──
    kraken_api_key: str = ""
    kraken_api_secret: str = ""
    kraken_taker_fee_pct: float = 0.26  # Kraken default taker fee %
    kraken_default_pair: str = "XXBTZUSD"  # BTC/USD


settings = Settings()
