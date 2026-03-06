-- =======================================
--  Uniqueness Check
-- =======================================
-- Checked Table: analytics.uplift_scores
-- Check list:
--   1) The uniqueness of customer_id in certain (score_date, model_version) pair
--   2) There are two conditions:
--     2.1) Duplicate customer (same customer_id, same uplift_score)
--     2.2) Conflicting duplicate customer (same customer_id, different uplift_score)

WITH score_run_raw AS (
  SELECT
    customer_id,
    score_date,
    model_version,
    uplift_score::numeric AS uplift_score
  FROM analytics.uplift_scores
  -- select certain (score_date, model_version) pair
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

-- 生成最终的单行汇总报告
SELECT
  r.score_date,
  r.model_version,

  COUNT(*) AS n_rows,
  COUNT(DISTINCT r.customer_id) AS n_customers,
  SUM((r.customer_id IS NULL)::int) AS n_null_customer_id,
  (COUNT(r.customer_id) - COUNT(DISTINCT r.customer_id)) AS n_duplicate_rows_non_null,    -- 重复的行数 (重复污染强度)
  SUM((r.uplift_score IS NULL)::int) AS n_null_scores,

  -- 防空处理
  COALESCE(d.n_duplicate_customers, 0) AS n_duplicate_customers,                          -- 出现重复的用户数 (受污染的用户数)
  COALESCE(d.max_rows_per_customer, 0) AS max_rows_per_customer,                          -- 重复行数最多的用户 (受污染的强度)
  COALESCE(d.n_conflicting_duplicate_customers, 0) AS n_conflicting_duplicate_customers   -- 得分矛盾的用户数
FROM score_run_raw r
CROSS JOIN dup_stats d
GROUP BY
  r.score_date,
  r.model_version,
  d.n_duplicate_customers,
  d.max_rows_per_customer,
  d.n_conflicting_duplicate_customers;
