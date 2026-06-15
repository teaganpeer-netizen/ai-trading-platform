"""
Logging configuration.

Call setup_logging() once at application startup.
All modules then use: import logging; logger = logging.getLogger(__name__)
"""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(log_level: str = "DEBUG") -> None:
    """Configure structured logging to both console and rotating file."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.DEBUG)

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)

    # Rotating file handler — max 10MB per file, keep 5 backups
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / "trading.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    # Apply to root logger so all modules inherit it
    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
