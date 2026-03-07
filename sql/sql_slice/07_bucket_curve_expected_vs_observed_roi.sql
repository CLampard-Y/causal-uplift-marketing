-- ===================================
--  Q7 - Bucket curve: expected vs observed ROI
-- ===================================
-- Params: {{score_date}}, {{model_version}}, {{n_buckets}}, {{min_cell_n}}, {{cost_per_contact}}
-- Checked Table: analytics.uplift_scores, analytics.hillstrom_features
-- Note: 如果 Q0 查询失败，则 validated_scores 会按照设计返回 0 行

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
    COUNT(*) AS n_scored_customers,
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
    r.score_date,
    r.model_version,
    r.uplift_score
  FROM score_run_raw r
  CROSS JOIN contract_gate g
  WHERE g.n_duplicate_score_customers = 0
    AND g.n_missing_feature_customers = 0
    AND g.n_multi_match_feature_customers = 0
),
scored AS (
  SELECT
    s.customer_id,
    s.uplift_score,
    g.n_duplicate_score_customers,
    f.treatment::int   AS treatment,
    f.conversion::int  AS conversion
  FROM validated_scores s
  JOIN analytics.hillstrom_features f
    ON f.customer_id = s.customer_id
  CROSS JOIN contract_gate g
),
bucketed AS (
  SELECT
    *,
    NTILE({{n_buckets}}) OVER (ORDER BY uplift_score DESC NULLS LAST, customer_id) AS bucket
  FROM scored
),
by_bucket AS (
  SELECT
    bucket,
    COUNT(*) AS n_users,
    SUM((treatment = 1)::int) AS n_treated,
    SUM((treatment = 0)::int) AS n_control,
    MAX(n_duplicate_score_customers) AS n_dup_score_customers,
    AVG(conversion::float) FILTER (WHERE treatment = 1) AS cr_treated,
    AVG(conversion::float) FILTER (WHERE treatment = 0) AS cr_control,
    SUM(uplift_score) AS expected_inc_conv_bucket
  FROM bucketed
  GROUP BY bucket
),
with_uplift AS (
  SELECT
    bucket,
    n_users,
    n_treated,
    n_control,
    n_dup_score_customers,
    expected_inc_conv_bucket,
    (cr_treated - cr_control) AS observed_uplift_conv,
    (cr_treated - cr_control) * n_users AS observed_inc_conv_bucket
  FROM by_bucket
),
totals AS (
  SELECT SUM(n_users) AS total_users FROM with_uplift
)
SELECT
  w.bucket,
  w.n_users,
  w.n_treated,
  w.n_control,
  w.n_dup_score_customers,
  (w.n_treated < {{min_cell_n}} OR w.n_control < {{min_cell_n}}) AS is_small_cell,

  -- Expected (model accounting)
  w.expected_inc_conv_bucket,
  (w.expected_inc_conv_bucket
    / NULLIF((w.n_users * {{cost_per_contact}}::numeric), 0)
  ) AS expected_roi_conv_per_cost_marginal,

  -- Observed (experiment estimate)
  w.observed_uplift_conv,
  w.observed_inc_conv_bucket,
  (w.observed_inc_conv_bucket
    / NULLIF((w.n_users * {{cost_per_contact}}::numeric), 0)
  ) AS observed_roi_conv_per_cost_marginal,

  -- Cumulative coverage and ROI (highest-score buckets first)
  SUM(w.n_users) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_users,
  (SUM(w.n_users) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))::float
    / NULLIF(t.total_users::float, 0) AS cum_coverage,

  SUM(w.expected_inc_conv_bucket) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_expected_inc_conv,
  SUM(w.expected_inc_conv_bucket) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    / NULLIF(
      (SUM(w.n_users) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))
        * {{cost_per_contact}}::numeric,
      0
    ) AS cum_expected_roi_conv_per_cost,

  SUM(w.observed_inc_conv_bucket) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_observed_inc_conv,
  SUM(w.observed_inc_conv_bucket) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    / NULLIF(
      (SUM(w.n_users) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))
        * {{cost_per_contact}}::numeric,
      0
    ) AS cum_observed_roi_conv_per_cost
FROM with_uplift w
CROSS JOIN totals t
ORDER BY w.bucket;
