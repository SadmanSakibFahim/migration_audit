"""Shared pytest fixtures for the Migration Audit test suite.

Created by: Ron Swanson (QA Lead)
Provides reusable test data and helpers across all QA test modules.
"""

import os
import pytest

# Global Test Environment Setup for FastAPI App
os.environ["SECRET_KEY"] = "test_secret_key_from_conftest"
os.environ["AUTH_DB_URI"] = "sqlite:///test_auth.db"
os.environ["ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"

import shutil

_AUDIT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "audit.yaml")
_AUDIT_CONFIG_BACKUP = os.path.join(os.path.dirname(__file__), "..", "config", "audit.yaml.bak")


@pytest.fixture(autouse=True, scope="session")
def protect_audit_yaml():
    """Back up config/audit.yaml before the test session; restore it after."""
    src = os.path.abspath(_AUDIT_CONFIG_PATH)
    bak = os.path.abspath(_AUDIT_CONFIG_BACKUP)
    if os.path.exists(src):
        shutil.copy2(src, bak)
    yield
    if os.path.exists(bak):
        shutil.copy2(bak, src)
        os.remove(bak)

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.audit.config_models import MappingConfig, TableConfig
from core.audit.enums import CheckStatus
from core.audit.result import TestResult

# ---------------------------------------------------------------------------
# DataFrame Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_src_df():
    """Standard source DataFrame for migration checks."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "email": ["a@x.com", "b@x.com", "c@x.com", "d@x.com", "e@x.com"],
            "amount": [100.0, 200.0, 300.0, 400.0, 500.0],
            "status": ["active", "active", "inactive", "active", "pending"],
        }
    )


@pytest.fixture
def sample_tgt_df():
    """Standard target DataFrame (exact copy of source)."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
            "email": ["a@x.com", "b@x.com", "c@x.com", "d@x.com", "e@x.com"],
            "amount": [100.0, 200.0, 300.0, 400.0, 500.0],
            "status": ["active", "active", "inactive", "active", "pending"],
        }
    )


@pytest.fixture
def empty_df():
    """Empty DataFrame with standard columns."""
    return pd.DataFrame(columns=["id", "name", "email", "amount", "status"])


@pytest.fixture
def large_src_df():
    """Large DataFrame for stress-testing (10K rows)."""
    import numpy as np

    n = 10_000
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "id": range(n),
            "amount": rng.uniform(1, 1000, n),
            "status": rng.choice(["active", "inactive", "pending"], n),
        }
    )


# ---------------------------------------------------------------------------
# Config Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def simple_table_meta():
    """Minimal TableConfig for tests that only need volume + aggregate checks."""
    return TableConfig(
        source="data/source/users.csv",
        target="data/target/users.csv",
        primary_key="id",
        aggregates=["amount"],
        mappings=[
            MappingConfig(
                columns=["status"], allowed_values=["active", "inactive", "pending"]
            ),
        ],
        data_constraints={"email": ["not_null"]},
    )


@pytest.fixture
def meta_no_checks():
    """TableConfig with no optional checks — only volume runs."""
    return TableConfig(
        source="data/source/users.csv",
        target="data/target/users.csv",
        primary_key="id",
    )


# ---------------------------------------------------------------------------
# Auth DB Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_db_session():
    """In-memory SQLite session with auth tables created."""
    from core.auth.models import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Temp File Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_csv(tmp_path):
    """Factory fixture — returns a function that writes a DataFrame to a temp CSV."""

    def _write(df: pd.DataFrame, name: str = "data.csv") -> str:
        path = tmp_path / name
        df.to_csv(path, index=False)
        return str(path)

    return _write


# ---------------------------------------------------------------------------
# TestResult Helpers
# ---------------------------------------------------------------------------


def make_result(status: CheckStatus, name: str = "test") -> TestResult:
    """Quick helper to build TestResult instances."""
    return TestResult(name=name, status=status, message=f"{status.value} result")
