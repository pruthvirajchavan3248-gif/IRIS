"""
IRIS Logging Subsystem
Configures structured diagnostic logging with file rotation and console output.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional
from .config import get_config


class ColoredFormatter(logging.Formatter):
    """Clean formatter with optional console coloring."""
    GREY = "\x1b[38;20m"
    CYAN = "\x1b[36;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"
    FORMAT = "%(asctime)s | %(levelname)-8s | [%(name)s] %(message)s"

    FORMATS = {
        logging.DEBUG: GREY + FORMAT + RESET,
        logging.INFO: CYAN + FORMAT + RESET,
        logging.WARNING: YELLOW + FORMAT + RESET,
        logging.ERROR: RED + FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + FORMAT + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.FORMAT)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)


def setup_logger(name: str = "iris", log_file: Optional[Path] = None, level: str = "INFO") -> logging.Logger:
    """Configures and returns a named logger instance."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(ColoredFormatter())
    logger.addHandler(console_handler)

    # Rotating File Handler
    try:
        config = get_config()
        target_file = log_file or (config.logs_dir / "iris.log")
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            target_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB per file
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | [%(name)s:%(filename)s:%(lineno)d] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Failed to setup rotating file logger: {e}", file=sys.stderr)

    logger.propagate = False
    return logger


def get_logger(name: str = "iris") -> logging.Logger:
    """Convenience getter for child loggers."""
    return logging.getLogger(f"iris.{name}")
