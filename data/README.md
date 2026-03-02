# Data Directory

This repository does not commit the Hillstrom dataset.

## Expected Layout

- `data/raw/hillstrom.csv`
  - The original Hillstrom Email Marketing dataset (CSV).
- `data/processed/`
  - Generated artifacts (cleaned data, feature matrix, matched data, CATE/Qini outputs).

## How To Run

1) Place the dataset at `data/raw/hillstrom.csv`.
2) Run notebooks in order under `notebooks/` (01 -> 05). The minimal acceptance gate is
   `notebooks/Phase1_DoD.ipynb`.

Notes:
- `data/raw/` and `data/processed/` are gitignored by design (see `.gitignore`).
- The pipeline will create timestamped raw snapshots under `data/raw/` for auditability.
