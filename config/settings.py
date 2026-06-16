"""
Central configuration module.

Loads all settings from environment variables (/.env file).
Every other module imports from here — never reads .env directly.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

# On Railway, /data is the persistent volume mount point
_DEFAULT_DB = "sqlite:////data/trading.db" if os.path.isdir("/data") else "sqlite:///data/trading.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Alpaca ---
    alpaca_api_key: str = Field(default="", description="Alpaca API key")
    alpaca_secret_key: str = Field(default="", description="Alpaca secret key")
    alpaca_base_url: str = Field(
        default="https://paper-api.alpaca.markets",
        description="Alpaca base URL (paper or live)",
    )

    # --- Groq ---
    groq_api_key: str = Field(default="", description="Groq API key")

    # --- Application ---
    environment: str = Field(default="development", description="development | paper | live")
    log_level: str = Field(default="DEBUG", description="Logging verbosity")
    database_url: str = Field(default=_DEFAULT_DB)

    # --- Risk Parameters ---
    max_risk_per_trade_pct: float = Field(default=0.02, description="Max risk per trade as fraction")
    daily_loss_limit_pct: float = Field(default=0.03, description="Daily loss limit as fraction")
    max_portfolio_exposure_pct: float = Field(default=0.80, description="Max portfolio deployed")

    # --- Trading Universe ---
    watchlist: list[str] = Field(default=["SPY", "QQQ"], description="Symbols to watch")

    @property
    def is_paper(self) -> bool:
        return self.environment in ("development", "paper")

    @property
    def is_live(self) -> bool:
        return self.environment == "live"

    def validate_required_keys(self) -> list[str]:
        """Return list of missing required API keys."""
        missing = []
        if not self.alpaca_api_key:
            missing.append("ALPACA_API_KEY")
        if not self.alpaca_secret_key:
            missing.append("ALPACA_SECRET_KEY")
        if not self.groq_api_key:
            missing.append("GROQ_API_KEY")
        return missing


# Single shared instance — import this everywhere
settings = Settings()
