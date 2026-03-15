# SQL Slice: Experiment Sanity -> Uplift -> ROI Targeting

## Overview

**用途：** 把“SQL + 指标口径 + demo 查询动作”明确写清楚。它是主线分析之外的一个 **local SQL appendix / handoff demo**，用于展示 uplift score 如何被 SQL 消费，而不是生产投放 SOP。

**环境：** PostgreSQL 14+ 风格 SQL（SQL 使用 `{{cost_per_contact}}` 这类模板参数；本仓库主要通过 DuckDB 做本地演示与语法/口径校验。）

**以此为准：** `sql/sql_slice/*.sql`

**本地快速运行（不依赖数仓）：**

- 运行 `python scripts/validate_sql_slice_duckdb.py`（需先执行 `pip install duckdb`）。
- 该脚本会基于 `data/processed/*.csv` 创建 DuckDB 视图，并按顺序执行全部 `sql/sql_slice/*.sql`。

---

## 30s TL;DR

- **业务问题：** 主线 Phase 3 已选定 `Persuadables only` 作为默认离线策略；这里额外演示如果未来业务需要继续按 score 扩量，候选名单、分桶和预算查询在 SQL 中会长什么样。
- **粒度优先（口径约定）：** 每行代表 1 位客户（若迁移到真实环境，应使用业务侧稳定 `customer_id`；本仓库当前导出的 `user_segments.csv` 默认包含 repo-local surrogate `customer_id`，只保证与 `hillstrom_features.csv` 在本地复现链路中对齐；仅在兼容旧 CSV 时，DuckDB 才回退到 `row_number()` 代理键）。
- **指标口径（约定）：**
  - `conversion`: 0/1
  - `spend`: numeric = 用户在观测窗内的消费金额（在收入结果型 SQL 中常别名为 `customer_revenue`；**不是营销成本**；营销成本只来自 `cost_per_contact`）
  - `uplift_score`: 表示转化概率层面的 CATE 估计值（单位 = 概率点）
  - `ROI_conv_per_cost = SUM(uplift_score) / (n_targeted * cost_per_contact)`
- **关键门禁：**
  - **数据质量门禁（DQ gate）：** 一旦出现主键重复 / 空主键 / 连接扇出（join fanout）-> 停止继续解读 demo ROI / 名单结果，先修数据合约
  - **平衡性门禁（Balance gate）：** `abs(SMD) < 0.10`（否则优先怀疑过滤偏差，并视情况调整或限制结论）
  - **Targeting gate：** Q0 通过后，主线默认建议仍是 `Persuadables only`；若进入 SQL appendix 的 downstream expansion demo，再看 `uplift_score > 0` 的 top-K / cutoff / 预算建议，最终价值仍需由线上 A/B 完成验证闭环
- **推荐执行顺序：** `Q0 -> Q1 -> Q2 -> Q4 -> Q6`；`Q7/Q8/Q9` 仅在需要 SQL demo 或未来扩量分析时再执行

---

## Demo Data Contract

### Table A: experiment feature table

**表：** `analytics.hillstrom_features`

**最小字段要求：**

- `customer_id`（本仓库 local demo 使用的 join key；当前为 repo-local surrogate key，不等同业务侧稳定主键）
- `treatment`（0/1 实验分组）
- `conversion`（0/1 是否转化）
- `spend`（numeric outcome；表示观测窗内的消费金额，在部分收入结果型 SQL 中会别名为 `customer_revenue`；不是营销成本）

### Table B: uplift scoring table

**表：** `analytics.uplift_scores`

**最小字段要求：**

- `customer_id`
- `score_date`（date：本仓库 demo 中用于标记当前 score run 的本地批次日期）
- `model_version`（text：本仓库 demo 中用于标记当前 score run 的本地版本标签）
- `uplift_score`（numeric；表示 `conversion` 结果上的 CATE 估计值）

**唯一性要求（必须）：** 在本仓库 demo 合约下，`(customer_id, score_date, model_version)` 必须唯一。若存在重复，应视为数据异常；这用于保证本地 SQL slice 的 join / bucket / 名单查询不发生静默放大。

**仓库映射：** CATE 向量文件保存在 `data/processed/cate_vectors.npz`（常见 key：`cate_x/cate_s/cate_t`，并额外保存与 `hillstrom_features.csv` 对齐的 `customer_id`）；`data/processed/qini_results.json` 保存 held-out Qini 评估与 `best_learner` 元数据。`notebooks/05_segmentation_and_roi.ipynb` 会据此生成 `data/processed/user_segments.csv`；该文件包含 `customer_id`, `score_date`, `model_version`, `uplift_score` 这些 demo handoff 字段，同时保留 `cate` 作为同义列。`uplift_score` / `cate` 保存的是 `qini_results.json.meta.best_learner` 对应的全样本 CATE 向量；按当前持久化产物，该 learner 为 X-Learner，因此本次文件中它们与 `cate_x` 对齐。这里的 `customer_id` 只用于仓库内本地复现与 SQL demo；若迁移到真实环境，应替换为业务侧稳定主键。

---

## Metric Dictionary

**时间窗口（若迁移到真实环境）：** `conversion` / `spend` 应在同一个处理后观测窗口内度量，例如 `[assignment_ts, assignment_ts + 14 days)`。

**本仓库：** Hillstrom 数据集已经提供固定观测窗下的 `conversion` / `spend` 结果，直接视为冻结口径。

**ATE (conversion, diff-in-means)**

- $\widehat{ATE}=\hat p_T-\hat p_C$

**ATE standard error（normal approx）**

- $\mathrm{SE}(\widehat{ATE})=\sqrt{\frac{\hat p_T(1-\hat p_T)}{n_T}+\frac{\hat p_C(1-\hat p_C)}{n_C}}$

**SMD (balance diagnostic)**

- $\mathrm{SMD}(X)=\frac{\mu_T-\mu_C}{\sqrt{(\sigma_T^2+\sigma_C^2)/2}}$
- 经验规则：`abs(SMD) < 0.10` 可接受

**ROI (conversion per cost; CATE-sum accounting)**

- 基于打分的预期增量转化：`SUM(uplift_score)`
- `ROI_conv_per_cost = SUM(uplift_score) / (n_targeted * cost_per_contact)`

---

## Decision Map

下表用于快速把指标结论对应到下一步动作。它描述的是 SQL appendix 中的 demo / extension flow，而不是主线 Phase 3 已选定的 targeting policy；Q3 / Q5 属于支撑分析，Q7 / Q8 / Q9 只在需要扩量 demo 时再看。

| 步骤 | 读取内容 | 默认动作 | SQL 文件 |
|---|---|---|---|
| DQ gate（数据质量门禁） | PK 唯一性 / 空主键 / join 约束 | **停止继续解读 demo 结果**：若发生异常,先处理好数据再进行下一步 | [`00a_key_grain_qa_hillstrom_features.sql`](../sql/sql_slice/00a_key_grain_qa_hillstrom_features.sql), [`00b_key_grain_qa_uplift_scores.sql`](../sql/sql_slice/00b_key_grain_qa_uplift_scores.sql), [`00c_key_grain_qa_scores_to_features_join_coverage.sql`](../sql/sql_slice/00c_key_grain_qa_scores_to_features_join_coverage.sql) |
| Experiment sanity by arm | `arm_share_rows` / `arm_share_distinct` / `conversion_rate` / `avg_customer_revenue_per_user` 是否异常 | 若异常则回查数据接入、过滤条件与指标口径；通过后才继续 | [`01_experiment_sanity_by_arm.sql`](../sql/sql_slice/01_experiment_sanity_by_arm.sql) |
| Naive ATE + CI + ROI sanity | ATE + CI, `roi_conv_per_cost` | CI 跨 0 -> 不进行下一步，只保留实验观察；CI 为正 -> 进入策略层 | [`02_naive_ate_roi_ci.sql`](../sql/sql_slice/02_naive_ate_roi_ci.sql) |
| Balance gate（平衡性门禁） | `abs_smd` / `null_rate_diff` | `abs(SMD) >= 0.10` -> 降级结论并排查过滤偏差；通过后才允许解释异质性与策略 | [`04_balance_smd_missingness.sql`](../sql/sql_slice/04_balance_smd_missingness.sql) |
| Score-run health snapshot | `pct_scored` / score quantiles / 按 `score_date` 对比历史分布 | 若当前批次与历史分布明显偏离 -> 排查当前本地打分产物与元数据 | [`06_score_run_health_drift.sql`](../sql/sql_slice/06_score_run_health_drift.sql) |
| Bucket curve | bucket curve + cumulative ROI | 作为补充上界分析观察“若未来继续扩量，边际回报何时开始变差”；不改变主线 `Persuadables only` 策略 | [`07_bucket_curve_expected_vs_observed_roi.sql`](../sql/sql_slice/07_bucket_curve_expected_vs_observed_roi.sql) |
| Budget allocation helper | 预算上限内的 `uplift_score > 0` top-K | 若未来做 score-based 扩量，可在预算上限下演示 top-K / cutoff 建议（当前 SQL 未实现 ROI floor 过滤） | [`08_cutoff_solver_budget_argmax_expected_roi.sql`](../sql/sql_slice/08_cutoff_solver_budget_argmax_expected_roi.sql) |
| Activation list + rollup | top-K 候选名单 + 单行汇总 | 导出 downstream extension demo 候选名单；若未来用于真实触达，仍必须通过线上 A/B 收口，不能把离线分数当真值 | [`09a_activation_list_topk.sql`](../sql/sql_slice/09a_activation_list_topk.sql), [`09b_activation_expected_roi_rollup.sql`](../sql/sql_slice/09b_activation_expected_roi_rollup.sql) |

---

## Query Index

这部分只做导航，不重复展开指标与动作；具体判断见上方 `Decision Map`，每个 query 的输入 / 输出 / 判定规则见下方 `Pattern Cards`。

| Q# | Pattern | 角色 | SQL 文件 |
|---|---|---|---|
| Q0 | Key + grain QA | 主门禁：数据质量 | `00a`, `00b`, `00c` |
| Q1 | Experiment sanity by arm | 主链：实验体检 | `01` |
| Q2 | Naive ATE + CI + ROI sanity | 主链：方向性判断 | `02` |
| Q3 | Customer revenue long-tail + winsor | 支撑分析：报表稳健性 | `03a`, `03b` |
| Q4 | Balance diagnostic | 主门禁：平衡性 / 泄漏排查 | `04` |
| Q5 | Heterogeneity template | 支撑分析：异质性探索 | `05` |
| Q6 | Score-run health snapshot | 主链：打分批次健康检查 | `06` |
| Q7 | Bucket curve | appendix：扩量上界 / sensitivity 分析 | `07` |
| Q8 | Budget allocation helper | appendix：预算内 K / cutoff demo | `08` |
| Q9 | Activation list + rollup | appendix：候选名单 demo 导出 | `09a`, `09b` |

文件缩写说明（供上表快速查找）：

- `00a` = `sql/sql_slice/00a_key_grain_qa_hillstrom_features.sql`
- `00b` = `sql/sql_slice/00b_key_grain_qa_uplift_scores.sql`
- `00c` = `sql/sql_slice/00c_key_grain_qa_scores_to_features_join_coverage.sql`
- `01` = `sql/sql_slice/01_experiment_sanity_by_arm.sql`
- `02` = `sql/sql_slice/02_naive_ate_roi_ci.sql`
- `03a` = `sql/sql_slice/03a_revenue_long_tail_percentiles.sql`
- `03b` = `sql/sql_slice/03b_revenue_winsorized_mean_p99.sql`
- `04` = `sql/sql_slice/04_balance_smd_missingness.sql`
- `05` = `sql/sql_slice/05_heterogeneity_template_channel.sql`
- `06` = `sql/sql_slice/06_score_run_health_drift.sql`
- `07` = `sql/sql_slice/07_bucket_curve_expected_vs_observed_roi.sql`
- `08` = `sql/sql_slice/08_cutoff_solver_budget_argmax_expected_roi.sql`
- `09a` = `sql/sql_slice/09a_activation_list_topk.sql`
- `09b` = `sql/sql_slice/09b_activation_expected_roi_rollup.sql`

---

## Pattern Cards (compact runbook metadata)

> 用这组卡片快速确认“输入是什么 / 输出形式是什么 / 应采取什么动作”。完整 SQL 仍以 `sql/sql_slice/` 为准。

<details>
<summary><strong>Q0 — Key + grain QA</strong> · 主键与粒度门禁 · <code>00a</code> <code>00b</code> <code>00c</code></summary>

- 输入：`analytics.hillstrom_features`, `analytics.uplift_scores`
- 输出结构：key / NULL / duplicate 统计 + `join_contract_ok`
- 判定规则：只要出现主键重复 / 空主键 / `join_contract_ok = false`，就立即停止继续解读名单 / ROI demo
- 下一步动作：修 PK、去重规则和 join 约束；通过前不解读 ROI / cutoff / 投放结果
- 注意：repo-local surrogate `customer_id` 只用于本地校验与 demo join；若迁移到真实环境，必须替换为稳定业务主键

</details>

<details>
<summary><strong>Q1 — Experiment sanity by arm</strong> · 分组 / 转化 / 客户消费金额快检 · <code>01</code></summary>

- 输入：`analytics.hillstrom_features`（客户粒度）
- 输出结构：`treatment`, `arm_share_rows`, `arm_share_distinct`, `conversion_rate`, `n_conversions`, `avg_customer_revenue_per_user`
- 判定规则：`arm_share_rows` / `arm_share_distinct` / `conversion_rate` / `avg_customer_revenue_per_user` 明显异常 -> 回查数据接入、过滤条件和指标窗口
- 下一步动作：基础检查通过后，再进入 ATE / uplift / 投放分析
- 注意：`spend` 表示观测窗内的消费金额，在部分报表 SQL 中会别名为 `customer_revenue`；它不是营销成本

</details>

<details>
<summary><strong>Q2 — Naive ATE + CI + ROI sanity</strong> · 方向性校验 · <code>02</code></summary>

- 输入：`analytics.hillstrom_features`, `cost_per_contact`
- 输出结构：`ate_conversion`, `ate_conversion_ci95_*`, `roi_conv_per_cost`, `inc_customer_revenue_per_cost`
- 判定规则：CI 跨 0 -> 不放量，只保留实验观察；CI 为正 -> 允许进入排序 / 策略层
- 下一步动作：结合 Q6 / Q7 判断是否可扩量
- 注意：`inc_customer_revenue_per_cost` 反映客户收入结果，不等同利润率

</details>

<details>
<summary><strong>Q3 — Customer revenue long-tail + winsor</strong> · 报表稳健化 · <code>03a</code> <code>03b</code></summary>

- 输入：`analytics.hillstrom_features`
- 输出结构：`p50_customer_revenue`, `p90_customer_revenue`, `p99_customer_revenue`, `max_customer_revenue`, `mean_customer_revenue_winsor_p99`
- 判定规则：长尾明显 -> 报表优先使用 winsor 处理 / 分位数，而不是只看均值
- 下一步动作：向业务解释“高均值不一定可复现”
- 注意：这是报表稳健性处理，不改变主要因果结论

</details>

<details>
<summary><strong>Q4 — Balance diagnostic</strong> · 泄漏 / 过滤 QA · <code>04</code></summary>

- 输入：`analytics.hillstrom_features` 中当前 SQL 写死的 covariates（现与 `configs/config.yml` 保持一致）
- 输出结构：`covariate`, `abs_smd`, `null_rate_diff`
- 判定规则：`abs(SMD) >= 0.10` -> 降级结论 / 排查后验筛选 / 视情况补做调整
- 下一步动作：先修平衡性，再解释 uplift / ROI
- 注意：平衡性好不等于一定无偏，但平衡性差时不应继续放量

</details>

<details>
<summary><strong>Q5 — Heterogeneity template</strong> · channel 切片模板 · <code>05</code></summary>

- 输入：`analytics.hillstrom_features`, `min_cell_n`
- 输出结构：`segment_dim`, `n_treated`, `n_control`, `uplift_conversion`, `uplift_customer_revenue`
- 判定规则：只解读样本量达到门槛的分组；找到稳定高 uplift 的分组后再做分层策略
- 下一步动作：作为下一轮实验或策略护栏输入
- 注意：多切片默认是探索性分析，不将单次高点视为稳定结论

</details>

<details>
<summary><strong>Q6 — Score-run health snapshot</strong> · 监控快照 · <code>06</code></summary>

- 输入：`analytics.uplift_scores`, `model_version`
- 输出结构：`pct_scored`, `pct_positive_*`, `mean_score`, `p50_score`, `p90_score`, `p99_score`, `min_score`, `max_score`
- 判定规则：coverage 下滑或与历史相比 quantile 分布明显偏离 -> 排查当前本地打分产物与元数据（当前 SQL 负责输出快照，drift 需人工对比）
- 下一步动作：只有当前打分批次健康且与历史对比无明显异常后，才继续看 Q7 / Q8 / Q9
- 注意：这里的 dedup 仅用于监控，不能直接当作真实触达查询的兜底逻辑

</details>

<details>
<summary><strong>Q7 — Bucket curve</strong> · optional upper-bound / expansion analysis · <code>07</code></summary>

- 输入：`analytics.uplift_scores`, `analytics.hillstrom_features`, `score_date`, `model_version`, `n_buckets`, `min_cell_n`, `cost_per_contact`
- 输出结构：bucket 级别的 `expected_roi_conv_per_cost_marginal`, `observed_roi_conv_per_cost_marginal`, `cum_expected_roi_conv_per_cost`, `cum_observed_roi_conv_per_cost`
- 判定规则：把累计 / 边际 ROI 变化当作未来扩量的上界参考；小样本 bucket 仅供参考
- 下一步动作：把峰值 bucket 作为未来放量区间参考；如需建议 K / cutoff，转到 Q8；这不改变主线 `Persuadables only` 策略
- 注意：前提是 Q0 已通过；若存在 score 表重复行 / 特征表关联放大，Q7 会返回空结果，不再靠静默取平均来兜底

</details>

<details>
<summary><strong>Q8 — Budget allocation helper</strong> · optional budgeted top-K demo · <code>08</code></summary>

- 输入：`analytics.uplift_scores`, `analytics.hillstrom_features`, `score_date`, `model_version`, `budget_n_users`, `cost_per_contact`
- 输出结构：`recommended_n_users`, `cutoff_uplift_score`, `expected_incremental_conversions`, `total_cost`, `expected_roi_conv_per_cost`, `budget_utilization`
- 判定规则：默认目标是“预算内最大化 expected incremental conversions”，不是追求最小 K 下的最高 ROI 比值
- 下一步动作：若未来决定从 `Persuadables only` 向外扩量，可用建议 K 驱动 Q9 demo 名单导出，再用线上留出组 / A/B 完成验证闭环
- 注意：前提是 Q0 已通过；这是预算分配辅助查询，不声称给出全局最优解，且当前 SQL 未实现 ROI floor 过滤

</details>

<details>
<summary><strong>Q9 — Activation list + rollup</strong> · downstream extension demo · <code>09a</code> <code>09b</code></summary>

- 输入：`analytics.uplift_scores`, `analytics.hillstrom_features`, `score_date`, `model_version`, `budget_n_users`, `cost_per_contact`
- 输出结构：候选名单（`customer_id`, `rank`, `score_date`, `model_version`, 补充字段）+ 单行 ROI 汇总
- 判定规则：若执行 SQL appendix 的扩量 demo，则只导出 `uplift_score > 0` 的 top-K；Q0 未过时名单为空；score-run 健康需先由 Q6 人工确认，Q9 本身不做该校验
- 下一步动作：若未来把这类查询迁移到真实触达场景，必须保留留出组 / A/B 验证
- 注意：这里导出的只是 repo-local 候选名单 demo，不是已经接入投放系统的生产 activation feed

</details>

---

## Reference Queries

为便于快速浏览，这里只内嵌 2 段代表性 SQL。标准版本以 `sql/sql_slice/` 为准。

### Q2) Naive ATE + ROI sanity（+ CI）

<details>
<summary>SQL（规范版本：<code>sql/sql_slice/02_naive_ate_roi_ci.sql</code>）</summary>

```sql
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
  (ate_conversion * n_treated) AS inc_conversions_on_treated,             
  (ate_customer_revenue * n_treated) AS inc_customer_revenue_on_treated, 
  {{cost_per_contact}}::numeric AS cost_per_contact,                       
  (n_treated * {{cost_per_contact}}::numeric) AS treated_cost,            
  (ate_conversion * n_treated)
    / NULLIF((n_treated * {{cost_per_contact}}::numeric), 0) AS roi_conv_per_cost,             
  (ate_customer_revenue * n_treated)
    / NULLIF((n_treated * {{cost_per_contact}}::numeric), 0) AS inc_customer_revenue_per_cost
FROM stats;
```

</details>

### Q7) Bucket curve（expected vs observed, cumulative ROI）

<details>
<summary>SQL（规范版本：<code>sql/sql_slice/07_bucket_curve_expected_vs_observed_roi.sql</code>）</summary>

```sql
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
score_key_counts AS (
  SELECT
    customer_id,
    COUNT(*) AS score_rows_per_customer
  FROM score_run_raw
  GROUP BY customer_id
),
feature_key_counts AS (
  SELECT
    customer_id,
    COUNT(*) AS feature_rows_per_customer
  FROM analytics.hillstrom_features
  WHERE customer_id IS NOT NULL
  GROUP BY customer_id
),
contract_gate AS (
  SELECT
    COUNT(*) AS n_scored_customers,
    SUM((s.score_rows_per_customer > 1)::int) AS n_duplicate_score_customers,
    SUM((COALESCE(f.feature_rows_per_customer, 0) = 0)::int) AS n_missing_feature_customers,
    SUM((COALESCE(f.feature_rows_per_customer, 0) > 1)::int) AS n_multi_match_feature_customers
  FROM score_key_counts s
  LEFT JOIN feature_key_counts f
    ON f.customer_id = s.customer_id
),
validated_scores AS (
  SELECT
    r.customer_id,
    r.score_date,
    r.model_version,
    r.uplift_score
  FROM score_run_raw r
  CROSS JOIN contract_gate g
  WHERE g.n_duplicate_score_customers = 0
    AND g.n_missing_feature_customers = 0
    AND g.n_multi_match_feature_customers = 0
),
scored AS (
  SELECT
    s.customer_id,
    s.uplift_score,
    g.n_duplicate_score_customers,
    f.treatment::int   AS treatment,
    f.conversion::int  AS conversion
  FROM validated_scores s
  JOIN analytics.hillstrom_features f
    ON f.customer_id = s.customer_id
  CROSS JOIN contract_gate g
),
bucketed AS (
  SELECT
    *,
    NTILE({{n_buckets}}) OVER (ORDER BY uplift_score DESC NULLS LAST, customer_id) AS bucket
  FROM scored
),
by_bucket AS (
  SELECT
    bucket,
    COUNT(*) AS n_users,
    SUM((treatment = 1)::int) AS n_treated,
    SUM((treatment = 0)::int) AS n_control,
    MAX(n_duplicate_score_customers) AS n_dup_score_customers,
    AVG(conversion::float) FILTER (WHERE treatment = 1) AS cr_treated,
    AVG(conversion::float) FILTER (WHERE treatment = 0) AS cr_control,
    SUM(uplift_score) AS expected_inc_conv_bucket
  FROM bucketed
  GROUP BY bucket
),
with_uplift AS (
  SELECT
    bucket,
    n_users,
    n_treated,
    n_control,
    n_dup_score_customers,
    expected_inc_conv_bucket,
    (cr_treated - cr_control) AS observed_uplift_conv,
    (cr_treated - cr_control) * n_users AS observed_inc_conv_bucket
  FROM by_bucket
),
totals AS (
  SELECT SUM(n_users) AS total_users FROM with_uplift
)
SELECT
  w.bucket,
  w.n_users,
  w.n_treated,
  w.n_control,
  w.n_dup_score_customers,
  (w.n_treated < {{min_cell_n}} OR w.n_control < {{min_cell_n}}) AS is_small_cell,
  w.expected_inc_conv_bucket,
  (w.expected_inc_conv_bucket
    / NULLIF((w.n_users * {{cost_per_contact}}::numeric), 0)
  ) AS expected_roi_conv_per_cost_marginal,
  w.observed_uplift_conv,
  w.observed_inc_conv_bucket,
  (w.observed_inc_conv_bucket
    / NULLIF((w.n_users * {{cost_per_contact}}::numeric), 0)
  ) AS observed_roi_conv_per_cost_marginal,
  SUM(w.n_users) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_users,
  (SUM(w.n_users) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))::float
    / NULLIF(t.total_users::float, 0) AS cum_coverage,

  SUM(w.expected_inc_conv_bucket) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_expected_inc_conv,
  SUM(w.expected_inc_conv_bucket) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    / NULLIF(
      (SUM(w.n_users) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))
        * {{cost_per_contact}}::numeric,
      0
    ) AS cum_expected_roi_conv_per_cost,

  SUM(w.observed_inc_conv_bucket) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_observed_inc_conv,
  SUM(w.observed_inc_conv_bucket) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
    / NULLIF(
      (SUM(w.n_users) OVER (ORDER BY w.bucket ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW))
        * {{cost_per_contact}}::numeric,
      0
    ) AS cum_observed_roi_conv_per_cost
FROM with_uplift w
CROSS JOIN totals t
ORDER BY w.bucket;
```

</details>

---

## Pitfalls

- **连接扇出（join fanout）/ 重复记录**：会虚增 ROI / 转化率；Q0 未通过时，Q7 / Q8 / Q9 不应输出业务结果。
- **粒度漂移（grain drift）**：`user`、`session`、`order` 三种粒度必须冻结，不能混用。
- **不可走索引的谓词（non-sargable predicates）**：避免用 `date(ts)` / `col::text` 包裹索引列；优先对参数做类型转换，而不是转换索引列本身。
- **处理后泄漏（post-treatment leakage）**：协变量必须来自处理前阶段（本仓库已把 `visit` 视为中介变量并排除）。
- **时间窗对齐（time window alignment）**：`conversion` / `spend`（在部分收入报表中常别名为 `customer_revenue`）必须落在同一观测窗；时区错配可能引发难以及时察觉的数据错误。
- **多重比较（multiplicity）**：子群切得越细，越容易“看见并不存在的 uplift”；应设置 `min_cell_n`，默认只作探索性参考。

若未来迁移到真实环境，可参考以下典型索引（Postgres）：

- `hillstrom_features(customer_id)` unique
- `uplift_scores(score_date, model_version, customer_id)` unique
- `uplift_scores(score_date, model_version, uplift_score DESC, customer_id)` 用于 top-K

---

## Appendix: Dialect notes

- Postgres `SUM((cond)::int)` -> BigQuery `COUNTIF(cond)`
- Postgres `FILTER (WHERE ...)` -> BigQuery `AVG(IF(cond, x, NULL))` / `SUM(IF(cond, 1, 0))`
- Postgres `PERCENTILE_CONT` -> BigQuery `APPROX_QUANTILES` (approx) or analytic percentile
- `NTILE(n) OVER (ORDER BY score DESC)` 在主流方言中普遍支持
