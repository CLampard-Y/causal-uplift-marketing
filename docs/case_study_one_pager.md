# One-Page Case Study: Experiment -> Uplift -> ROI Targeting

## Headline (30s)
离线策略模拟表明：若将全量触达改为基于 uplift 的精准投放，预计可在预算下降 `75%` 的同时，保留 `51.9%` 的增量转化；按统一归一化口径计算，expected ROI proxy 提升至 `2.08x`。

## Problem
- 只看 A/B 的平均提升（ATE），只能回答“整体是否有效”，却无法回答“预算应该投给谁”。
- 如果继续全量触达，会把原本就会转化的人一并计入触达成本。
- 同时，部分人群在被触达后可能出现负增量（如 **Sleeping Dogs**）；若不识别，这部分损失会直接侵蚀投放效率。

## Data & Setup
- 数据来自 Hillstrom 邮件营销随机对照试验（RCT），共 `64,000` 名用户，Treatment:Control = `2:1`。
- 核心结果变量为 `conversion`（是否转化）和 `spend`（用户收入结果）。
- 在成本约束下，将是否投放视为 activation 决策：把 `uplift_score` 作为预期增量转化信号，按分数排序后仅激活前 `16,000` 名用户（`25%`）。

## Approach
- 以 **反事实视角** 估计增量，并结合实验臂 sanity check 与协变量平衡诊断，界定 **因果识别假设** 的适用边界。
- 估计用户级 **异质性效应**（CATE / uplift），把“平均有效”转化为“可用于预算分配的排序信号”。
- 用 Qini / AUUC 评估排序质量，再将 score 落成 cutoff 与名单输出，形成可追溯的决策闭环。

## Decision
- 采用四象限策略：优先 Persuadables；对 Sure Things / Lost Causes 降级或不投；对 Sleeping Dogs 显式拦截。
- 将 uplift 作为排序信号，而非绝对概率；cutoff 结合离线 expected ROI proxy 与业务 guardrail 共同确定。

## Impact
- 在离线策略模拟中，精准投放将触达规模从 `64,000` 收缩至 `16,000`，预计预算下降 `75%`，同时预计保留 `51.9%` 的增量转化。
- 在统一、归一化的 `cost_per_contact` 口径下，expected ROI proxy 为 `2.08x`（`0.008893` vs `0.004285`）。
- 该指标用于比较策略优先级与相对效率，不等同于真实财务结算结果。

## Risks & Next
- 在线验证：用 holdout A/B 检验当前 cutoff 的真实增量效果，并据此迭代策略。
- 口径说明：上述 Budget / ROI / retention 数字均来自 offline policy simulation，应解读为策略优先级信号，而非已上线验证的真实业务 ROI。
- 漂移与校准：持续监控打分覆盖率、分数分布与样本漂移；必要时按 `model_version` 回滚，并重新打分复盘。

## Evidence Links
- 业务数字与端到端叙事：[`README.md`](../README.md)
- 质量保障（data-free tests）：[`tests/README.md`](../tests/README.md)
- Matching + balance diagnostics：[`notebooks/03_propensity_score_matching.ipynb`](../notebooks/03_propensity_score_matching.ipynb)
- Uplift modeling + Qini/AUUC：[`notebooks/04_uplift_modeling.ipynb`](../notebooks/04_uplift_modeling.ipynb)
- Segmentation + ROI simulation：[`notebooks/05_segmentation_and_roi.ipynb`](../notebooks/05_segmentation_and_roi.ipynb)
- SQL runbook（metrics -> action）：[`docs/sql_slice.md`](./sql_slice.md)
