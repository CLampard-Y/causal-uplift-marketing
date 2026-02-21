# ===============================================
# Phase 1 MVP — Data Utility Functions
# ===============================================

from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

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

        # Temporal contamination check: verify visit is a true post-treatment variable
        # If control group visit rate >= treatment group, it suggests pre-treatment visits exist
        if "visit" in df.columns:
            # Convert visit to numeric (handle string '0'/'1' from raw data)
            # Use .astype(str) first to ensure consistent string type, then convert to int
            df_visit_clean = df["visit"].astype(str).str.strip()
            visit_numeric = pd.to_numeric(df_visit_clean, errors="coerce").fillna(0).astype(int)

            # Calculate visit rates by group
            control_mask = df["treatment"] == 0
            treatment_mask = df["treatment"] == 1
            control_visit_rate = visit_numeric[control_mask].mean()
            treatment_visit_rate = visit_numeric[treatment_mask].mean()

            # Output visit rates for transparency and debugging (BEFORE assertion)
            print(f"[Temporal Contamination Check]")
            print(f"  Control group visit rate:   {control_visit_rate:.4f} ({control_visit_rate:.2%})")
            print(f"  Treatment group visit rate: {treatment_visit_rate:.4f} ({treatment_visit_rate:.2%})")
            print(f"  Difference: {treatment_visit_rate - control_visit_rate:.4f}")

            # Only assert if the difference is meaningful (not just floating point error)
            assert control_visit_rate < treatment_visit_rate, (
                f"Temporal contamination detected: control visit rate ({control_visit_rate:.2%}) "
                f">= treatment visit rate ({treatment_visit_rate:.2%}). "
                "This suggests pre-treatment visits may exist, violating the post-treatment assumption."
            )

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
    

def build_features(df: pd.DataFrame, config) -> pd.DataFrame:
    """
    Build a feature matrix for causal/uplift baselines and persist to `config.paths.features_data`.
    Parameters
    ----------
    df : pd.DataFrame
        Cleaned dataset with treatment/outcomes and baseline covariates.
    config : Any
        Configuration object/dict with `paths.features_data` (or equivalent)
    Returns
    -------
    pd.DataFrame
        Final feature DataFrame saved to disk.
    """

    # Define function to get config path
    # Supports: 1. dict-like config['paths']['features_data']
    #           2. object-like config.paths.features_data
    def _get_config_path_features_data(cfg) -> Path:
        if cfg is None:
            raise ValueError("`config` must not be None.")

        # dict-like config
        if isinstance(cfg, dict):
            if "paths" not in cfg:
                raise KeyError("config['paths'] must exist and be a dict.")
            if not isinstance(cfg["paths"], dict):
                raise TypeError("config['paths'] must be a dict.")
            if "features_data" not in cfg["paths"]:
                raise KeyError("config['paths']['features_data'] must exist.")
            return Path(cfg["paths"]["features_data"])

        # object-like config
        # Check: config.paths.features_data
        paths = getattr(cfg, "paths", None)
        if paths is not None and hasattr(paths, "features_data"):
            # If passed, `paths.features_data` must exist
            return Path(paths.features_data)

        # object-like config
        # Check: config.features_data (allow a flat attribute or key)
        if hasattr(cfg, "features_data"):
            return Path(cfg.features_data)
        
        # Final error
        raise KeyError("config must provide `paths.features_data` (or dict equivalent).")

    try:
        if not isinstance(df, pd.DataFrame):
            raise TypeError("`df` must be a pandas DataFrame.")
        if df.empty:
            raise ValueError("`df` must not be empty.")

        required_cols = {
            "channel",
            "zip_code",
            "history",
            "mens",
            "womens",
            "treatment",
            "conversion",
            "spend",
        }
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns for feature engineering: {sorted(missing)}")

        features = df.copy()

        # -------------------------
        # 1) One-hot encoding
        # -------------------------
        channel_dummies = pd.get_dummies(
            features["channel"],
            prefix="channel",
            prefix_sep="_",
            dtype=np.int64,
        )
        zip_dummies = pd.get_dummies(
            features["zip_code"],
            prefix="zip",
            prefix_sep="_",
            dtype=np.int64,
        )
        features = pd.concat([features, channel_dummies, zip_dummies], axis=1)

        # -------------------------
        # 2) Derived features
        # -------------------------
        history_numeric = pd.to_numeric(features["history"], errors="raise")
        assert (history_numeric >= 0).all(), "`history` must be non-negative for log1p."

        # Defensive against log(0) -> -inf by construction (log1p).
        features["history_log"] = np.log1p(history_numeric)

        mens_numeric = pd.to_numeric(features["mens"], errors="raise")
        womens_numeric = pd.to_numeric(features["womens"], errors="raise")
        features["is_both_gender"] = ((mens_numeric > 0) & (womens_numeric > 0)).astype(np.int64)

        # -------------------------
        # 3) Architecture-level column drop
        # -------------------------
        drop_cols = ["segment", "history_segment", "channel", "zip_code", "visit"]

        # Drop `visit` because it is a downstream mediator of treatment assignment.
        # Keeping it would introduce mediator bias and can underestimate ATE.

        # Keep `spend` in the feature table (not as the modeling target) because it is extremely
        # zero-inflated; mean-based effect estimates are unstable, but it is useful for ROI simulation.

        features = features.drop(columns=[c for c in drop_cols if c in features.columns], errors="ignore")

        # -------------------------
        # 4) Type coercion (numeric-only table)
        # -------------------------
        # Convert any remaining boolean-like columns to int and enforce numeric dtypes.
        for col in list(features.columns):
            if pd.api.types.is_bool_dtype(features[col]):
                features[col] = features[col].astype(np.int64)
            if not pd.api.types.is_numeric_dtype(features[col]):
                features[col] = pd.to_numeric(features[col], errors="raise")

        # -------------------------
        # 5) Data quality assertions (must all run before return)
        # -------------------------
        # 1. Dtype: all columns must be numeric (int/float)
        assert all(
            pd.api.types.is_numeric_dtype(features[c]) for c in features.columns
        ), "All columns must be numeric (int/float)."

        # 2. NaN: no missing values anywhere
        assert features.isnull().sum().sum() == 0, "Data contains NaN values."

        # 3. Inf: no +/- inf anywhere
        values = features.to_numpy(dtype=float, copy=False)
        assert np.isfinite(values).all(), "Data contains inf or -inf values."

        # 4. Channel mutual exclusivity/completeness: row-wise sum of channel_* must equal 1
        channel_cols = [c for c in features.columns if c.startswith("channel_")]
        assert len(channel_cols) > 0, "One-hot encoding for channel produced no `channel_*` columns."
        assert (features[channel_cols].sum(axis=1) == 1).all(), "Channel one-hot columns must sum to 1 per row."

        # 5. Zip mutual exclusivity/completeness: row-wise sum of zip_* must equal 1
        zip_cols = [c for c in features.columns if c.startswith("zip_")]
        assert len(zip_cols) > 0, "One-hot encoding for zip_code produced no `zip_*` columns."
        assert (features[zip_cols].sum(axis=1) == 1).all(), "Zip one-hot columns must sum to 1 per row."

        # 6-8. Mandatory keep columns
        assert "treatment" in features.columns, "Missing required column: treatment."
        assert "conversion" in features.columns, "Missing required column: conversion."
        assert "spend" in features.columns, "Missing required column: spend."

        # 9-12. Mandatory dropped columns (must NOT exist)
        assert "segment" not in features.columns, "Forbidden column present: segment."
        assert "channel" not in features.columns, "Forbidden column present: channel."
        assert "zip_code" not in features.columns, "Forbidden column present: zip_code."
        assert "visit" not in features.columns, "Forbidden column present: visit."

        # 13. Column count bounds
        assert 15 <= features.shape[1] <= 20, "Feature DataFrame must have between 15 and 20 columns."

        # -------------------------
        # 6) Persist
        # -------------------------
        out_path = _get_config_path_features_data(config)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        features.to_csv(out_path, index=False)

        return features

    except Exception as exc:
        raise RuntimeError(f"build_features failed: {exc}") from exc

