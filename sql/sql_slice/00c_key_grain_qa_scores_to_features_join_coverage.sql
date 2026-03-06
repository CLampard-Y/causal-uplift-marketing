-- =======================================
--  Join Fan-Out Check
-- =======================================
-- Grain: customer
-- Checked Table: analytics.uplift_scores
-- Check list:
--   1) The uniqueness of customer_id in certain (score_date, model_version) pair

-- Logic: 
--   1) 先分别把原始得分数据 (analytics.uplift_scores) 和 JOIN 后的特征数据 (analytics.hillstrom_features) 按照 customer_id 进行聚合
--   2) 再把两个聚合后的表进行连接, 检查映射关系 (是否 1:1)

-- 为什么不直接把两个数据表进行 LEFT JOIN, 然后检查一共有多少行:
--   - 如果本来 JOIN 后的特征数据就发生了 Fan-Out, 那么 QA 查询本身也会被 Fan-Out 污染 (检测器被污染)

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

  -- 得分表 (uplift_scores) 有记录, 但是在特征表 (hillstrom_features) 里没有记录的用户
  SUM((feature_rows_per_customer = 0)::int) AS n_missing_feature_customers,

  -- 得分表 (uplift_scores) 有记录, 但是在特征表 (hillstrom_features) 里有多个记录的用户
  -- Fan-Out 标志
  SUM((feature_rows_per_customer > 1)::int) AS n_score_customers_with_multi_feature_match,
  COALESCE(MAX(feature_rows_per_customer), 0) AS max_feature_matches_per_score_customer,        -- 最大的 fan-out 数

  SUM(CASE WHEN feature_rows_per_customer > 0 THEN feature_rows_per_customer ELSE 0 END) AS joined_rows_raw,     -- 每个用户对应的特征表行数
  (SUM((feature_rows_per_customer = 1)::int)::float / NULLIF(COUNT(*)::float, 0)) AS join_coverage_exactly_one,  -- 1:1 匹配的用户比例
  (SUM((feature_rows_per_customer > 0)::int)::float / NULLIF(COUNT(*)::float, 0)) AS join_coverage_any,          -- 匹配到的用户比例
  
  -- 总判断闸门: 是否所有用户都 1:1 匹配 (既没有 Fan-Out,也没有空缺的特征表行)
  (
    SUM((score_rows_per_customer > 1)::int) = 0
    AND SUM((feature_rows_per_customer = 0)::int) = 0
    AND SUM((feature_rows_per_customer > 1)::int) = 0
  ) AS join_contract_ok
FROM joined;
