-- ===================================
--  Balance Diagnostic 
-- ===================================
-- Grain: Covariate (Pre-treatment)
-- Checked Table: analytics.hillstrom_features
-- Motivation: treatment/control 的协变量平衡性 (Uplift可行性第一步)
--   1) SMD (treatment/control)
--   2) Missingness Difference (treatment/control)


WITH 
base AS (
  SELECT
    treatment::int AS treatment,
    recency::numeric        AS recency,
    history::numeric        AS history,
    mens::numeric           AS mens,
    womens::numeric         AS womens,
    newbie::numeric         AS newbie,
    channel_Phone::numeric  AS channel_Phone,
    channel_Web::numeric    AS channel_Web,
    zip_Surburban::numeric  AS zip_Surburban,
    zip_Urban::numeric      AS zip_Urban
  FROM analytics.hillstrom_features
),
stats AS (
  SELECT
    ----------------------
    -- 1) Recency
    ----------------------
    AVG(recency) FILTER (WHERE treatment = 1) AS mean_recency_t,
    VAR_SAMP(recency) FILTER (WHERE treatment = 1) AS var_recency_t,
    AVG((recency IS NULL)::int::float) FILTER (WHERE treatment = 1) AS null_recency_t,
    AVG(recency) FILTER (WHERE treatment = 0) AS mean_recency_c,
    VAR_SAMP(recency) FILTER (WHERE treatment = 0) AS var_recency_c,
    AVG((recency IS NULL)::int::float) FILTER (WHERE treatment = 0) AS null_recency_c,

    ----------------------
    -- 2) History
    ----------------------
    AVG(history) FILTER (WHERE treatment = 1) AS mean_history_t,
    VAR_SAMP(history) FILTER (WHERE treatment = 1) AS var_history_t,
    AVG((history IS NULL)::int::float) FILTER (WHERE treatment = 1) AS null_history_t,
    AVG(history) FILTER (WHERE treatment = 0) AS mean_history_c,
    VAR_SAMP(history) FILTER (WHERE treatment = 0) AS var_history_c,
    AVG((history IS NULL)::int::float) FILTER (WHERE treatment = 0) AS null_history_c,
  
    ----------------------
    -- 3) Mens
    ----------------------
    AVG(mens) FILTER (WHERE treatment = 1) AS mean_mens_t,
    VAR_SAMP(mens) FILTER (WHERE treatment = 1) AS var_mens_t,
    AVG((mens IS NULL)::int::float) FILTER (WHERE treatment = 1) AS null_mens_t,
    AVG(mens) FILTER (WHERE treatment = 0) AS mean_mens_c,
    VAR_SAMP(mens) FILTER (WHERE treatment = 0) AS var_mens_c,
    AVG((mens IS NULL)::int::float) FILTER (WHERE treatment = 0) AS null_mens_c,

    ----------------------
    -- 4) Womens
    ----------------------
    AVG(womens) FILTER (WHERE treatment = 1) AS mean_womens_t,
    VAR_SAMP(womens) FILTER (WHERE treatment = 1) AS var_womens_t,
    AVG((womens IS NULL)::int::float) FILTER (WHERE treatment = 1) AS null_womens_t,
    AVG(womens) FILTER (WHERE treatment = 0) AS mean_womens_c,
    VAR_SAMP(womens) FILTER (WHERE treatment = 0) AS var_womens_c,
    AVG((womens IS NULL)::int::float) FILTER (WHERE treatment = 0) AS null_womens_c,

    ----------------------
    -- 5) Newbie
    ----------------------
    AVG(newbie) FILTER (WHERE treatment = 1) AS mean_newbie_t,
    VAR_SAMP(newbie) FILTER (WHERE treatment = 1) AS var_newbie_t,
    AVG((newbie IS NULL)::int::float) FILTER (WHERE treatment = 1) AS null_newbie_t,
    AVG(newbie) FILTER (WHERE treatment = 0) AS mean_newbie_c,
    VAR_SAMP(newbie) FILTER (WHERE treatment = 0) AS var_newbie_c,
    AVG((newbie IS NULL)::int::float) FILTER (WHERE treatment = 0) AS null_newbie_c,

    ----------------------
    -- 6) Channel_Phone
    ----------------------
    AVG(channel_Phone) FILTER (WHERE treatment = 1) AS mean_channel_phone_t,
    VAR_SAMP(channel_Phone) FILTER (WHERE treatment = 1) AS var_channel_phone_t,
    AVG((channel_Phone IS NULL)::int::float) FILTER (WHERE treatment = 1) AS null_channel_phone_t,
    AVG(channel_Phone) FILTER (WHERE treatment = 0) AS mean_channel_phone_c,
    VAR_SAMP(channel_Phone) FILTER (WHERE treatment = 0) AS var_channel_phone_c,
    AVG((channel_Phone IS NULL)::int::float) FILTER (WHERE treatment = 0) AS null_channel_phone_c,

    ----------------------
    -- 7) Channel_Web
    ----------------------
    AVG(channel_Web) FILTER (WHERE treatment = 1) AS mean_channel_web_t,
    VAR_SAMP(channel_Web) FILTER (WHERE treatment = 1) AS var_channel_web_t,
    AVG((channel_Web IS NULL)::int::float) FILTER (WHERE treatment = 1) AS null_channel_web_t,
    AVG(channel_Web) FILTER (WHERE treatment = 0) AS mean_channel_web_c,
    VAR_SAMP(channel_Web) FILTER (WHERE treatment = 0) AS var_channel_web_c,
    AVG((channel_Web IS NULL)::int::float) FILTER (WHERE treatment = 0) AS null_channel_web_c,

    ----------------------
    -- 8) Zip_Surburban
    ----------------------
    AVG(zip_Surburban) FILTER (WHERE treatment = 1) AS mean_zip_surburban_t,
    VAR_SAMP(zip_Surburban) FILTER (WHERE treatment = 1) AS var_zip_surburban_t,
    AVG((zip_Surburban IS NULL)::int::float) FILTER (WHERE treatment = 1) AS null_zip_surburban_t,
    AVG(zip_Surburban) FILTER (WHERE treatment = 0) AS mean_zip_surburban_c,
    VAR_SAMP(zip_Surburban) FILTER (WHERE treatment = 0) AS var_zip_surburban_c,
    AVG((zip_Surburban IS NULL)::int::float) FILTER (WHERE treatment = 0) AS null_zip_surburban_c,

    ----------------------
    -- 9) Zip_Urban
    ----------------------
    AVG(zip_Urban) FILTER (WHERE treatment = 1) AS mean_zip_urban_t,
    VAR_SAMP(zip_Urban) FILTER (WHERE treatment = 1) AS var_zip_urban_t,
    AVG((zip_Urban IS NULL)::int::float) FILTER (WHERE treatment = 1) AS null_zip_urban_t,
    AVG(zip_Urban) FILTER (WHERE treatment = 0) AS mean_zip_urban_c,
    VAR_SAMP(zip_Urban) FILTER (WHERE treatment = 0) AS var_zip_urban_c,
    AVG((zip_Urban IS NULL)::int::float) FILTER (WHERE treatment = 0) AS null_zip_urban_c
  FROM base
),

covariate_rows AS (
  SELECT 
    *
  FROM stats s
  CROSS JOIN LATERAL (
    VALUES
      ('recency', s.mean_recency_t, s.mean_recency_c, s.var_recency_t, s.var_recency_c, s.null_recency_t, s.null_recency_c),
      ('history', s.mean_history_t, s.mean_history_c, s.var_history_t, s.var_history_c, s.null_history_t, s.null_history_c),
      ('mens', s.mean_mens_t, s.mean_mens_c, s.var_mens_t, s.var_mens_c, s.null_mens_t, s.null_mens_c),
      ('womens', s.mean_womens_t, s.mean_womens_c, s.var_womens_t, s.var_womens_c, s.null_womens_t, s.null_womens_c),
      ('newbie', s.mean_newbie_t, s.mean_newbie_c, s.var_newbie_t, s.var_newbie_c, s.null_newbie_t, s.null_newbie_c),
      ('channel_Phone', s.mean_channel_phone_t, s.mean_channel_phone_c, s.var_channel_phone_t, s.var_channel_phone_c, s.null_channel_phone_t, s.null_channel_phone_c),
      ('channel_Web', s.mean_channel_web_t, s.mean_channel_web_c, s.var_channel_web_t, s.var_channel_web_c, s.null_channel_web_t, s.null_channel_web_c),
      ('zip_Surburban', s.mean_zip_surburban_t, s.mean_zip_surburban_c, s.var_zip_surburban_t, s.var_zip_surburban_c, s.null_zip_surburban_t, s.null_zip_surburban_c),
      ('zip_Urban', s.mean_zip_urban_t, s.mean_zip_urban_c, s.var_zip_urban_t, s.var_zip_urban_c, s.null_zip_urban_t, s.null_zip_urban_c)
  ) v(covariate, mean_treated, mean_control, var_treated, var_control, null_rate_treated, null_rate_control)
)

SELECT
  covariate,
  mean_treated,
  mean_control,
  (mean_treated - mean_control)
    / NULLIF(SQRT((var_treated + var_control) / 2.0), 0) AS smd,
  ABS(
    (mean_treated - mean_control)
      / NULLIF(SQRT((var_treated + var_control) / 2.0), 0)
  ) AS abs_smd,
  null_rate_treated,
  null_rate_control,
  (null_rate_treated - null_rate_control) AS null_rate_diff
FROM covariate_rows
ORDER BY abs_smd DESC, covariate;
