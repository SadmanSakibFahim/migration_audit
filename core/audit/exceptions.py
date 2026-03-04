class AuditError(Exception):
    """Base exception for all migration audit errors."""

    pass


class DataLoadError(AuditError):
    """Raised when loading source or target data fails."""

    def __init__(self, table_name: str, source: str, original_exception: Exception) -> None:
        self.table_name = table_name
        self.source = source
        self.original_exception = original_exception
        super().__init__(
            f"Failed to load table '{table_name}' from '{source}': {original_exception}"
        )


class ConfigError(AuditError):
    """Raised when config is missing or invalid."""

    pass


class ValidationError(AuditError):
    """Raised when a check fails in a non-recoverable way."""

    pass
