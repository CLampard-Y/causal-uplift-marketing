# ===============================================
# Phase 1 MVP — Data Utility Functions
# ===============================================

from __future__ import annotations
from pathlib import Path
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
        # Raw data as all-string to avoid premature type coercion issues.
        raw_df = pd.read_csv(source_path, dtype=str)

        # Persist immutable raw TEXT snapshot before transformation (ELT lineage).
        stage_file = Path(raw_text_path)
        stage_file.parent.mkdir(parents=True, exist_ok=True)
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
