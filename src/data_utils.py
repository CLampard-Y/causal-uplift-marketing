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
    # Strictly distinguish error:
    # 1. filepath is not a string → TypeError
    # 2. filepath is whitespace-only → ValueError
    if not isinstance(filepath, (str, Path)):
        raise TypeError("`filepath` must be a non-empty path string or Path object.")
    if not str(filepath).strip():
        raise ValueError("`filepath` cannot be empty or whitespace-only.")

    #if not isinstance(output_path, (str, Path)) or not output_path.strip():
    if not isinstance(output_path, (str, Path)):
        raise TypeError("`output_path` must be a non-empty path string or Path object.")
    if not str(output_path).strip():
        raise ValueError("`output_path` cannot be empty or whitespace-only.")

    #if not isinstance(raw_text_path, (str, Path)) or not raw_text_path.strip():
    if not isinstance(raw_text_path, (str, Path)):
        raise TypeError("`raw_text_path` must be a non-empty path string or Path object.")
    if not str(raw_text_path).strip():
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

        # ------------------------------------------------
        #  Fill NaN columns (numeric & categorical)
        # ------------------------------------------------
        # Some models (e.g.Logistic Regression) cannot handle NaN values.
        # XGBoost's handle of NaN values are "black boxex", may cause unexpected behavior.


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

        # ------------------------------------------------
        #  Examination of segment values
        # ------------------------------------------------
        # Define allowed segment values
        allowed_segments = {"Mens E-Mail", "Womens E-Mail", "No E-Mail"}
        observed_segments = set(df["segment"].astype(str).unique())

        # Check for illegal segment values
        unknown_segments = observed_segments - allowed_segments
        if unknown_segments:
            raise ValueError(f"Unknown segment values detected: {sorted(unknown_segments)}")

        # Map experimental segment labels into binary treatment indicator.
        df["treatment"] = df["segment"].isin(["Mens E-Mail", "Womens E-Mail"]).astype(int)

        # DQ boundary control.
        df["recency"] = pd.to_numeric(df["recency"], errors="coerce").fillna(1).clip(1, 12)
        df["spend"] = pd.to_numeric(df["spend"], errors="coerce").fillna(0.0)
        df.loc[df["spend"] < 0, "spend"] = 0.0

        int_columns = ["recency", "mens", "womens", "newbie", "treatment", "conversion"]
        float_columns = ["history", "spend"]

        for col in int_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        for col in float_columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)

        # Error-checking assertions
        null_columns = df.isnull().sum()
        null_cols = null_columns[null_columns > 0]
        assert len(null_cols) == 0, f"Existing NaN values in columns: {null_cols.to_dict()}"
        assert set(df["treatment"].unique()) == {0, 1}, "'treatment' column values error"
        assert set(df["conversion"].unique()) <= {0, 1}, "'conversion' column values error"
        assert (df["spend"] >= 0).all(), "'spend' column contains negative values"
        assert 60000 <= len(df) <= 70000, "rows count error, check data source"
        assert 0.60 <= float(df["treatment"].mean()) <= 0.70, "Treatment ratio error"

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Idempotency guard: prevent accidental data loss
        if output_file.exists() and not overwrite:
            raise FileExistsError(
                f"Output file already exists: {output_file}. "
                "Set overwrite=True to replace it, or use a different output_path."
            )
        
        df.to_csv(output_file, index=False)

        return df

    except Exception as exc:
        raise RuntimeError(f"load_and_clean failed for {filepath}: {exc}") from exc
