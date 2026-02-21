"""
Data Source Abstraction Layer
=============================
Provides a unified interface for loading data from various sources
(CSV files, databases) into pandas DataFrames.

Author: Howard Wolowitz (Software Engineering)
Component: database
ADR: ADR-001 — SQLAlchemy chosen for database abstraction
"""

import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from core.audit.logger import get_logger
from core.db.exceptions import DatabaseConnectionError, DatabaseQueryError

logger = get_logger(__name__)


class DataSource(ABC):
    """Abstract base class for all data sources.

    Subclasses must implement `load()`, `validate()`, and `get_schema()`.
    This provides a consistent interface regardless of whether data
    comes from a CSV file, a database table, or any future source.
    """

    @abstractmethod
    def load(
        self,
        query: Optional[str] = None,
        chunk_size: Optional[int] = None,
    ) -> pd.DataFrame:
        """Load data from the source into a DataFrame.

        Args:
            query: Optional custom query/filter expression.
            chunk_size: If set, return an iterable of chunks instead of
                        a single DataFrame (for streaming large datasets).

        Returns:
            A pandas DataFrame (or iterator of DataFrames if chunk_size is set).
        """
        ...

    @abstractmethod
    def validate(self) -> bool:
        """Check that the data source is accessible and valid.

        Returns:
            True if the source is reachable and the data can be loaded.

        Raises:
            DatabaseConnectionError: If the source cannot be reached.
        """
        ...

    @abstractmethod
    def get_schema(self) -> Dict[str, str]:
        """Return column names and their inferred types.

        Returns:
            Dict mapping column name -> dtype string.
        """
        ...

    @property
    @abstractmethod
    def source_type(self) -> str:
        """Return a human-readable source type identifier (e.g. 'csv', 'postgresql')."""
        ...

    @property
    @abstractmethod
    def source_identifier(self) -> str:
        """Return a human-readable identifier for the specific source (path or URI)."""
        ...


# ---------------------------------------------------------------------------
# CSV Data Source
# ---------------------------------------------------------------------------


class CSVDataSource(DataSource):
    """Loads data from a CSV file on the local filesystem.

    Args:
        file_path: Absolute or relative path to the CSV file.
        encoding: File encoding (default: utf-8).
        delimiter: Column delimiter (default: comma).
    """

    def __init__(
        self,
        file_path: str,
        encoding: str = "utf-8",
        delimiter: str = ",",
    ):
        self.file_path = file_path
        self.encoding = encoding
        self.delimiter = delimiter

    # -- ABC implementation --------------------------------------------------

    def load(
        self,
        query: Optional[str] = None,
        chunk_size: Optional[int] = None,
    ) -> pd.DataFrame:
        """Load the CSV file into a DataFrame.

        Args:
            query: Ignored for CSV sources (reserved for future pandas query).
            chunk_size: If set, returns a TextFileReader for chunked reading.

        Returns:
            pd.DataFrame (or TextFileReader iterator when chunk_size is set).

        Raises:
            FileNotFoundError: If the CSV file does not exist.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(
                f"CSV file not found: '{self.file_path}'. "
                f"Please verify the path and try again."
            )

        logger.info(f"Loading CSV: {self.file_path}")

        read_kwargs: Dict[str, Any] = {
            "filepath_or_buffer": self.file_path,
            "encoding": self.encoding,
            "delimiter": self.delimiter,
            "on_bad_lines": "warn",
        }

        if chunk_size:
            read_kwargs["chunksize"] = chunk_size
            logger.info(f"Streaming CSV in chunks of {chunk_size} rows")
            return pd.read_csv(**read_kwargs)  # returns TextFileReader

        df = pd.read_csv(**read_kwargs)
        logger.info(f"Loaded {len(df)} rows × {len(df.columns)} columns from CSV")
        return df

    def validate(self) -> bool:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"CSV file not found: '{self.file_path}'")
        if os.path.getsize(self.file_path) == 0:
            logger.warning(f"CSV file is empty: '{self.file_path}'")
        return True

    def get_schema(self) -> Dict[str, str]:
        df = pd.read_csv(
            self.file_path,
            encoding=self.encoding,
            delimiter=self.delimiter,
            nrows=5,
        )
        return {col: str(dtype) for col, dtype in df.dtypes.items()}

    @property
    def source_type(self) -> str:
        return "csv"

    @property
    def source_identifier(self) -> str:
        return self.file_path


# ---------------------------------------------------------------------------
# Database Data Source
# ---------------------------------------------------------------------------


class DatabaseDataSource(DataSource):
    """Loads data from a relational database via SQLAlchemy.

    Supports PostgreSQL, MySQL, SQLite, SQL Server, and Oracle.

    Args:
        uri: SQLAlchemy connection URI (e.g. ``postgresql://user:pass@host/db``).
        table_name: Target table to query.
        schema: Optional database schema name.
    """

    def __init__(
        self,
        uri: str,
        table_name: str,
        schema: Optional[str] = None,
    ):
        self.uri = uri
        self.table_name = table_name
        self.schema = schema
        self._engine: Optional[Engine] = None

    @property
    def _db_engine(self) -> Engine:
        """Lazy-initialise the SQLAlchemy engine."""
        if self._engine is None:
            try:
                self._engine = create_engine(self.uri, pool_pre_ping=True)
                logger.info(f"Created database engine for {self._safe_uri}")
            except Exception as exc:
                raise DatabaseConnectionError(
                    self._safe_uri, exc
                ) from exc
        return self._engine

    @property
    def _safe_uri(self) -> str:
        """Return the URI with password masked for logging."""
        parts = self.uri.split("@")
        if len(parts) > 1:
            # Mask everything between :// and @
            prefix = parts[0].split("://")[0] if "://" in parts[0] else parts[0]
            return f"{prefix}://***@{parts[-1]}"
        return self.uri

    # -- ABC implementation --------------------------------------------------

    def load(
        self,
        query: Optional[str] = None,
        chunk_size: Optional[int] = None,
    ) -> pd.DataFrame:
        """Load data from the database table.

        Args:
            query: Custom SQL query. If omitted, ``SELECT * FROM <table>`` is used.
            chunk_size: If set, returns an iterator of DataFrames.

        Returns:
            pd.DataFrame (or iterator if chunk_size is set).

        Raises:
            DatabaseQueryError: If the SQL query fails.
            DatabaseConnectionError: If the database is unreachable.
        """
        sql = query or f"SELECT * FROM {self.table_name}"
        logger.info(f"Executing query on {self._safe_uri}: {sql[:80]}...")

        try:
            with self._db_engine.connect() as conn:
                if chunk_size:
                    return pd.read_sql(text(sql), conn, chunksize=chunk_size)
                df = pd.read_sql(text(sql), conn)
                logger.info(
                    f"Loaded {len(df)} rows × {len(df.columns)} columns "
                    f"from {self.table_name}"
                )
                return df
        except DatabaseConnectionError:
            raise
        except Exception as exc:
            raise DatabaseQueryError(
                sql, self._safe_uri, exc
            ) from exc

    def validate(self) -> bool:
        try:
            inspector = inspect(self._db_engine)
            tables = inspector.get_table_names(schema=self.schema)
            if self.table_name not in tables:
                logger.warning(
                    f"Table '{self.table_name}' not found. "
                    f"Available tables: {tables[:10]}{'...' if len(tables) > 10 else ''}"
                )
                return False
            return True
        except Exception as exc:
            raise DatabaseConnectionError(
                self._safe_uri, exc, self.table_name
            ) from exc

    def get_schema(self) -> Dict[str, str]:
        inspector = inspect(self._db_engine)
        columns = inspector.get_columns(self.table_name, schema=self.schema)
        return {col["name"]: str(col["type"]) for col in columns}

    @property
    def source_type(self) -> str:
        """Detect the database dialect from the URI."""
        dialect = (
            self.uri.split("://")[0].split("+")[0] if "://" in self.uri else "unknown"
        )
        return dialect

    @property
    def source_identifier(self) -> str:
        return f"{self._safe_uri}/{self.table_name}"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_data_source(path_or_uri: str, **kwargs) -> DataSource:
    """Factory function — choose the right DataSource based on the input.

    Args:
        path_or_uri: A file path (CSV) or a database connection URI.
        **kwargs: Extra arguments forwarded to the DataSource constructor.

    Returns:
        An appropriate DataSource instance.
    """
    if "://" in path_or_uri and not path_or_uri.startswith("/"):
        # Looks like a database URI
        table_name = kwargs.pop("table_name", None)
        if table_name is None:
            # Standard DB URIs look like: dialect://host/database
            # We only auto-extract table if there's an extra path segment
            # beyond the database name, e.g.: dialect:///path/to/file.db/table_name
            # For sqlite file URIs: sqlite:///path/to/db — count path segments after host
            scheme_rest = path_or_uri.split("://", 1)[1]
            # Count path depth after host (ignore leading slashes for sqlite)
            path_part = scheme_rest.split("/", 1)[1] if "/" in scheme_rest else ""
            segments = [s for s in path_part.split("/") if s]

            if len(segments) >= 2:
                # Has extra segment beyond DB name — treat last as table
                path_or_uri, table_name = path_or_uri.rstrip("/").rsplit("/", 1)
            else:
                raise ValueError(
                    "Database URI must include a table name. "
                    "Either pass table_name= or append /table_name to the URI."
                )

        return DatabaseDataSource(uri=path_or_uri, table_name=table_name, **kwargs)

    # Default: treat as a file path → CSV
    return CSVDataSource(file_path=path_or_uri, **kwargs)
