"""JSON logging with proper escaping."""

import json
import logging
import sys
from datetime import UTC, datetime

from app.core.config import settings


class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps(
            {
                "time": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
            }
        )


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(
        level=logging.DEBUG if settings.DEBUG else logging.INFO, handlers=[handler], force=True
    )
    for name in ("sqlalchemy.engine", "httpx", "httpcore", "openai", "botocore"):
        logging.getLogger(name).setLevel(logging.WARNING)
