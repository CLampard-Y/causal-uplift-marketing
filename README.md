# Causal Uplift Marketing Analysis

> Causal inference, uplift modeling, and ROI-oriented targeting on the Hillstrom email marketing RCT.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)

Quick navigation: [Dashboard Showcase](#dashboard-showcase) · [Start Here](#start-here) · [Key Results](#key-results) · [Decision Snapshot](#decision-snapshot) · [Documentation Map](#documentation-map) · [Quickstart](#quickstart) · [Limitations](#limitations)

## Overview

This repository studies not only whether a campaign works on average, but who should be targeted under a constrained budget.

本项目聚焦一个直接营销决策问题：仅知道邮件活动“平均有效”还不够，真正影响投放效率的是“预算应该优先给谁”。

基于 Hillstrom 的 `64,000` 用户随机对照实验数据，项目实现了一条从因果基线到策略落地的完整分析链路：

- 用 EDA 与随机化平衡检查建立可信基线
- 用 Propensity Score Matching (PSM) 把去偏流程做成可迁移、可审计的 pipeline
- 用 S/T/X-Learner 估计个体级 CATE（Conditional Average Treatment Effect）
- 用 Qini/AUUC 评估 uplift 排序能力
- 用四象限分群与 offline policy simulation 将模型输出转成 targeting 策略
- 用 placebo / permutation falsification 为主实验补充稳健性证据；Notebook 06 会重估 PS，并通过 notebook-local shadow matcher 计算 placebo ATE，而不是直接回放 Notebook 03 的 matcher
- 用 `Decision Desk` + `Evidence Desk` 两页 Tableau ，把分析结果翻译成面向业务方的决策台与证据台

总体转化率仅 `0.9031%`，而按渠道分层的 uplift 介于 `+0.3573%` 到 `+0.8609%` 之间。这说明平均值会掩盖具有经济意义的异质性，因此项目重点不止是证明 treatment 有效，而是把异质性翻译成可执行的 targeting 策略。

## Dashboard Showcase

This repository now includes a Tableau MVP that turns the analysis into a business-facing BI deliverable.

- `Decision Desk`: 回答“预算有限时，应该优先投给谁”，把 `Persuadables only` 推荐动作、预算节省与 ROI proxy 压成一页高管摘要
- `Evidence Desk`: 回答“为什么要相信这个 recommendation”，把实验基线、PSM 证据、Qini 排序能力与 placebo 边界压成一页证据台
- `Delivery package`: [`dashboard/README.md`](dashboard/README.md) · [`Packaged workbook (.twbx, recommended)`](dashboard/Causal%20Uplift%20Marketing%28Decision%20Desk%26Evidence%20Desk%29.twbx) · [`Source workbook (.twb)`](dashboard/Causal%20Uplift%20Marketing%28Decision%20Desk%26Evidence%20Desk%29.twb) · [`Decision Desk`](dashboard/Decision%20Desk.png) · [`Evidence Desk`](dashboard/Evidence%20Desk.png)
- `Sharing note`: `.twbx` 适合直接分发给面试官或招聘方打开；`.twb` 继续保留为 repo 内可编辑、可追溯的源文件版本
- `Refresh note`: 如果你更新了 `data/processed/*.csv`，应优先刷新 `.twb`，再重新导出 `.twbx`，避免 packaged workbook 和 notebook 结果脱节

`Decision Desk` preview:

![Decision Desk preview](dashboard/Decision%20Desk.png)

`Evidence Desk` preview:

![Evidence Desk preview](dashboard/Evidence%20Desk.png)

## Start Here

Choose a reading path below based on how quickly you want to review the project.

- `30 sec`: 先看 [`dashboard/README.md`](dashboard/README.md) 与上面的两张 dashboard preview，直接把项目当成一个 Tableau 决策交付件来理解
- `2 min`: 再看 [`docs/case_study_one_pager.md`](docs/case_study_one_pager.md)，把可视化 recommendation 翻译回业务问题、策略选择和核心离线结论
- `10 min`: 阅读 [`docs/Phase2_Execution_PRD.md`](docs/Phase2_Execution_PRD.md)、[`docs/Phase3_Execution_PRD.md`](docs/Phase3_Execution_PRD.md)、[`docs/Phase4_Execution_PRD.md`](docs/Phase4_Execution_PRD.md)，按“matching -> targeting -> robustness”快速看完整技术主线；如需本地 SQL demo 补充，再看 [`docs/sql_slice.md`](docs/sql_slice.md)
- `Reproduce locally`: 按 [Quickstart](#quickstart) 复现，再结合 [`dashboard/README.md`](dashboard/README.md)、[`data/README.md`](data/README.md) 和 [`tests/README.md`](tests/README.md) 查看 `.twbx`/`.twb` 的分工、数据源依赖与验证边界

## Key Results

Verified phase metrics and offline policy estimates from repo-visible notebooks and execution reports are listed below.

下表只保留仓库中可直接核验的核心结果，详细证据见各阶段执行报告与对应 notebook。

| Stage | Verified Result | Evidence |
|---|---|---|
| Baseline causal effect | 在 `64,000` 用户 RCT 上，Naive ATE = `+0.4955%` | [`Notebook 02`](notebooks/02_bias_exposure_and_naive_ate.ipynb), [`Phase 1 report`](docs/Phase1_Execution_PRD.md) |
| PSM diagnostics | `OVL=0.9880`，overlap ratio `95.79%`，matched pairs `21,305` | [`Notebook 03`](notebooks/03_propensity_score_matching.ipynb), [`Phase 2 report`](docs/Phase2_Execution_PRD.md) |
| PSM effect estimate | PSM ATE = `0.502%`，`95% CI [0.324%, 0.690%]` | [`Notebook 03`](notebooks/03_propensity_score_matching.ipynb), [`Phase 2 report`](docs/Phase2_Execution_PRD.md) |
| Uplift ranking | X-Learner 的 Qini Coefficient = `1.719097`（S-Learner `1.670222`，T-Learner `-0.679497`） | [`Notebook 04`](notebooks/04_uplift_modeling.ipynb), [`Phase 2 report`](docs/Phase2_Execution_PRD.md) |
| Targeting simulation | 以“仅触达 Persuadables”作为选定离线策略，在归一化触达成本下得到 `ROI proxy 2.08x`（`0.008893` vs `0.004285`），预计预算 `-75.0%`，预计保留 `51.9%` 增量转化；预算扫描仅作为补充扩量上界分析 | [`Notebook 05`](notebooks/05_segmentation_and_roi.ipynb), [`Phase 3 report`](docs/Phase3_Execution_PRD.md) |
| Robustness check | Placebo test（`n_permutations=200`）得到 placebo mean `-0.000064`、std `0.000914`、`p=0.0050` | [`Notebook 06`](notebooks/06_robustness_checks.ipynb), [`Phase 4 report`](docs/Phase4_Execution_PRD.md) |

## Decision Snapshot

This repo goes beyond model comparison and supports a concrete offline targeting recommendation on the benchmark dataset.

- `Why targeting matters`: 总体 uplift 为正，但在低基线转化率和明显异质性下，“全量触达”并不是默认最优策略
- `Selected offline policy`: 以 Phase 2 在 held-out test split 上按 Qini 选出的 X-Learner 为选型依据，先做四象限分群，再将 `Persuadables only` 作为默认投放名单；`Sleeping Dogs` 显式排除，`Sure Things` 与 `Lost Causes` 不属于默认投放名单，仅在未来需要扩量时再单独评估
- `Offline policy takeaway`: 在当前默认阈值下，`Persuadables` 恰好对应 `16,000` 人（`25%`）；离线模拟表明，仅触达这部分用户预计可保留 `51.9%` 的增量转化，同时将预算压缩 `75.0%`。预算曲线中“约 `60%` 预算覆盖 `>=95%` 全量 uplift”只表示连续 CATE 排序下的补充扩量上界，不代表当前选定策略
- `Deployment boundary`: 以上均为基于 RCT 基准数据和归一化触达成本的离线结果；若迁移到观察性投放场景，仍需重新验证 overlap，并通过线上 holdout 完成闭环

## Documentation Map

Open these documents for phase-by-phase evidence and implementation details.

- [`dashboard/README.md`](dashboard/README.md): Tableau MVP 的交付索引；说明 `.twbx` 为什么是推荐分享版本、`.twb` 为什么仍保留在 repo，以及两页 dashboard 分别回答什么问题
- [`docs/case_study_one_pager.md`](docs/case_study_one_pager.md): 业务优先的单页入口；先看推荐策略与核心结论，再回到 phase reports 看证据
- [`docs/Phase1_Execution_PRD.md`](docs/Phase1_Execution_PRD.md): 数据摄入、EDA、Naive ATE、HTE、RCT 平衡性检查
- [`docs/Phase2_Execution_PRD.md`](docs/Phase2_Execution_PRD.md): PSM、overlap/positivity、matched ATE、uplift modeling、Qini 评估
- [`docs/Phase3_Execution_PRD.md`](docs/Phase3_Execution_PRD.md): 四象限分群、`Persuadables only` 默认策略、阈值敏感性，以及作为补充扩量分析的预算曲线
- [`docs/Phase4_Execution_PRD.md`](docs/Phase4_Execution_PRD.md): placebo / permutation falsification 与 verification boundary
- [`docs/tableau_execution_manual.md`](docs/tableau_execution_manual.md): Tableau MVP 的 build manual / packaging appendix；说明这套决策台最初是如何规划、取舍和压缩的
- [`tests/README.md`](tests/README.md): data-free 单元测试范围、运行入口与 Coverage Map
- [`data/README.md`](data/README.md): 本地数据布局、常见产物与复现路径
- [`docs/sql_slice.md`](docs/sql_slice.md): 可选的 SQL appendix / local demo runbook；在读完主线分析后，用于把已选定的 `Persuadables only` 策略，以及未来可能的 score-based top-K / cutoff 扩量 demo，翻译成可复现的本地查询

## Repository Guide

Key files and directories for configuration, methods, notebooks, and outputs.

- [`configs/config.yml`](configs/config.yml): 单一配置入口，集中管理路径、covariates、PSM 默认参数与随机种子
- [`src/data_utils.py`](src/data_utils.py): 数据加载、清洗、特征工程与产物落盘
- [`src/causal.py`](src/causal.py): propensity score、matching、balance check、ATE / bootstrap 工具
- [`src/uplift.py`](src/uplift.py): S/T/X-Learner、Qini / AUUC 评估
- [`src/business.py`](src/business.py): 分群、ROI simulation 与预算扫描逻辑
- [`dashboard/`](dashboard): Tableau MVP 的 `.twbx` / `.twb` workbook、dashboard 截图与交付说明
- [`notebooks/`](notebooks): 分阶段分析与结果输出
- [`notebooks/Phase1_DoD.ipynb`](notebooks/Phase1_DoD.ipynb): 端到端回归门禁 notebook
- [`outputs/figures/`](outputs/figures): 各阶段已落盘图表

## Quickstart

Run from the repository root.

在仓库根目录执行以下步骤。

### 1) Install dependencies

```bash
python -m pip install -r requirements.txt
python -m pip install pytest
```

说明：建议在虚拟环境中安装；`requirements.txt` 已固定版本以便复现。`pytest` 作为开发依赖单独安装，用于 data-free smoke check。

### 2) No-data smoke check

```bash
python -m compileall src
python -m pytest -q
```

说明：更完整的测试入口与 Coverage Map 见 [`tests/README.md`](tests/README.md)。

### 3) With-data reproduction

1. 将数据文件放到 `data/raw/hillstrom.csv`
2. 推荐先运行 [`notebooks/Phase1_DoD.ipynb`](notebooks/Phase1_DoD.ipynb) 作为最小端到端验收门禁
3. 如需完整复现，可按顺序执行 [`notebooks/01_data_ingestion_and_eda.ipynb`](notebooks/01_data_ingestion_and_eda.ipynb) 到 [`notebooks/06_robustness_checks.ipynb`](notebooks/06_robustness_checks.ipynb)

可选的非交互执行方式：

```bash
jupyter nbconvert --execute --to notebook --inplace notebooks/Phase1_DoD.ipynb
```

### 4) Local Data + Expected Artifacts

- 原始数据来自 Hillstrom Email Marketing RCT / MineThatData challenge；pipeline 默认读取本地 `data/raw/hillstrom.csv`，公开仓库默认不再分发原始 CSV
- 常见产物包括：`data/processed/hillstrom_cleaned.csv`、`data/processed/hillstrom_features.csv`、`data/processed/hillstrom_matched.csv`、`data/processed/cate_vectors.npz`、`data/processed/qini_results.json`、`data/processed/user_segments.csv`
- 可选的本地审计产物包括：`data/processed/roi_simulation.json`、`data/processed/placebo_results.json`，以及 `data/raw/` 下带时间戳的 raw snapshot
- Tableau MVP 额外依赖以下 flat files：`data/processed/tableau_policy_compare.csv`、`data/processed/tableau_budget_curve.csv`、`data/processed/tableau_qini_curve.csv`、`data/processed/tableau_validation_kpis.csv`，并与 `data/processed/user_segments.csv`、`data/processed/hillstrom_features.csv` 共同组成当前 workbook 的最小数据包
- 当前仓库同时保留 [`dashboard/Causal Uplift Marketing(Decision Desk&Evidence Desk).twbx`](dashboard/Causal%20Uplift%20Marketing%28Decision%20Desk%26Evidence%20Desk%29.twbx) 与 [`dashboard/Causal Uplift Marketing(Decision Desk&Evidence Desk).twb`](dashboard/Causal%20Uplift%20Marketing%28Decision%20Desk%26Evidence%20Desk%29.twb)；前者用于低摩擦分享，后者用于本地刷新与版本追踪
- 若只需要浏览 dashboard，优先打开 `.twbx`；若需要重连数据、刷新图表或继续迭代，使用 `.twb` 并指向本地 `data/processed/` 下的 CSV
- 图表默认写入 [`outputs/figures/`](outputs/figures)

## Data and Validation Notes

Validation is intentionally split between implementation tests and notebook-level statistical evidence.

本项目把“实现合同验证”和“统计层证据”明确分开：前者负责保证代码与接口不跑偏，后者负责支撑因果与策略层结论。

### Validation Boundaries

- [`tests/README.md`](tests/README.md) 中的 `pytest` 用例主要验证 `src/` 内的实现合同与关键不变量；它们不单独证明因果识别成立或业务 lift 达标
- 统计层证据来自 notebooks 与 phase reports，其中 [`notebooks/Phase1_DoD.ipynb`](notebooks/Phase1_DoD.ipynb) 是最小端到端回归门禁，[`notebooks/06_robustness_checks.ipynb`](notebooks/06_robustness_checks.ipynb) 提供 placebo / falsification evidence
- `data/raw/` 与 `data/processed/` 是 pipeline 的本地工作目录；重新执行 notebook 时，会在这些目录以及 [`outputs/figures/`](outputs/figures) 下生成或刷新产物
- [`data/README.md`](data/README.md) 记录了预期目录结构、常见产物和复现路径
- 项目配置由 `configs/config.yml` 统一管理，包括 covariates、PSM 默认参数（如 `caliper_factor=0.2`）和 `random_state=42`

## Methods at a Glance

The method stack combines a causal baseline, an uplift ranking layer, and an offline decision layer.

- `Causal baseline`: 在 RCT 的 `conversion` 结果上使用 difference-in-means 建立总体因果基线
- `De-biasing workflow`: 用 propensity score estimation、overlap diagnostics、1:1 no-replacement matching、balance checks 与 pair-level bootstrap 形成可审计的 PSM 链路
- `Uplift modeling`: 用 S/T/X-Learner 估计个体级 CATE，并在 held-out test split 上以 Qini/AUUC 比较排序能力、记录最佳 learner 元数据
- `Decision layer`: 读取 `data/processed/qini_results.json` 与 `data/processed/cate_vectors.npz`，将 Phase 2 已选 learner 的全样本 CATE 向量翻译成分群、ROI proxy 与预算敏感性分析
- `Robustness layer`: 用 placebo / permutation test 检查一条与 Phase 2 设计对齐、但由 Notebook 06 在本地内存中重建的 shadow `PS -> matching -> ATE` 链路在随机标签下的假阳性风险

### Important Modeling Conventions

- `visit` 被排除出 covariates，因为 treatment 会将 visit rate 从 `10.62%` 抬升到 `16.70%`；它更像 treatment 之后的中介变量，而不是有效的前置特征
- `spend` 保留为辅助业务结果和 ROI 输入，而不是营销成本；Phase 3 的 ROI 使用归一化 `cost_per_contact=1.0` 做相对策略比较，不直接替代真实预算表
- Phase 3 的 `ROI 2.08x`、`budget -75%` 与 `51.9%` retention 都应理解为 offline policy simulation / policy value proxy，而不是已上线验证的真实业务 ROI

## SQL Slice

The repo also includes an optional local SQL appendix for demonstrating how validated experiment results and uplift scores can be consumed by reproducible demo queries.

- Guide: [`docs/sql_slice.md`](docs/sql_slice.md)
- Query pack: [`sql/sql_slice/`](sql/sql_slice)
- 可选的本地验证方式（在生成 `data/processed/*.csv` 后，并安装 `duckdb`）：`python -m pip install duckdb && python scripts/validate_sql_slice_duckdb.py`
- 这部分作为主线项目的 SQL 补充切片，用于把实验结果、uplift score 与 targeting policy 翻译成可复现的本地 demo 查询流程，而不是生产投放 SOP
- `customer_id` / `score_date` / `model_version` 在该 appendix 中只承担 repo-local demo contract 的角色，不应解读为已经接入真实生产 activation pipeline

## Limitations

This repository uses an RCT benchmark and offline policy simulation; observational deployment would still require fresh validation.

- 当前主数据是 RCT，因此 PSM 在本项目里主要承担可迁移去偏流程的 sanity check / audit 角色
- ROI simulation 使用统一的归一化成本口径，适合做策略相对比较，不直接替代真实预算表
- Phase 3 的 ROI / retention 数字是 offline policy value proxy，用于 ranking 与 policy comparison，不等同于已上线验证的财务结果
- SQL slice 是本地 appendix / handoff demo，用于展示“模型结果如何被 SQL 消费”；它不是已经接入业务系统的生产投放链路
- 若迁移到观察性投放场景，仍需要重新验证 overlap、balance、placebo stability 与线上 holdout 结果

## References

1. Rosenbaum, P.R. & Rubin, D.B. (1983). "The central role of the propensity score in observational studies for causal effects." *Biometrika*, 70(1), 41-55.
2. Kunzel, S.R., Sekhon, J.S., Bickel, P.J., & Yu, B. (2019). "Metalearners for estimating heterogeneous treatment effects using machine learning." *PNAS*, 116(10), 4156-4165.
3. Radcliffe, N.J. & Surry, P.D. (2011). "Real-world uplift modelling with significance-based uplift trees." *Portrait Technical Report TR-2011-1*.
4. Hillstrom, K. (2008). "The MineThatData E-Mail Analytics And Data Mining Challenge." *MineThatData Blog*.

## Contact

- GitHub Issues: [Repository Issues](https://github.com/CLampard-Y/causal-uplift-marketing/issues)
- Email: nianmingyao.math@outlook.com
