-- =======================================
--  Q0c - Key + grain QA: scores-to-features join coverage
-- =======================================
-- Grain: 1 scored customer_id -> exactly 1 feature row
-- Checked Table: analytics.uplift_scores, analytics.hillstrom_features
-- Check list:
--   1) Selected score-run customers must map 1:1 to feature rows
--   2) No missing feature rows for scored customers
--   3) No feature-table fanout for scored customers

-- Logic: 
--   1) 先分别把得分表和特征表按 customer_id 聚合
--   2) 再连接聚合结果，检查 scored customer -> feature row 是否保持 1:1

-- 为什么不直接对原表 LEFT JOIN 后数行数：
--   - 如果特征表本身已经发生 fanout，QA 查询本身也会被 fanout 污染

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

score_customers AS (
  SELECT
    customer_id,
    COUNT(*) AS score_rows_per_customer
  FROM score_run_raw
  GROUP BY customer_id
),

feature_customers AS (
  SELECT
    customer_id,
    COUNT(*) AS feature_rows_per_customer
  FROM analytics.hillstrom_features
  WHERE customer_id IS NOT NULL
  GROUP BY customer_id
),

joined AS (
  SELECT
    s.customer_id,
    s.score_rows_per_customer,
    COALESCE(f.feature_rows_per_customer, 0) AS feature_rows_per_customer
  FROM score_customers s
  LEFT JOIN feature_customers f
    ON f.customer_id = s.customer_id
)

SELECT
  (SELECT COUNT(*) FROM score_run_raw) AS score_rows_raw,
  COUNT(*) AS score_customers_distinct,
  (SELECT COUNT(*) FROM analytics.hillstrom_features WHERE customer_id IS NOT NULL) AS feature_rows_raw,
  (SELECT COUNT(DISTINCT customer_id) FROM analytics.hillstrom_features WHERE customer_id IS NOT NULL)
    AS feature_customers_distinct,

  SUM((score_rows_per_customer > 1)::int) AS n_duplicate_score_customers,

  -- Scored customers that are missing from the feature table.
  SUM((feature_rows_per_customer = 0)::int) AS n_missing_feature_customers,

  -- Scored customers that fan out to multiple feature rows.
  SUM((feature_rows_per_customer > 1)::int) AS n_multi_match_feature_customers,
  COALESCE(MAX(feature_rows_per_customer), 0) AS max_feature_matches_per_score_customer, -- Maximum fanout factor

  SUM(CASE WHEN feature_rows_per_customer > 0 THEN feature_rows_per_customer ELSE 0 END) AS joined_rows_raw,    -- Total joined feature rows across scored customers
  (SUM((feature_rows_per_customer = 1)::int)::float / NULLIF(COUNT(*)::float, 0)) AS join_coverage_exactly_one, -- Share with exact 1:1 match
  (SUM((feature_rows_per_customer > 0)::int)::float / NULLIF(COUNT(*)::float, 0)) AS join_coverage_any,         -- Share with any feature match
  
  -- Q0 gate: every scored customer must map to exactly one feature row.
  (
    SUM((score_rows_per_customer > 1)::int) = 0
    AND SUM((feature_rows_per_customer = 0)::int) = 0
    AND SUM((feature_rows_per_customer > 1)::int) = 0
) AS join_contract_ok
FROM joined;
