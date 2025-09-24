from __future__ import annotations
import logging
import logging.config
from pathlib import Path

def setup_logging(app_name: str, log_dir: Path, level: str = "INFO") -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    cfg = {
        "version": 1,
        "formatters": {
            "std": {"format": "%(asctime)s %(levelname)s [%(name)s] %(message)s"}
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "std",
                "level": level,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "std",
                "level": level,
                "filename": str(log_dir / f"{app_name}.log"),
                "maxBytes": 5 * 1024 * 1024,
                "backupCount": 3,
                "encoding": "utf-8",
            },
        },
        "root": {"handlers": ["console", "file"], "level": level},
    }
    logging.config.dictConfig(cfg)
    logger = logging.getLogger(app_name)
    logger.info("Logging initialized.")
    return logger
