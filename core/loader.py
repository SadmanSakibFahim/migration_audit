import pandas as pd
from core.logger import get_logger
from typing import List, Dict, Optional
from core.config_models import SourceTableConfig, TargetTableConfig, ComplexMappingConfig
from sqlalchemy import create_engine, inspect

logger = get_logger(__name__)

def load_table(path: str, chunk_size: Optional[int] = None) -> Any:
    """
    Load a table from a CSV file or a database URI.
    Database format: 'dialect://user:pass@host:port/db/table_name'
    SQLite example: 'sqlite:///path/to/db.sqlite/table_name'
    
    If chunk_size is provided, returns an iterator (generator) of DataFrames.
    """
    # Check if path looks like a database URI
    db_prefixes = ['sqlite://', 'postgresql://', 'mysql://', 'mssql://', 'oracle://']
    is_db = any(path.startswith(prefix) for prefix in db_prefixes)

    if is_db:
        try:
            # For DB URIs, the last part is usually the table name
            # Format: 'connection_string/table_name'
            if '/' not in path.replace('://', ''):
                raise ValueError(f"Invalid DB URI format. Expected 'connection_uri/table_name', got: {path}")
            
            # Split from the right once to get the table name
            base_uri, table_name = path.rsplit('/', 1)
            
            logger.info(f"Connecting to database: {base_uri} (table: {table_name})")
            engine = create_engine(base_uri)
            
            # Use pandas read_sql_table
            if chunk_size:
                logger.info(f"Loading DB table '{table_name}' in chunks of {chunk_size}")
                return pd.read_sql_table(table_name, engine, chunksize=chunk_size)
            
            df = pd.read_sql_table(table_name, engine)
            logger.info(f"Successfully loaded {len(df)} rows from DB table '{table_name}'")
            return df
        except Exception as e:
            logger.error(f"Failed to load data from database '{path}': {e}")
            raise

    # Default to CSV loading
    import os
    if not os.path.exists(path):
        logger.error(f"File not found: {path}")
        raise FileNotFoundError(f"Data file missing: {path}")

    logger.info(f"Loading CSV from: {path}")
    try:
        if chunk_size:
            # returns TextFileReader iterator
            return pd.read_csv(path, chunksize=chunk_size)

        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        logger.warning(f"File '{path}' is empty (no columns/data).")
        return pd.DataFrame() # Return empty DF with no columns
    except Exception as e:
        logger.error(f"Unexpected error loading '{path}': {e}")
        raise
    
    if len(df) == 0:
        logger.info(f"Loaded empty table from '{path}' (Columns: {list(df.columns)})")
    
    # Try to convert columns to numeric, but only if they're already numeric-like
    # Don't convert date/string columns that would become NaN
    for col in df.columns:
        # Skip if column is already a string/object type (likely contains dates or text)
        if df[col].dtype == 'object':
            # Try to detect if it's actually numeric but stored as string
            # Only convert if ALL values can be converted to numeric
            sample_values = df[col].dropna().head(10)
            if len(sample_values) > 0:
                # Check if sample values are numeric strings
                try:
                    pd.to_numeric(sample_values, errors='raise')
                    # All sample values are numeric - safe to convert entire column
                    converted = pd.to_numeric(df[col], errors='coerce')
                    nan_count_before = df[col].isna().sum()
                    nan_count_after = converted.isna().sum()
                    new_nans = nan_count_after - nan_count_before
                    
                    if new_nans == 0:
                        # Conversion successful without creating NaNs
                        df[col] = converted
                    elif new_nans > 0:
                        logger.warning(
                            f"Column '{col}' in '{path}': Found {new_nans} non-numeric values. "
                            f"Keeping as string/object type to preserve data."
                        )
                        # Don't convert - keep as original type
                except (ValueError, TypeError):
                    # Contains non-numeric values - keep as object/string type
                    pass
        else:
            # Column is already numeric - ensure it's the right type
            converted = pd.to_numeric(df[col], errors='coerce')
            if converted.dtype in ['int64', 'float64']:
                df[col] = converted
    return df


def load_and_merge_sources(
    sources: List[SourceTableConfig],
    mapping_type: str,
    aggregation_strategy: Optional[str] = None
) -> pd.DataFrame:
    """
    Load and merge multiple source tables based on mapping type.
    
    Args:
        sources: List of source table configurations
        mapping_type: Type of mapping ('1:1', '1:N', 'N:1', 'N:M')
        aggregation_strategy: Strategy for N:1 mappings ('sum', 'count', 'merge', 'first', 'last')
    
    Returns:
        Merged DataFrame
    """
    if not sources:
        raise ValueError("No source tables provided")
    
    if len(sources) == 1:
        df = load_table(sources[0].path)
        # Apply column mapping if specified
        if sources[0].column_mapping:
            df = df.rename(columns=sources[0].column_mapping)
        return df
    
    # Multiple sources - need to merge
    dataframes = []
    for src in sources:
        df = load_table(src.path)
        # Apply column mapping if specified
        if src.column_mapping:
            df = df.rename(columns=src.column_mapping)
        dataframes.append(df)
    
    if mapping_type in ['N:1', 'N:M']:
        if aggregation_strategy == 'sum':
            # Sum numeric columns, keep first non-numeric
            merged = dataframes[0]
            for df in dataframes[1:]:
                # Find common columns
                common_cols = set(merged.columns) & set(df.columns)
                for col in common_cols:
                    if pd.api.types.is_numeric_dtype(merged[col]):
                        merged[col] = merged[col].fillna(0) + df[col].fillna(0)
                    else:
                        # For non-numeric, keep first value
                        pass
            return merged
        elif aggregation_strategy == 'merge':
            # Simple concatenation
            return pd.concat(dataframes, ignore_index=True)
        elif aggregation_strategy == 'count':
            # Count rows per group
            all_dfs = pd.concat(dataframes, ignore_index=True)
            # Group by primary key if available
            if sources[0].primary_key:
                pk_col = sources[0].column_mapping.get(sources[0].primary_key, sources[0].primary_key) if sources[0].column_mapping else sources[0].primary_key
                if pk_col in all_dfs.columns:
                    return all_dfs.groupby(pk_col).size().reset_index(name='count')
            return all_dfs
        else:
            # Default: concatenate
            return pd.concat(dataframes, ignore_index=True)
    else:
        # For 1:1 or 1:N, just concatenate
        return pd.concat(dataframes, ignore_index=True)


def load_and_merge_targets(
    targets: List[TargetTableConfig],
    mapping_type: str,
    split_strategy: Optional[str] = None
) -> pd.DataFrame:
    """
    Load and merge multiple target tables based on mapping type.
    
    Args:
        targets: List of target table configurations
        mapping_type: Type of mapping ('1:1', '1:N', 'N:1', 'N:M')
        split_strategy: Strategy for 1:N mappings ('copy', 'distribute', 'filter')
    
    Returns:
        Merged DataFrame
    """
    if not targets:
        raise ValueError("No target tables provided")
    
    if len(targets) == 1:
        df = load_table(targets[0].path)
        # Apply column mapping if specified
        if targets[0].column_mapping:
            df = df.rename(columns=targets[0].column_mapping)
        return df
    
    # Multiple targets - need to merge
    dataframes = []
    for tgt in targets:
        df = load_table(tgt.path)
        # Apply column mapping if specified
        if tgt.column_mapping:
            df = df.rename(columns=tgt.column_mapping)
        dataframes.append(df)
    
    if mapping_type in ['1:N', 'N:M']:
        if split_strategy == 'distribute':
            # For distributed data, concatenate
            return pd.concat(dataframes, ignore_index=True)
        elif split_strategy == 'filter':
            # Each target may have filtered data, concatenate
            return pd.concat(dataframes, ignore_index=True)
        else:
            # Default: concatenate
            return pd.concat(dataframes, ignore_index=True)
    else:
        # For 1:1 or N:1, concatenate
        return pd.concat(dataframes, ignore_index=True)