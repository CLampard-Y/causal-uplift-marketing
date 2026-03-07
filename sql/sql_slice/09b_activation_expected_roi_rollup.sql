-- ===================================
--  Q9b - Activation expected ROI rollup
-- ===================================
-- Params: {{score_date}}, {{model_version}}, {{budget_n_users}}, {{cost_per_contact}}
-- Checked Table: analytics.uplift_scores, analytics.hillstrom_features
-- Prereqs: 
--    1) requires Q0 contract to pass 
--    2) prior Q6 manual score-run health confirmation.
-- Logic: roll up expected incremental conversions and expected_roi_conv_per_cost for the Q9a export

WITH score_run_raw AS (
  SELECT
    customer_id,
    score_date,
    model_version,
    uplift_score::numeric AS uplift_score
  FROM analytics.uplift_scores
  WHERE score_date = {{score_date}}
    AND model_version = {{model_version}}
    AND uplift_score IS NOT NULL
    AND customer_id IS NOT NULL
),
score_key_counts AS (
  SELECT
    customer_id,
    COUNT(*) AS score_rows_per_customer
  FROM score_run_raw
  GROUP BY customer_id
),
feature_key_counts AS (
  SELECT
    customer_id,
    COUNT(*) AS feature_rows_per_customer
  FROM analytics.hillstrom_features
  WHERE customer_id IS NOT NULL
  GROUP BY customer_id
),
contract_gate AS (
  SELECT
    SUM((s.score_rows_per_customer > 1)::int) AS n_duplicate_score_customers,
    SUM((COALESCE(f.feature_rows_per_customer, 0) = 0)::int) AS n_missing_feature_customers,
    SUM((COALESCE(f.feature_rows_per_customer, 0) > 1)::int) AS n_multi_match_feature_customers
  FROM score_key_counts s
  LEFT JOIN feature_key_counts f
    ON f.customer_id = s.customer_id
),
validated_scores AS (
  SELECT
    r.customer_id,
    r.uplift_score
  FROM score_run_raw r
  CROSS JOIN contract_gate g
  WHERE g.n_duplicate_score_customers = 0
    AND g.n_missing_feature_customers = 0
    AND g.n_multi_match_feature_customers = 0
),
selected AS (
  SELECT
    customer_id,
    uplift_score
  FROM validated_scores
  WHERE uplift_score > 0
  ORDER BY uplift_score DESC, customer_id
  LIMIT {{budget_n_users}}
)
SELECT
  COUNT(*) AS n_targeted,
  COALESCE(SUM(uplift_score), 0) AS expected_incremental_conversions,
  {{cost_per_contact}}::numeric AS cost_per_contact,
  (COUNT(*) * {{cost_per_contact}}::numeric) AS total_cost,
  (COALESCE(SUM(uplift_score), 0) / NULLIF((COUNT(*) * {{cost_per_contact}}::numeric), 0)) AS expected_roi_conv_per_cost
FROM selected;
