import json
import logging
import os
import socket
import getpass
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Optional


def _safe_getuser() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return "unknown"


def _get_audit_logger() -> logging.Logger:
    logger = logging.getLogger("add_two_numbers.audit")
    if not logger.handlers:
        log_dir = os.environ.get("AUDIT_LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        handler = RotatingFileHandler(
            os.path.join(log_dir, "audit.log"),
            maxBytes=1_048_576, backupCount=5, encoding="utf-8"
        )
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def _build_entry(event: str, input_1: str, input_2: str,
                 result: Optional[float], error: Optional[str]) -> str:
    return json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "input_1": input_1,
        "input_2": input_2,
        "result": result,
        "error": error,
        "hostname": socket.gethostname(),
        "os_user": _safe_getuser(),
    })


def log_success(input_1: str, input_2: str, result: float) -> None:
    try:
        _get_audit_logger().info(_build_entry("SUCCESS", input_1, input_2, result, None))
    except Exception:
        pass


def log_failure(input_1: str, input_2: str, error: str) -> None:
    try:
        _get_audit_logger().info(_build_entry("VALIDATION_ERROR", input_1, input_2, None, error))
    except Exception:
        pass
