"""Validate SQL slice queries in DuckDB.

This is a local sandbox helper. It:
- Creates DuckDB views that map repo CSV artifacts to the documented tables
- Substitutes {{...}} params with demo defaults
- Executes all `sql/sql_slice/*.sql` files (in lexicographic order)

The intent is to validate the SQL patterns end-to-end without requiring
Postgres + COPY/DDL scaffolding.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import duckdb


@dataclass(frozen=True)
class BlockResult:
    name: str
    ok: bool
    error: str | None = None
    first_row: tuple | None = None


def _substitute_params(sql: str, params: dict[str, str]) -> str:
    for k, v in params.items():
        sql = sql.replace(k, v)
    return sql


def _validate_contract_row(name: str, row: tuple | None) -> str | None:
    if row is None:
        return None

    if name == "00a_key_grain_qa_hillstrom_features.sql":
        if not (row[0] == row[1] and all(v == 0 for v in row[2:])):
            return f"Feature table contract failed: {row}"

    if name == "00b_key_grain_qa_uplift_scores.sql":
        if not (row[4] == 0 and row[5] == 0 and row[6] == 0 and row[7] == 0 and row[9] == 0):
            return f"Score table contract failed: {row}"

    if name == "00c_key_grain_qa_scores_to_features_join_coverage.sql":
        if not (row[4] == 0 and row[5] == 0 and row[6] == 0 and bool(row[11])):
            return f"Score->feature join contract failed: {row}"

    return None


def main() -> int:
    sql_dir = Path("sql/sql_slice")
    sql_files = sorted(sql_dir.glob("*.sql"))
    print(f"found_sql_files={len(sql_files)}")

    features_path = Path("data/processed/hillstrom_features.csv")
    with features_path.open("r", encoding="utf-8", newline="") as f:
        feature_fieldnames = csv.DictReader(f).fieldnames or []

    user_segments_path = Path("data/processed/user_segments.csv")
    with user_segments_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        first_data_row = next(reader, None)
        score_runs = {
            (str(row.get("score_date", "")).strip(), str(row.get("model_version", "")).strip())
            for row in reader
        } if {"score_date", "model_version"}.issubset(fieldnames) else set()

    if first_data_row is None:
        raise ValueError("user_segments.csv must contain at least one data row")

    score_date_value = str(first_data_row.get("score_date", "")).strip() if "score_date" in fieldnames else "2026-03-05"
    if "score_date" in fieldnames and not score_date_value:
        raise ValueError("user_segments.csv contains blank score_date in first data row")

    model_version_value = str(first_data_row.get("model_version", "")).strip() if "model_version" in fieldnames else "demo"
    if "model_version" in fieldnames and not model_version_value:
        raise ValueError("user_segments.csv contains blank model_version in first data row")
    if score_runs:
        score_runs.add((score_date_value, model_version_value))
        if len(score_runs) != 1:
            raise ValueError(f"user_segments.csv must contain exactly one score run, found: {sorted(score_runs)}")

    customer_id_expr = "customer_id" if "customer_id" in fieldnames else "row_number() OVER ()"
    feature_customer_id_expr = "customer_id" if "customer_id" in feature_fieldnames else "row_number() OVER ()"
    score_date_expr = "CAST(score_date AS DATE)" if "score_date" in fieldnames else f"DATE '{score_date_value}'"
    model_version_expr = "model_version" if "model_version" in fieldnames else f"'{model_version_value}'"
    uplift_score_expr = "CAST(uplift_score AS DOUBLE)" if "uplift_score" in fieldnames else "cate::DOUBLE"

    con = duckdb.connect(database=":memory:")
    con.execute("CREATE SCHEMA IF NOT EXISTS analytics")

    # Demo mapping:
    # - user_segments.csv prefers explicit customer_id/score metadata when available;
    #   otherwise fall back to the historical row-order demo contract.
    # - hillstrom_features.csv prefers explicit customer_id when available; otherwise
    #   we fall back to row_number() for backward-compatible local demos.
    con.execute(
        f"""
        CREATE OR REPLACE VIEW analytics.hillstrom_features AS
        SELECT
          {feature_customer_id_expr} AS customer_id,
          *
        FROM read_csv_auto('data/processed/hillstrom_features.csv', header=true)
        """
    )
    con.execute(
        f"""
        CREATE OR REPLACE VIEW analytics.uplift_scores AS
        SELECT
          {customer_id_expr} AS customer_id,
          {score_date_expr} AS score_date,
          {model_version_expr} AS model_version,
          {uplift_score_expr} AS uplift_score
        FROM read_csv_auto('data/processed/user_segments.csv', header=true)
        """
    )

    params = {
        "{{cost_per_contact}}": "1.0",
        "{{min_cell_n}}": "200",
        "{{score_date}}": f"DATE '{score_date_value}'",
        "{{model_version}}": f"'{model_version_value}'",
        "{{n_buckets}}": "10",
        "{{budget_n_users}}": "5000",
    }

    results: list[BlockResult] = []
    for p in sql_files:
        raw = p.read_text(encoding="utf-8")
        sql = _substitute_params(raw.strip(), params)
        if "{{" in sql or "}}" in sql:
            results.append(
                BlockResult(
                    name=p.name,
                    ok=False,
                    error="Unresolved templated params remain after substitution",
                )
            )
            continue
        try:
            cur = con.execute(sql)
            first_row = cur.fetchone()
            if first_row is None:
                results.append(BlockResult(name=p.name, ok=False, error="Query returned no rows"))
                continue
            contract_error = _validate_contract_row(p.name, first_row)
            if contract_error:
                results.append(BlockResult(name=p.name, ok=False, error=contract_error, first_row=first_row))
                continue
            results.append(BlockResult(name=p.name, ok=True, first_row=first_row))
        except Exception as e:  # noqa: BLE001 - reporting tool
            results.append(BlockResult(name=p.name, ok=False, error=f"{type(e).__name__}: {e}"))

    for r in results:
        if r.ok:
            print(f"{r.name}: OK first_row={r.first_row}")
        else:
            print(f"{r.name}: FAIL error={r.error}")

    failed = [r for r in results if not r.ok]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
