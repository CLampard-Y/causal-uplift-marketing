# ===============================================
# Phase 1 MVP — Data Utility Functions
# ===============================================

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd

# ELT approach: load raw data in string format, then apply transformation.
# Improves auditability and reproducibility when cleaning rules evolve.
def load_and_clean(
    # Raw data path
    filepath: str | Path,
    # Cleaned data path
    output_path: str | Path = Path("data/processed/hillstrom_cleaned.csv"),
    # Raw TEXT snapshot path
    raw_text_path: str | Path = Path("data/raw/hillstrom_raw_text.csv"),
    # Overwrite existing output file (default: False for idempotency)
    overwrite: bool = False,
# Type hint
) -> pd.DataFrame:
    """Load Hillstrom CSV, perform DQ cleaning, and persist cleaned output.
    Returns
    -------
    pd.DataFrame
        Cleaned dataframe with `treatment` column.
    """
    #if not isinstance(filepath, (str, Path)) or not filepath.strip():
    # strip() will create new object, will consume memory when filepath is large

    # Strictly distinguish error:
    # 1. filepath is not a string → TypeError
    # 2. filepath is whitespace-only → ValueError
    if not isinstance(filepath, (str, Path)):
        raise TypeError("`filepath` must be a non-empty string.")
    if not filepath or filepath.isspace():
        raise ValueError("`filepath` cannot be empty or whitespace-only.")
    
    #if not isinstance(output_path, (str, Path)) or not output_path.strip():
    if not isinstance(output_path, (str, Path)):
        raise TypeError("`output_path` must be a non-empty string.")
    if not output_path or output_path.isspace():
        raise ValueError("`output_path` cannot be empty or whitespace-only.")
    
    #if not isinstance(raw_text_path, (str, Path)) or not raw_text_path.strip():
    if not isinstance(raw_text_path, (str, Path)):
        raise TypeError("`raw_text_path` must be a non-empty string.")
    if not raw_text_path or raw_text_path.isspace():
        raise ValueError("`raw_text_path` cannot be empty or whitespace-only.")

    source_path = Path(filepath)
    if not source_path.exists():
        raise FileNotFoundError(f"Raw data file not found: {filepath}")

    try:
        # Timestamp(UTC+8) for reproducibility
        timestamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
        # Raw data as all-string to avoid premature type coercion issues.
        raw_df = pd.read_csv(source_path, dtype=str)

        # Persist immutable raw TEXT snapshot before transformation (ELT lineage).
        #stage_file = Path(raw_text_path).with_suffix(f".{timestamp}.csv")
        stage_file = Path(raw_text_path).parent / f"{Path(raw_text_path).stem}_{timestamp}.csv"     # e.g. data/raw/hillstrom_raw_text_20230101_123456.csv
        stage_file.parent.mkdir(parents=True, exist_ok=True)
        # index=False to avoid index column
        raw_df.to_csv(stage_file, index=False)

        # Reload from staged raw snapshot
        # guarantee downstream cleaning reads from the raw layer.
        staged_raw_df = pd.read_csv(stage_file, dtype=str)

        required_columns = {
            "recency",
            "history",
            "mens",
            "womens",
            "zip_code",
            "newbie",
            "channel",
            "segment",
            "conversion",
            "spend",
        }
        missing_columns = required_columns - set(staged_raw_df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {sorted(missing_columns)}")

        df = staged_raw_df.copy()

        # Seperate numeric and categorical columns
        numeric_columns = [
            "recency",
            "history",
            "mens",
            "womens",
            "newbie",
            "conversion",
            "spend",
        ]
        categorical_columns = [col for col in df.columns if col not in numeric_columns]

        # Fill numeric nulls using median for robustness against skewed distributions.
        for col in numeric_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
            if df[col].isnull().any():
                df[col] = df[col].fillna(df[col].median())

        # Fill categorical nulls using mode to preserve the most frequent state.
        for col in categorical_columns:
            # fill NaN with mode value
            # fill with random value will change the distribution
            # fill with mode maintains the distribution
            if df[col].isnull().any():
                mode_values = df[col].mode(dropna=True)
                if mode_values.empty:
                    raise ValueError(f"Cannot infer mode value for column: {col}")
                df[col] = df[col].fillna(mode_values.iloc[0])

