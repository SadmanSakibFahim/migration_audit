import os

import pandas as pd
from sqlalchemy import create_engine

from core.audit.logger import get_logger

logger = get_logger(__name__)


def create_sqlite_db(db_path: str, table_name: str, df: pd.DataFrame):
    """
    Step-by-Step database creation for learning:
    1. Resolve the absolute path for the database.
    2. Create a SQLAlchemy engine for SQLite.
    3. Use Pandas 'to_sql' to write the DataFrame to the database.
    """
    abs_db_path = os.path.abspath(db_path)
    # Ensure the directory exists
    os.makedirs(os.path.dirname(abs_db_path), exist_ok=True)

    # SQLite connection string format: sqlite:///path/to/file.db
    # Note: Three slashes for relative, four for absolute on Unix,
    # but on Windows 'sqlite:///C:\path' works fine.
    connection_string = f"sqlite:///{abs_db_path}"

    logger.info(f"Creating SQLite DB at: {connection_string}")
    engine = create_engine(connection_string)

    # Write dataframe to SQL
    # if_exists='replace' ensures we start fresh
    # index=False prevents pandas from adding an extra 'index' column to the DB
    df.to_sql(table_name, engine, if_exists="replace", index=False)

    logger.info(f"Successfully created table '{table_name}' with {len(df)} rows.")
    return connection_string
