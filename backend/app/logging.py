import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict


class SafeJsonFormatter(logging.Formatter):
    """
    Structured JSON log formatter that automatically sanitizes sensitive fields
    such as API keys, tokens, and authorization headers.
    """
    SENSITIVE_KEYS = {"api_key", "gemini_api_key", "groq_api_key", "authorization", "secret", "password"}

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include custom structured attributes attached to record
        for attr in ["request_id", "session_id", "dataset_id", "analysis_id", "provider", "duration_ms", "sandbox_status"]:
            val = getattr(record, attr, None)
            if val is not None:
                log_obj[attr] = val

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Sanitize any accidental sensitive leaks
        sanitized = self._sanitize(log_obj)
        return json.dumps(sanitized)

    def _sanitize(self, obj: Any) -> Any:
        if isinstance(obj, dict):
            clean = {}
            for k, v in obj.items():
                if any(s in k.lower() for s in self.SENSITIVE_KEYS):
                    clean[k] = "[REDACTED]"
                else:
                    clean[k] = self._sanitize(v)
            return clean
        elif isinstance(obj, list):
            return [self._sanitize(item) for item in obj]
        return obj


def setup_logger(name: str = "data_detective") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(SafeJsonFormatter())
        logger.addHandler(handler)
    return logger


logger = setup_logger()
