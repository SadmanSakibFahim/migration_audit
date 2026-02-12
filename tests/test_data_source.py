"""
Tests for the DataSource abstraction layer.

Tests CSVDataSource and DatabaseDataSource (using SQLite in-memory)
to verify the unified data loading interface.

Author: Howard Wolowitz (Software Engineering)
"""

import os
import tempfile

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from core.db.data_source import (
    CSVDataSource,
    DatabaseDataSource,
    DataSource,
    create_data_source,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_csv(tmp_path):
    """Create a temporary CSV file with sample data."""
    csv_path = tmp_path / "test_data.csv"
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "amount": [100.50, 200.75, 300.00, 150.25, 450.00],
        "status": ["active", "inactive", "active", "active", "inactive"],
    })
    df.to_csv(csv_path, index=False)
    return str(csv_path)


@pytest.fixture
def empty_csv(tmp_path):
    """Create an empty CSV file (headers only)."""
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("id,name,amount\n")
    return str(csv_path)


@pytest.fixture
def sqlite_db():
    """Create a SQLite in-memory database with test data."""
    engine = create_engine("sqlite:///:memory:")
    df = pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "amount": [100.50, 200.75, 300.00, 150.25, 450.00],
    })
    df.to_sql("test_table", engine, index=False, if_exists="replace")
    return engine


@pytest.fixture
def sqlite_db_file(tmp_path):
    """Create a SQLite file database with test data."""
    db_path = tmp_path / "test.db"
    uri = f"sqlite:///{db_path}"
    engine = create_engine(uri)
    df = pd.DataFrame({
        "id": [10, 20, 30],
        "value": [1.1, 2.2, 3.3],
    })
    df.to_sql("scores", engine, index=False, if_exists="replace")
    engine.dispose()
    return str(db_path)


# ---------------------------------------------------------------------------
# CSVDataSource Tests
# ---------------------------------------------------------------------------


class TestCSVDataSource:
    """Tests for CSVDataSource."""

    def test_load_basic(self, sample_csv):
        ds = CSVDataSource(sample_csv)
        df = ds.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert "id" in df.columns
        assert "name" in df.columns

    def test_load_file_not_found(self, tmp_path):
        ds = CSVDataSource(str(tmp_path / "nonexistent.csv"))
        with pytest.raises(FileNotFoundError):
            ds.load()

    def test_validate_exists(self, sample_csv):
        ds = CSVDataSource(sample_csv)
        assert ds.validate() is True

    def test_validate_not_found(self, tmp_path):
        ds = CSVDataSource(str(tmp_path / "nonexistent.csv"))
        with pytest.raises(FileNotFoundError):
            ds.validate()

    def test_get_schema(self, sample_csv):
        ds = CSVDataSource(sample_csv)
        schema = ds.get_schema()
        assert "id" in schema
        assert "name" in schema
        assert "amount" in schema

    def test_source_type(self, sample_csv):
        ds = CSVDataSource(sample_csv)
        assert ds.source_type == "csv"

    def test_source_identifier(self, sample_csv):
        ds = CSVDataSource(sample_csv)
        assert ds.source_identifier == sample_csv

    def test_load_empty_csv(self, empty_csv):
        ds = CSVDataSource(empty_csv)
        df = ds.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_load_with_delimiter(self, tmp_path):
        tsv_path = tmp_path / "data.tsv"
        tsv_path.write_text("id\tname\n1\tAlice\n2\tBob\n")
        ds = CSVDataSource(str(tsv_path), delimiter="\t")
        df = ds.load()
        assert len(df) == 2
        assert df.iloc[0]["name"] == "Alice"


# ---------------------------------------------------------------------------
# DatabaseDataSource Tests
# ---------------------------------------------------------------------------


class TestDatabaseDataSource:
    """Tests for DatabaseDataSource using SQLite in-memory."""

    def test_load_from_file_db(self, sqlite_db_file):
        uri = f"sqlite:///{sqlite_db_file}"
        ds = DatabaseDataSource(uri=uri, table_name="scores")
        df = ds.load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "id" in df.columns
        assert "value" in df.columns

    def test_load_with_custom_query(self, sqlite_db_file):
        uri = f"sqlite:///{sqlite_db_file}"
        ds = DatabaseDataSource(uri=uri, table_name="scores")
        df = ds.load(query="SELECT id FROM scores WHERE value > 2")
        assert len(df) == 2
        assert list(df.columns) == ["id"]

    def test_validate_table_exists(self, sqlite_db_file):
        uri = f"sqlite:///{sqlite_db_file}"
        ds = DatabaseDataSource(uri=uri, table_name="scores")
        assert ds.validate() is True

    def test_validate_table_not_found(self, sqlite_db_file):
        uri = f"sqlite:///{sqlite_db_file}"
        ds = DatabaseDataSource(uri=uri, table_name="nonexistent")
        assert ds.validate() is False

    def test_get_schema(self, sqlite_db_file):
        uri = f"sqlite:///{sqlite_db_file}"
        ds = DatabaseDataSource(uri=uri, table_name="scores")
        schema = ds.get_schema()
        assert "id" in schema
        assert "value" in schema

    def test_source_type(self, sqlite_db_file):
        uri = f"sqlite:///{sqlite_db_file}"
        ds = DatabaseDataSource(uri=uri, table_name="scores")
        assert ds.source_type == "sqlite"

    def test_safe_uri_masks_password(self):
        ds = DatabaseDataSource(
            uri="postgresql://admin:s3cret@db.example.com:5432/mydb",
            table_name="users",
        )
        assert "s3cret" not in ds._safe_uri
        assert "***" in ds._safe_uri


# ---------------------------------------------------------------------------
# Factory Tests
# ---------------------------------------------------------------------------


class TestCreateDataSource:
    """Tests for the create_data_source factory function."""

    def test_csv_from_path(self, sample_csv):
        ds = create_data_source(sample_csv)
        assert isinstance(ds, CSVDataSource)

    def test_db_from_uri(self, sqlite_db_file):
        uri = f"sqlite:///{sqlite_db_file}/scores"
        ds = create_data_source(uri)
        assert isinstance(ds, DatabaseDataSource)

    def test_db_from_uri_with_table_kwarg(self, sqlite_db_file):
        uri = f"sqlite:///{sqlite_db_file}"
        ds = create_data_source(uri, table_name="scores")
        assert isinstance(ds, DatabaseDataSource)

    def test_db_uri_without_table_raises(self):
        with pytest.raises(ValueError, match="table name"):
            create_data_source("postgresql://localhost/mydb")
