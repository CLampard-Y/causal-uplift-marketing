# One-Page Case Study: Experiment -> Uplift -> ROI Targeting

## Headline (30s)
离线策略模拟表明：若将全量触达改为 **只触达 Persuadables** 的精准投放，预计可在预算下降 `75%` 的同时，保留 `51.9%` 的增量转化；按统一归一化口径计算，expected ROI proxy 提升至 `2.08x`。

以上建议已被封装成一个 `2-page` Tableau MVP：`Decision Desk` 负责给动作建议，`Evidence Desk` 负责解释为什么这个建议值得信。

## Problem
- 只看 A/B 的平均提升（ATE），只能回答“整体是否有效”，却无法回答“预算应该投给谁”。
- 如果继续全量触达，会把原本就会转化的人一并计入触达成本。
- 同时，部分人群在被触达后可能出现负增量（如 **Sleeping Dogs**）；若不识别，这部分损失会直接侵蚀投放效率。

## Data & Setup
- 数据来自 Hillstrom 邮件营销随机对照试验（RCT），共 `64,000` 名用户，Treatment:Control = `2:1`。
- 核心结果变量为 `conversion`（是否转化）和 `spend`（用户收入结果）。
- 在成本约束下，将是否触达视为离线 targeting 决策：先基于 uplift 做四象限分群，再把 `Persuadables` 作为默认投放名单；在当前默认阈值下，该象限恰好对应 `16,000` 名用户（`25%`）。

## Approach
- 以 **反事实视角** 估计增量，并结合实验臂 sanity check 与协变量平衡诊断，界定 **因果识别假设** 的适用边界。
- 估计用户级 **异质性效应**（CATE / uplift），把“平均有效”转化为“可用于预算分配的排序信号”。
- 用 Qini / AUUC 评估排序质量，再把 score 先翻译成四象限分群与 `Persuadables only` 主推荐策略；cutoff 与候选名单只在 SQL appendix 中作为未来扩量的 demo 展示。

## Decision
- 选定策略为 **只投放 Persuadables**；`Sleeping Dogs` 显式拦截。`Sure Things` 与 `Lost Causes` 不在默认投放名单中，只作为未来扩量时的候选扩展人群。
- uplift 在主线中承担的是“分群与排序信号”角色，而不是已经选定的通用 cutoff policy；若未来做 score-based 扩量，再结合离线 expected ROI proxy 与业务 guardrail 单独确定 cutoff。

## Impact
- 在离线策略模拟中，`Persuadables only` 策略将触达规模从 `64,000` 收缩至 `16,000`，预计预算下降 `75%`，同时预计保留 `51.9%` 的增量转化。
- 在统一、归一化的 `cost_per_contact` 口径下，expected ROI proxy 为 `2.08x`（`0.008893` vs `0.004285`）。
- 该指标用于比较策略优先级与相对效率，不等同于真实财务结算结果。

## Tableau Delivery
- `Decision Desk`: 把 recommendation 压成一页预算决策台，直接回答“预算有限时应不应该继续全量触达”。
- `Evidence Desk`: 把实验 uplift、PSM 估计、Qini 排序能力和 placebo 边界压成一页证据台，避免项目看起来像单纯模型炫技。
- 交付形式从 notebook 结果进一步推进到 BI 交付件：面试官可以先看 `.twbx` 与 dashboard 截图，再回到 notebook / phase report 追溯证据。

## Risks & Next
- 在线验证：若未来迁移到真实触达场景，可先用 holdout A/B 检验当前 `Persuadables only` 策略的真实增量效果；若再引入 top-K / cutoff 扩量，应把它作为独立扩展策略另行验证。
- 口径说明：上述 Budget / ROI / retention 数字均来自 offline policy simulation，应解读为策略优先级信号，而非已上线验证的真实业务 ROI。
- 漂移与校准：在本地 demo 中可持续检查打分覆盖率、分数分布与样本漂移；若未来迁移到真实环境，再补充更严格的版本治理与重打分流程。

## Evidence Links
- Tableau deliverable index：[`dashboard/README.md`](../dashboard/README.md)
- Packaged workbook（recommended）：[`dashboard/Causal Uplift Marketing(Decision Desk&Evidence Desk).twbx`](../dashboard/Causal%20Uplift%20Marketing%28Decision%20Desk%26Evidence%20Desk%29.twbx)
- Source workbook：[`dashboard/Causal Uplift Marketing(Decision Desk&Evidence Desk).twb`](../dashboard/Causal%20Uplift%20Marketing%28Decision%20Desk%26Evidence%20Desk%29.twb)
- Dashboard preview：[`Decision Desk`](../dashboard/Decision%20Desk.png) · [`Evidence Desk`](../dashboard/Evidence%20Desk.png)
- 业务数字与端到端叙事：[`README.md`](../README.md)
- 质量保障（data-free tests）：[`tests/README.md`](../tests/README.md)
- Matching + balance diagnostics：[`notebooks/03_propensity_score_matching.ipynb`](../notebooks/03_propensity_score_matching.ipynb)
- Uplift modeling + Qini/AUUC：[`notebooks/04_uplift_modeling.ipynb`](../notebooks/04_uplift_modeling.ipynb)
- Segmentation + ROI simulation：[`notebooks/05_segmentation_and_roi.ipynb`](../notebooks/05_segmentation_and_roi.ipynb)
- SQL appendix（local demo only）：[`docs/sql_slice.md`](./sql_slice.md)
