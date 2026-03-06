# ===================================
#  Outcome Long-tail Sanity Check
# ===================================
# Grain: treatment (treatment/control)
# Checked Table: analytics.hillstrom_features
# Cheeck List: 
#   1) Percentiles (p50/p90/p99)
#   2) Mean (compare with p50)
#   3) Max (compare with p99)
#   4) Standard Deviation
WITH 
base AS (
  SELECT
    treatment::int AS treatment,
    spend::numeric AS customer_revenue
  FROM analytics.hillstrom_features
)

SELECT
  treatment,
  COUNT(*) AS n_users,
  MIN(customer_revenue) AS min_customer_revenue,

  PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY customer_revenue) AS p50_customer_revenue,
  PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY customer_revenue) AS p90_customer_revenue,
  PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY customer_revenue) AS p99_customer_revenue,
  
  MAX(customer_revenue) AS max_customer_revenue,
  AVG(customer_revenue) AS mean_customer_revenue,
  STDDEV_SAMP(customer_revenue) AS sd_customer_revenue
FROM base
GROUP BY treatment
ORDER BY treatment;
