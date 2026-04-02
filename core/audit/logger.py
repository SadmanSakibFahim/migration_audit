# core/logger.py
import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any

# Ensure logs directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Sensistive data patterns (Passwords, Tokens, Keys)
SENSITIVE_PATTERNS = [
    re.compile(r"(password|secret|token|key|pwd)\s*[:=]\s*['\"]?([^'\"\s]+)['\"]?", re.IGNORECASE),
]

def mask_sensitive_data(message: str) -> str:
    """Replaces sensitive patterns with [REDACTED]."""
    if not isinstance(message, str):
        return message
        
    masked = message
    for pattern in SENSITIVE_PATTERNS:
        # Replace the value group (group 2) with [REDACTED]
        masked = pattern.sub(r"\1: [REDACTED]", masked)
    return masked

class JsonFormatter(logging.Formatter):
    """Formats log records as JSON objects for SIEM ingestion."""

    def format(self, record: logging.LogRecord) -> str:
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
            
        # Mask all string fields in the final output
        for key, value in log_entry.items():
            if isinstance(value, str):
                log_entry[key] = mask_sensitive_data(value)

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


def log_audit_event(
    action: str,
    user_id: str = "anonymous",
    ip_address: str = "unknown",
    details: str = "",
    db: Any = None, 
) -> None:
    """Helper to log structured audit events and optionally persist to Db."""
    # Mask details before logging
    masked_details = mask_sensitive_data(details)
    extra = {"user_id": user_id, "action": action, "ip_address": ip_address}
    audit_logger.info(masked_details, extra=extra)

    # Persist database event if active session was mapped
    if db:
        try:
            from albatross_pro.compliance.service import ComplianceService
            service = ComplianceService(db)
            service.log_event(action, user_id, ip_address, details)
        except Exception as e:
            audit_logger.error(f"Failed to persist audit event to DB: {str(e)}", extra=extra)
