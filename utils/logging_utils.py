import logging
import os
from logging.handlers import RotatingFileHandler

# Log format: [2026-03-01 19:00:00] [INFO ] [scrape_nonreg] Starting...
LOG_FORMAT = "[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Map level names to logging constants for easy configuration
LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

# Global registry so the same logger isn't configured twice
_configured_loggers: set = set()


def get_logger(name: str, log_level: str = "info") -> logging.Logger:
    """Return a logger that writes to both console and a rotating log file.

    Args:
        name:      Logger name (usually __name__ or the script stem).
        log_level: One of 'debug', 'info', 'warning', 'error'.

    Usage:
        from utils.logging_utils import get_logger
        logger = get_logger(__name__)
        logger.info("Starting scrape...")
        logger.error("Something went wrong: %s", err)
    """
    logger = logging.getLogger(name)

    # Only configure once even if get_logger is called multiple times
    if name in _configured_loggers:
        return logger

    level = LEVELS.get(log_level.lower(), logging.INFO)
    logger.setLevel(level)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # --- Console handler ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # --- Rotating file handler (logs/<name>.log, max 5 MB × 3 backups) ---
    logs_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs"
    )
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, f"{name}.log")
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Prevent messages bubbling up to the root logger (avoids duplicate output)
    logger.propagate = False

    _configured_loggers.add(name)
    return logger
