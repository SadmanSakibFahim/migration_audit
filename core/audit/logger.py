# core/logger.py
import logging
import os
import json
import time
from datetime import datetime, timezone

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

class JsonFormatter(logging.Formatter):
    """Formats log records as JSON objects for SIEM ingestion."""
    def format(self, record):
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        # Include extra fields if available
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "action"):
            log_entry["action"] = record.action
        if hasattr(record, "ip_address"):
            log_entry["ip_address"] = record.ip_address
            
        return json.dumps(log_entry)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # Prevent duplicate handlers

    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    logger.setLevel(log_level)
    logger.propagate = False

    # 1. Console Handler (Pretty text for devs)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # 2. File Handler (JSON for Audit/SIEM)
    # We use a rotating file or just a simple file handler. 
    # For audit, we typically want a dedicated file.
    # Using .jsonl extension (Newline Delimited JSON) is standard for logs
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, "audit.jsonl"))
    file_handler.setFormatter(JsonFormatter())
    logger.addHandler(file_handler)

    return logger

# Dedicated Audit Logger Helper
audit_logger = get_logger("audit")

def log_audit_event(action: str, user_id: str = "anonymous", ip_address: str = "unknown", details: str = ""):
    """Helper to log structured audit events."""
    extra = {"user_id": user_id, "action": action, "ip_address": ip_address}
    audit_logger.info(details, extra=extra)
