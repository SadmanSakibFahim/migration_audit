import os
import pytest
import pandas as pd
import numpy as np

# Global Test Environment Setup for FastAPI App
os.environ["SECRET_KEY"] = "test_secret_key_from_conftest"
os.environ["AUTH_DB_URI"] = "sqlite:///test_auth.db"
os.environ["ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1"

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
    n = 10_000
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "id": range(n),
            "amount": rng.uniform(1, 1000, n),
            "status": rng.choice(["active", "inactive", "pending"], n),
        }
    )

@pytest.fixture
def tmp_csv(tmp_path):
    """Factory fixture — returns a function that writes a DataFrame to a temp CSV."""
    def _write(df: pd.DataFrame, name: str = "data.csv") -> str:
        path = tmp_path / name
        df.to_csv(path, index=False)
        return str(path)
    return _write
