-- ===================================
--  Budget Allocation Helper
-- ===================================
-- Params: {{score_date}}, {{model_version}}, {{budget_n_users}}, {{cost_per_contact}}
-- Checked Table: analytics.uplift_scores, analytics.hillstrom_features

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
ranked AS (
  SELECT
    customer_id,
    uplift_score,
    ROW_NUMBER() OVER (ORDER BY uplift_score DESC, customer_id) AS recommended_n_users,
    SUM(uplift_score) OVER (
      ORDER BY uplift_score DESC, customer_id
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS expected_incremental_conversions
  FROM validated_scores
  WHERE uplift_score > 0
),
curve AS (
  SELECT
    recommended_n_users,
    uplift_score AS cutoff_uplift_score,
    expected_incremental_conversions,
    {{cost_per_contact}}::numeric AS cost_per_contact,
    (recommended_n_users * {{cost_per_contact}}::numeric) AS total_cost,
    (expected_incremental_conversions / NULLIF((recommended_n_users * {{cost_per_contact}}::numeric), 0))
      AS expected_roi_conv_per_cost,
    (recommended_n_users::float / NULLIF({{budget_n_users}}::float, 0)) AS budget_utilization
  FROM ranked
  WHERE recommended_n_users <= {{budget_n_users}}
),
best AS (
  SELECT *
  FROM curve
  ORDER BY recommended_n_users DESC
  LIMIT 1
),
fallback AS (
  SELECT
    0 AS recommended_n_users,
    NULL::numeric AS cutoff_uplift_score,
    0::numeric AS expected_incremental_conversions,
    {{cost_per_contact}}::numeric AS cost_per_contact,
    0::numeric AS total_cost,
    NULL::numeric AS expected_roi_conv_per_cost,
    0::float AS budget_utilization
  WHERE NOT EXISTS (SELECT 1 FROM curve)
)
SELECT * FROM best
UNION ALL
SELECT * FROM fallback;
