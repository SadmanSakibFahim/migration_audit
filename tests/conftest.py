"""Shared pytest fixtures for the Migration Audit test suite.

Provides reusable test data and helpers across all QA test modules.
"""

import os
import pytest

# Global Test Environment already setup in root conftest.py

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
# TestResult Helpers
# ---------------------------------------------------------------------------


def make_result(status: CheckStatus, name: str = "test") -> TestResult:
    """Quick helper to build TestResult instances."""
    return TestResult(name=name, status=status, message=f"{status.value} result")
