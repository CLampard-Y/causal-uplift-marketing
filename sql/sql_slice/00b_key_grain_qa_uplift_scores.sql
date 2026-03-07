-- =======================================
--  Q0b - Key + grain QA: uplift_scores score-run uniqueness
-- =======================================
-- Grain: customer_id within one (score_date, model_version) score run
-- Checked Table: analytics.uplift_scores
-- Check list:
--   1) Enforce uniqueness of (customer_id, score_date, model_version)
--   2) Detect duplicate customer rows within the selected score run
--   3) Detect conflicting duplicate customer rows with different uplift_score
--   4) Any duplicate/conflict means the Q0 data-quality gate fails

WITH score_run_raw AS (
  SELECT
    customer_id,
    score_date,
    model_version,
    uplift_score::numeric AS uplift_score
  FROM analytics.uplift_scores
  -- Filter to one score run: (score_date, model_version).
  WHERE score_date = {{score_date}}
    AND model_version = {{model_version}}
),

by_customer AS (
  SELECT
    customer_id,
    COUNT(*) AS rows_per_customer,
    MIN(uplift_score) AS min_uplift_score,
    MAX(uplift_score) AS max_uplift_score
  FROM score_run_raw
  WHERE customer_id IS NOT NULL
  GROUP BY customer_id
),

dup_stats AS (
  SELECT
    SUM((rows_per_customer > 1)::int) AS n_duplicate_customers,
    MAX(rows_per_customer) AS max_rows_per_customer,
    SUM((rows_per_customer > 1 AND min_uplift_score <> max_uplift_score)::int)
      AS n_conflicting_duplicate_customers
  FROM by_customer
)

-- Single-row contract summary for the selected score run.
SELECT
  r.score_date,
  r.model_version,

  COUNT(*) AS n_rows,
  COUNT(DISTINCT r.customer_id) AS n_customers,
  SUM((r.customer_id IS NULL)::int) AS n_null_customer_id,
  (COUNT(r.customer_id) - COUNT(DISTINCT r.customer_id)) AS n_duplicate_rows_non_null,    -- 重复的行数 (重复污染强度)
  SUM((r.uplift_score IS NULL)::int) AS n_null_scores,

  COALESCE(d.n_duplicate_customers, 0) AS n_duplicate_customers,                        -- Number of customers affected by duplicates
  COALESCE(d.max_rows_per_customer, 0) AS max_rows_per_customer,                        -- Worst duplicate intensity for one customer
  COALESCE(d.n_conflicting_duplicate_customers, 0) AS n_conflicting_duplicate_customers -- Duplicate customers with conflicting scores
FROM score_run_raw r
CROSS JOIN dup_stats d
GROUP BY
  r.score_date,
  r.model_version,
  d.n_duplicate_customers,
  d.max_rows_per_customer,
  d.n_conflicting_duplicate_customers;
