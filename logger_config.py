"""
Intelligent logging configuration for JobMatcher.
- Rotating file handler for crash analysis (logs/jobmatcher.log)
- Also writes crawler-specific logs to DB (CrawlerLog table)
- Structured format: [TIMESTAMP] [LEVEL] [MODULE] message
"""
import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime


def setup_logging():
    """Configure structured logging with rotating file handler."""
    os.makedirs("logs", exist_ok=True)

    # Root logger
    logger = logging.getLogger("jobmatcher")
    logger.setLevel(logging.DEBUG)

    # Formatter
    fmt = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Rotating file handler (5MB max, 3 backups)
    file_handler = RotatingFileHandler(
        "logs/jobmatcher.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # Console handler (INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger


def log_to_db(db_session, message, level="INFO", source="system"):
    """
    Write a log entry to the CrawlerLog table for the frontend console.
    This is separate from Python logging to give the frontend access.
    """
    from models import CrawlerLog
    try:
        entry = CrawlerLog(
            message=message,
            level=level,
            source=source,
            timestamp=datetime.utcnow()
        )
        db_session.add(entry)
        db_session.commit()
    except Exception:
        db_session.rollback()


# Module-level logger
logger = setup_logging()
