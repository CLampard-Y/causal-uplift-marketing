-- ===================================
--  Q3b - Customer revenue winsorized mean (p99, reporting only)
-- ===================================
-- Grain: treatment (treatment/control)
-- Checked Table: analytics.hillstrom_features
-- Motivation: 检查 customer_revenue（spend 的报表别名）对极端值的依赖程度
-- Note: 只用于报表稳健性 (避免被长尾极端数据主导) ，不影响主要结论。

WITH 
p AS (
  SELECT
    treatment::int AS treatment,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY COALESCE(spend::numeric, 0)) AS p99
  FROM analytics.hillstrom_features
  GROUP BY 1
),

base AS (
  SELECT
    f.treatment::int AS treatment,
    LEAST(COALESCE(f.spend::numeric, 0), p.p99) AS customer_revenue_winsor
  FROM analytics.hillstrom_features f
  JOIN p 
    ON p.treatment = f.treatment::int
)

SELECT
  treatment,
  AVG(customer_revenue_winsor) AS mean_customer_revenue_winsor_p99
FROM base
GROUP BY 1
ORDER BY 1;
