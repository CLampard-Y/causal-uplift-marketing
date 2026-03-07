-- ===================================
--  Heterogeneity Template (example: channel)
-- ===================================
-- Param: {{min_cell_n}}
-- Checked Table: analytics.hillstrom_features
-- Motivation: 协变量异质性 (Heterogeneity) 模板化观察
-- Cheeck List: 
--   1) Uplift conversion
--   2) Uplift customer revenue
WITH 
base AS (
  SELECT
    treatment::int  AS treatment,
    conversion::int AS conversion,
    spend::numeric  AS customer_revenue,
    CASE
      WHEN channel_Phone = 1 THEN 'Phone'
      WHEN channel_Web = 1 THEN 'Web'
      ELSE 'Multichannel'
    END AS segment_dim
  FROM analytics.hillstrom_features
),

agg AS (
  SELECT
    segment_dim,
    COUNT(*) AS n_users,
    SUM((treatment = 1)::int) AS n_treated,
    SUM((treatment = 0)::int) AS n_control,
    
    (AVG(conversion::float) FILTER (WHERE treatment = 1)
     - AVG(conversion::float) FILTER (WHERE treatment = 0)) AS uplift_conversion,
    (AVG(customer_revenue) FILTER (WHERE treatment = 1)
     - AVG(customer_revenue) FILTER (WHERE treatment = 0)) AS uplift_customer_revenue
  FROM base
  GROUP BY segment_dim
)

SELECT 
  *
FROM agg
WHERE n_treated >= {{min_cell_n}} 
  AND n_control >= {{min_cell_n}}
ORDER BY uplift_conversion DESC, uplift_customer_revenue DESC;
