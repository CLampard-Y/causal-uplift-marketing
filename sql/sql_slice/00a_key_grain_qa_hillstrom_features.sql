-- =======================================
--  Grain Check
-- =======================================
-- Grain: customer
-- Checked Table: analytics.hillstrom_features
-- Check list:
--   1) 1 row = 1 customer_id 
--   2) Duplicate rows
--   3) Null customer_id
--   4) Null treatment
--   5) Null conversion
--   6) Null spend

SELECT
  COUNT(*) AS n_rows,
  COUNT(DISTINCT customer_id) AS n_customers,
  -- ATTENTION: COUNT(*) will include NULL rows
  COUNT(*) - COUNT(DISTINCT customer_id) AS n_duplicate_rows,
  SUM((customer_id IS NULL)::int) AS n_null_customer_id,
  SUM((treatment IS NULL)::int) AS n_null_treatment,
  SUM((conversion IS NULL)::int) AS n_null_conversion,
  SUM((spend IS NULL)::int) AS n_null_spend
FROM analytics.hillstrom_features;
