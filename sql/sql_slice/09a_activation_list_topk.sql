-- ===================================
--  Q9a - Activation list / targeting export
-- ===================================
-- Params: {{score_date}}, {{model_version}}, {{budget_n_users}}
-- Checked Table: analytics.uplift_scores, analytics.hillstrom_features
-- Prereqs: 
--    1) requires Q0 contract to pass 
--    2) prior Q6 manual score-run health confirmation.
-- Logic: 有限预算下的 uplift_score > 0 top-K 名单

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
    r.score_date,
    r.model_version,
    r.uplift_score,
    sc.score_rows_per_customer
  FROM score_run_raw r
  JOIN score_key_counts sc
    ON sc.customer_id = r.customer_id
  CROSS JOIN contract_gate g
  WHERE g.n_duplicate_score_customers = 0
    AND g.n_missing_feature_customers = 0
    AND g.n_multi_match_feature_customers = 0
),
topk AS (
  -- Budget-capped positive-uplift targeting list.
  SELECT
    s.customer_id,
    s.score_date,
    s.model_version,
    s.uplift_score,
    s.score_rows_per_customer AS score_n_rows_raw
  FROM validated_scores s
  WHERE s.uplift_score > 0
  ORDER BY s.uplift_score DESC, s.customer_id
  LIMIT {{budget_n_users}}
),
selected AS (
  SELECT
    t.customer_id,
    t.score_date,
    t.model_version,
    t.uplift_score,
    t.score_n_rows_raw,
    f.newbie::int AS newbie,
    CASE
      WHEN f.channel_Phone = 1 THEN 'Phone'
      WHEN f.channel_Web = 1 THEN 'Web'
      ELSE 'Multichannel'
    END AS channel,
    f.recency::numeric AS recency,
    f.history::numeric AS history
  FROM topk t
  LEFT JOIN analytics.hillstrom_features f
    ON f.customer_id = t.customer_id
)
SELECT
  customer_id,
  uplift_score,
  ROW_NUMBER() OVER (ORDER BY uplift_score DESC, customer_id) AS rank,
  score_date,
  model_version,
  score_n_rows_raw,
  newbie,
  channel,
  recency,
  history
FROM selected
ORDER BY rank;
