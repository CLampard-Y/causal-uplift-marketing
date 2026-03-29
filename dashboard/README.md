# Tableau MVP Deliverables

This folder packages the analysis into a 2-page Tableau MVP for portfolio review and interview walkthroughs.

## What is in this folder

- `Causal Uplift Marketing(Decision Desk&Evidence Desk).twbx`: 推荐的分享版本；适合直接发给面试官或招聘方打开
- `Causal Uplift Marketing(Decision Desk&Evidence Desk).twb`: 当前的 Tableau workbook，包含 `Decision Desk` 与 `Evidence Desk` 两页
- `Decision Desk.png`: 页面 1 截图，展示预算约束下的 targeting recommendation
- `Evidence Desk.png`: 页面 2 截图，展示为什么这个 recommendation 值得信

## Recommended usage

- `Use .twbx to review`: 如果目标是低摩擦浏览作品，优先打开 `.twbx`
- `Use .twb to edit or refresh`: 如果目标是继续改图、重连数据源或在新 CSV 上刷新 dashboard，使用 `.twb`
- `Keep both`: `.twbx` 负责交付体验，`.twb` 负责源文件可维护性

## Page roles

- `Decision Desk`: 回答“预算有限时，应该优先投给谁”；核心信息是 `Persuadables only` 在保留 `51.9%` 增量转化的同时节省 `75%` 预算，并把 ROI proxy 提升到 `2.08x`
- `Evidence Desk`: 回答“为什么相信这条 recommendation”；核心证据是实验平均 uplift、PSM overlap / matched ATE、Qini 排序能力、以及 placebo 边界

## Preview

`Decision Desk`:

![Decision Desk preview](Decision%20Desk.png)

`Evidence Desk`:

![Evidence Desk preview](Evidence%20Desk.png)

## Data contract used by the current workbook

The source workbook `.twb` reads local CSVs from `data/processed/`; the packaged workbook `.twbx` is the recommended sharing artifact.

- `tableau_policy_compare.csv`: 页面 1 的 KPI strip 与策略对比
- `tableau_budget_curve.csv`: 页面 1 的预算扩量 / incremental conversion 曲线
- `user_segments.csv`: 页面 1 的 segment mix 与分群逻辑
- `hillstrom_features.csv`: 页面 1 的画像 / 辅助解释
- `tableau_qini_curve.csv`: 页面 2 的 learner 排序能力曲线
- `tableau_validation_kpis.csv`: 页面 2 的 baseline / PSM / placebo 证据卡

## Open locally

1. 如果只是查看作品，优先打开 `Causal Uplift Marketing(Decision Desk&Evidence Desk).twbx`。
2. 如果你需要刷新数据或继续编辑，先准备 `data/processed/` 下的上述 CSV，再打开 `Causal Uplift Marketing(Decision Desk&Evidence Desk).twb`。
3. 如果 Tableau 提示数据源丢失，逐个把数据源重连到本地 `data/processed/` 目录中的对应 CSV。
4. 当 `.twb` 刷新或改版后，重新导出 `.twbx`，保证分享版本与源文件版本一致。

## Portability caveat

- 当前 repo 已同时保留 `.twbx` 与 `.twb`：前者降低外部打开门槛，后者保留可编辑、可追溯的源文件形态。
- `.twb` 内部目前写的是本机绝对路径 `E:/Work/MyCode/causal-uplift-marketing/data/processed`，因此跨机器刷新时仍需要手动重连数据源。
- 因为 `data/processed/` 默认是 gitignored，本仓库更像“分析代码 + dashboard 资产”的作品集；如果你对外只想展示成品，优先发 `.twbx`。
- `.twbx` 本质上是打包快照；如果后续 notebook 结果或 CSV 更新，记得重新导出 `.twbx`，否则分享版本会滞后。
- 当前 workbook 由 Tableau `2026.1 / version 18.1` 生成；低版本 Tableau 可能出现兼容性问题。

## Notes

- `~Causal Uplift Marketing(Decision Desk&Evidence Desk)__31708.twbr` 是 Tableau 自动恢复 / 临时文件，不属于正式交付物。

## How to present this in interview

- 第一步先讲 `Decision Desk`：预算有限时，不该默认全量触达，而应优先投给真正带来增量的人群
- 第二步再讲 `Evidence Desk`：实验基线、排序能力和 placebo 边界共同支撑 recommendation
- 最后主动补一句 caveat：这仍是 benchmark data 上的 offline policy simulation，不是已上线验证的真实财务 ROI
