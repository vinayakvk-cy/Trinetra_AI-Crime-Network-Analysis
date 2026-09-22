"""
TRINETRA Logging Configuration
==============================

Centralized logging configuration for the backend.

All major modules should use:

    logger = logging.getLogger(__name__)

instead of configuring their own logging handlers.
"""

from __future__ import annotations

import logging
import logging.config
from pathlib import Path

from app.core.config import settings


# ============================================================
# LOG DIRECTORY
# ============================================================

LOG_DIR = (
    Path(settings.data_dir)
    / "logs"
)

LOG_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# LOG FILES
# ============================================================

APPLICATION_LOG = (
    LOG_DIR / "application.log"
)

ERROR_LOG = (
    LOG_DIR / "error.log"
)


# ============================================================
# LOG FORMAT
# ============================================================

LOG_FORMAT = (
    "%(asctime)s | "
    "%(levelname)s | "
    "%(name)s | "
    "%(message)s"
)


# ============================================================
# LOGGING CONFIGURATION
# ============================================================

LOGGING_CONFIG = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": LOG_FORMAT,
        },
    },

    "handlers": {

        # ----------------------------------------------------
        # Console
        # ----------------------------------------------------

        "console": {
            "class": "logging.StreamHandler",
            "level": settings.log_level.upper(),
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },

        # ----------------------------------------------------
        # Application log
        # ----------------------------------------------------

        "application_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": settings.log_level.upper(),
            "formatter": "standard",
            "filename": str(
                APPLICATION_LOG
            ),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },

        # ----------------------------------------------------
        # Error log
        # ----------------------------------------------------

        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "standard",
            "filename": str(
                ERROR_LOG
            ),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },

    # ========================================================
    # ROOT LOGGER
    # ========================================================

    "root": {
        "level": settings.log_level.upper(),
        "handlers": [
            "console",
            "application_file",
            "error_file",
        ],
    },

    # ========================================================
    # THIRD-PARTY LOGGER CONTROL
    # ========================================================

    "loggers": {

        "uvicorn": {
            "level": settings.log_level.upper(),
            "handlers": [
                "console",
                "application_file",
            ],
            "propagate": False,
        },

        "uvicorn.error": {
            "level": settings.log_level.upper(),
            "handlers": [
                "console",
                "application_file",
                "error_file",
            ],
            "propagate": False,
        },

        "uvicorn.access": {
            "level": "INFO",
            "handlers": [
                "console",
                "application_file",
            ],
            "propagate": False,
        },

        "neo4j": {
            "level": "WARNING",
            "handlers": [
                "console",
                "application_file",
            ],
            "propagate": False,
        },
    },
}


# ============================================================
# SETUP FUNCTION
# ============================================================

def setup_logging() -> None:
    """
    Configure application-wide logging.

    This should be called once during application startup.
    """

    logging.config.dictConfig(
        LOGGING_CONFIG
    )


# ============================================================
# LOGGER HELPER
# ============================================================

def get_logger(
    name: str,
) -> logging.Logger:
    """
    Return a logger for a module.

    Example:

        logger = get_logger(__name__)
    """

    return logging.getLogger(
        name
    )