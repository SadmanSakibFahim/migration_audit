import pandas as pd
from core.logger import get_logger

logger = get_logger(__name__)

def load_table(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Try to convert columns to numeric, coercing non-numeric values to NaN
    for col in df.columns:
        # Attempt conversion
        converted = pd.to_numeric(df[col], errors='coerce')
        # Check if conversion produced NaN values that weren't there before
        nan_count_before = df[col].isna().sum()
        nan_count_after = converted.isna().sum()
        new_nans = nan_count_after - nan_count_before
        
        if new_nans > 0:
            logger.warning(
                f"Column '{col}' in '{path}': Found {new_nans} non-numeric values "
                f"that will be treated as missing. These values will be excluded from aggregate calculations."
            )
            df[col] = converted
        elif converted.dtype in ['int64', 'float64']:
            # Successfully converted to numeric
            df[col] = converted
    return df