import hashlib

import pandas as pd


class DataSanitizer:
    """
    Sanitizes dataframes by hashing PII and dropping high-risk columns.
    Used for GDPR/HIPAA compliance when generating reports.
    """

    PII_COLUMNS = ["email", "user_id", "username", "customer_email", "patient_id"]
    SENSITIVE_COLUMNS = ["ssn", "credit_card", "password", "medical_record_number"]

    @staticmethod
    def hash_value(value: str) -> str:
        if not isinstance(value, str):
            value = str(value)
        return hashlib.sha256(value.encode()).hexdigest()

    def sanitize(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return df

        sanitized_df = df.copy()

        # 1. Drop highly sensitive columns (Redaction)
        columns_to_drop = [
            col for col in self.SENSITIVE_COLUMNS if col in sanitized_df.columns
        ]
        if columns_to_drop:
            sanitized_df.drop(columns=columns_to_drop, inplace=True)

        # 2. Hash PII columns (Pseudonymization)
        for col in self.PII_COLUMNS:
            if col in sanitized_df.columns:
                sanitized_df[col] = sanitized_df[col].apply(self.hash_value)

        return sanitized_df
