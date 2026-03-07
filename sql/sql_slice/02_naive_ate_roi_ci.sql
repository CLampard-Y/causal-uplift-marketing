-- ===================================
--  Naive ATE & Rough ROI Check
-- ===================================
-- Grain: treatment (treatment/control)
-- Checked Table: analytics.hillstrom_features
-- Cheeck List: 
--   1) Naive ATE
--   2) Rough ROI

WITH 
base AS (
  SELECT
    treatment::int   AS treatment,
    conversion::int  AS conversion,
    spend::numeric   AS customer_revenue
  FROM analytics.hillstrom_features
),

by_arm AS (
  SELECT
    treatment,
    COUNT(*) AS n,
    AVG(conversion::float) AS cr,
    AVG(customer_revenue) AS mean_customer_revenue
  FROM base
  GROUP BY treatment
),

t AS (SELECT * FROM by_arm WHERE treatment = 1),

c AS (SELECT * FROM by_arm WHERE treatment = 0),

stats AS (
  SELECT
    t.n AS n_treated,
    c.n AS n_control,
    t.cr AS cr_treated,
    c.cr AS cr_control,
    (t.cr - c.cr) AS ate_conversion,
    SQRT(
      (t.cr * (1 - t.cr)) / NULLIF(t.n::float, 0)
      + (c.cr * (1 - c.cr)) / NULLIF(c.n::float, 0)
    ) AS ate_conversion_se,
    t.mean_customer_revenue AS customer_revenue_treated,
    c.mean_customer_revenue AS customer_revenue_control,
    (t.mean_customer_revenue - c.mean_customer_revenue) AS ate_customer_revenue
  FROM t 
  CROSS JOIN c
)

SELECT
  n_treated,
  n_control,
  cr_treated,
  cr_control,
  ate_conversion,
  ate_conversion_se,

  (ate_conversion - 1.96 * ate_conversion_se) AS ate_conversion_ci95_low,
  (ate_conversion + 1.96 * ate_conversion_se) AS ate_conversion_ci95_high,

  customer_revenue_treated,
  customer_revenue_control,
  ate_customer_revenue,

  -- 粗略的增量转化与增量收入计算
  (ate_conversion * n_treated) AS inc_conversions_on_treated,             -- 增量转化数
  (ate_customer_revenue * n_treated) AS inc_customer_revenue_on_treated,  -- 增量收入

  -- 粗略 ROI 计算
  {{cost_per_contact}}::numeric AS cost_per_contact,                       -- treated 单位成本设定
  (n_treated * {{cost_per_contact}}::numeric) AS treated_cost,             -- 总 treated 成本
  
  -- 每单位成本带来的增量转化
  (ate_conversion * n_treated)
    / NULLIF((n_treated * {{cost_per_contact}}::numeric), 0) AS roi_conv_per_cost,             
  
  -- 每单位成本带来的增量客户收入
  -- 这不是利润率 (revenue 不等于 margin)
  (ate_customer_revenue * n_treated)
    / NULLIF((n_treated * {{cost_per_contact}}::numeric), 0) AS inc_customer_revenue_per_cost
FROM stats;
