-- ===================================
--  Rational Check of Data
-- ===================================
-- Grain: customer
-- Checked Table: analytics.hillstrom_features
-- Cheeck List:
--   1) Assignment Error:
--     - treatment/control 比例不对
--     - 说明抽样、过滤、导入有问题
--   2) Outcome Error:
--     - conversion rate 过高/过低、不像这个业务
--     - revenue 明显异常
--   3) Data Contract Error:
--     - 同一个用户重复
--     - customer revenue 出现负值
--     - 说明 metric pipeline 可能出错

WITH base AS (
  SELECT
    customer_id,
    treatment::int AS treatment,
    conversion::int AS conversion,
    spend::numeric AS customer_revenue
  FROM analytics.hillstrom_features
  WHERE customer_id IS NOT NULL
),

by_arm AS (
  SELECT
    treatment,
    COUNT(*) AS n_users,
    COUNT(DISTINCT customer_id) AS n_distinct_users,
    COUNT(*) - COUNT(DISTINCT customer_id) AS n_duplicate_rows,
    AVG(conversion::float) AS conversion_rate,
    SUM(conversion) AS n_conversions,
    AVG(customer_revenue) AS avg_customer_revenue_per_user,
    SUM((customer_revenue < 0)::int) AS n_negative_customer_revenue   -- record negative revenue
  FROM base
  GROUP BY treatment
)

SELECT
  treatment,
  n_users,
  n_distinct_users,
  n_duplicate_rows,
  (n_users::float / NULLIF(SUM(n_users) OVER (), 0)) AS arm_share_rows,
  (n_distinct_users::float / NULLIF(SUM(n_distinct_users) OVER (), 0)) AS arm_share_distinct,
  conversion_rate,
  n_conversions,
  avg_customer_revenue_per_user,
  n_negative_customer_revenue
FROM by_arm
ORDER BY treatment;
