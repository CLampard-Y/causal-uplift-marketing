-- ===================================
--  Score-run Health & Drift Monitoring
-- ===================================
-- Param: {{model_version}}
-- Checked Table: analytics.hillstrom_features
-- Cheeck List: 
--   1) Pct_scored
--   2) Quantiles
--   3) Min/Max Score

WITH 
scores AS (
  -- Monitoring-only dedup to avoid row-weighting under duplicates.
  -- Do not reuse this pattern for activation-safe targeting queries.
  SELECT
    score_date,
    model_version,
    customer_id,
    AVG(uplift_score)::numeric AS uplift_score,
    COUNT(*) AS n_rows_raw
  FROM analytics.uplift_scores
  WHERE model_version = {{model_version}}
    AND customer_id IS NOT NULL
  GROUP BY score_date, model_version, customer_id
)

SELECT
  score_date,
  model_version,
  COUNT(*) AS n_customers,
  SUM(n_rows_raw) AS n_rows_raw,
  SUM((n_rows_raw > 1)::int) AS n_dup_customers,
  SUM((uplift_score IS NULL)::int) AS n_null_score_customers,
  (COUNT(uplift_score)::float / NULLIF(COUNT(*)::float, 0)) AS pct_scored,
  AVG((uplift_score > 0)::int::float) AS pct_positive_non_null,
  AVG(CASE WHEN uplift_score > 0 THEN 1.0 ELSE 0.0 END) AS pct_positive_all_customers,
  AVG(uplift_score) AS mean_score,
  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY uplift_score) AS p50_score,
  PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY uplift_score) AS p90_score,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY uplift_score) AS p99_score,
  MIN(uplift_score) AS min_score,
  MAX(uplift_score) AS max_score
FROM scores
GROUP BY score_date, model_version
ORDER BY score_date DESC;
