import random
import string
from datetime import datetime, timedelta
from typing import List

import numpy as np
import pandas as pd


def generate_random_string(length=10) -> str:
    """Generate a random string of fixed length."""
    letters = string.ascii_lowercase
    return "".join(random.choice(letters) for i in range(length))


def generate_base_data(rows: int = 100) -> pd.DataFrame:
    """
    Generate a clean base dataframe with various data types.
    - id: sequence int
    - name: random string
    - value: random float
    - category: random choice from list
    - date: random date
    """
    data = {
        "id": range(1, rows + 1),
        "name": [generate_random_string() for _ in range(rows)],
        "amount": [round(random.uniform(10.0, 1000.0), 2) for _ in range(rows)],
        "category": [random.choice(["A", "B", "C", "D"]) for _ in range(rows)],
        "status": [
            random.choice(["Active", "Inactive", "Pending"]) for _ in range(rows)
        ],
        "created_at": [
            datetime.now() - timedelta(days=random.randint(0, 365)) for _ in range(rows)
        ],
    }
    return pd.DataFrame(data)


def inject_volume_loss(df: pd.DataFrame, loss_pct: float = 0.05) -> pd.DataFrame:
    """Randomly drop rows to simulate volume loss."""
    if loss_pct <= 0:
        return df.copy()

    rows_to_keep = int(len(df) * (1 - loss_pct))
    return (
        df.sample(n=rows_to_keep, random_state=42)
        .sort_values("id")
        .reset_index(drop=True)
    )


def inject_data_corruption(
    df: pd.DataFrame,
    col_name: str,
    corruption_pct: float = 0.05,
    corruption_type: str = "null",
) -> pd.DataFrame:
    """
    Inject corruption into a specific column.
    types: 'null', 'zero', 'negative', 'garbage'
    """
    df_mod = df.copy()
    num_corrupt = int(len(df) * corruption_pct)
    if num_corrupt == 0:
        return df_mod

    indices = np.random.choice(df.index, num_corrupt, replace=False)

    if corruption_type == "null":
        df_mod.loc[indices, col_name] = np.nan
    elif corruption_type == "zero":
        df_mod.loc[indices, col_name] = 0
    elif corruption_type == "negative":
        # Assuming numeric
        df_mod.loc[indices, col_name] = df_mod.loc[indices, col_name] * -1
    elif corruption_type == "garbage":
        df_mod.loc[indices, col_name] = "INVALID"

    return df_mod


def inject_duplicate_ids(df: pd.DataFrame, pct: float = 0.05) -> pd.DataFrame:
    """Duplicate existing rows to simulate uniqueness violation (if ID is unique)."""
    if pct <= 0:
        return df.copy()

    num_dupes = int(len(df) * pct)
    dupes = df.sample(n=num_dupes, random_state=42)
    return pd.concat([df, dupes]).sort_values("id").reset_index(drop=True)


def inject_special_chars(
    df: pd.DataFrame, col_name: str, pct: float = 0.1
) -> pd.DataFrame:
    """Inject special characters (emojis, unicode) into string column."""
    df_mod = df.copy()
    num_corrupt = int(len(df) * pct)
    indices = np.random.choice(df.index, num_corrupt, replace=False)

    special_chars = ["🎉", "ñ", "ü", "🤔", "test,comma", "line\nbreak"]

    for idx in indices:
        original = str(df_mod.loc[idx, col_name])
        df_mod.loc[idx, col_name] = original + random.choice(special_chars)

    return df_mod


def drop_column(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
    """Drop a column from the dataframe."""
    return df.drop(columns=[col_name])


def split_dataframe(df: pd.DataFrame, num_chunks: int = 2) -> List[pd.DataFrame]:
    """Split dataframe into roughly equal chunks."""
    return np.array_split(df, num_chunks)


def generate_related_data(
    parent_df: pd.DataFrame, rows: int = 200, fk_col: str = "user_id"
) -> pd.DataFrame:
    """Generate child data that references parent_df ids."""
    parent_ids = parent_df["id"].tolist()
    data = {
        "id": range(1, rows + 1),
        fk_col: [random.choice(parent_ids) for _ in range(rows)],
        "order_value": [round(random.uniform(5.0, 500.0), 2) for _ in range(rows)],
        "order_date": [
            datetime.now() - timedelta(days=random.randint(0, 30)) for _ in range(rows)
        ],
    }
    return pd.DataFrame(data)
