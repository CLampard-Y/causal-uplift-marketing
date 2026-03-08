# Phase 3 Execution Report


本报告记录 Phase 3 的实际实现、可核验证据与主要结论，供仓库审阅、项目归档和后续复现参考。文中仅引用可在仓库中直接验证的结果（Notebook stdout/Markdown、配置文件、代码常量、已落盘图表与 JSON/CSV/NPZ）。

## 1. Overview

Phase 3 的目标，是把 Phase 2 的个体级因果增量（CATE）从“模型输出”转成“可执行策略”。具体做法是：先将全样本的 CATE 向量划分为四象限人群（Persuadables / Sure Things / Lost Causes / Sleeping Dogs），再在统一成本口径下进行离线 ROI policy simulation，并用“预算节省 vs 增量保留”的量化结果形成策略层输出。

在 `notebooks/05_segmentation_and_roi.ipynb` 的可核验输出中，本次选用的最佳 learner 为 X-Learner，`CATE shape = (64000,)`，`CATE range = [-0.049814, 0.045046]`，且 `X-Learner Qini Coef = 1.72`。

按默认阈值（`cate_threshold_pct=50.0`、`baseline_threshold=0.5`）分群后，Persuadables 与 Sure Things 各占 `25.0% (16,000)`，Sleeping Dogs 占 `13.4266% (8,593)`。

离线 ROI policy simulation 显示：

- 全量投放（64,000 人）的离线 expected incremental conversions proxy 为 `274.27`，`ROI proxy = 0.004285`
- 精准投放（仅 Persuadables，16,000 人）的离线 expected incremental conversions proxy 为 `142.29`，`ROI proxy = 0.008893`
- 在该归一化成本口径下，预计节省预算 `75.0%`、预计保留增量转化 `51.9%`，`ROI proxy` 比值为 `2.08×`

预算扫描结果进一步显示：`Precision reaches ≥95% of full uplift at budget ≈ 60%`（见同一 Notebook 的输出与 `outputs/figures/fig_08b_budget_uplift_curve.png`）。

- LaTeX（用 CATE-sum 做增量归因的核心口径）:
  $$\widehat{\Delta N}(\mathcal{S}) = \sum_{i\in\mathcal{S}} \widehat{\tau}_i$$
- Plain text:
  `DeltaN_hat(S) = sum_{i in S} tau_hat_i`

其中 $\widehat{\tau}_i$ 为个体 CATE，$\mathcal{S}$ 为被投放的用户集合。

## 2. Evidence Policy (Verifiable Numbers Only)

本报告中的数值遵循以下规则：

- 仅使用在 `notebooks/05_segmentation_and_roi.ipynb`、`configs/config.yml`、`src/business.py`、或 `outputs/figures/` 中可直接核验的数值。
- 若本地复跑生成 `data/processed/roi_simulation.json` 等落盘产物（默认 gitignored，详见 `data/README.md`），也可作为额外审计痕迹。
- 若某个数字只能“推测”或需要跑代码但当前产物不可核验，则不写；对可由可核验数字推导出的显式计算会写明公式与来源。

## 3. Scope

Phase 3 的范围聚焦在“从 CATE 向量到投放决策”的翻译层，覆盖三块内容：

1) 四象限分群（CATE + baseline proxy → quadrant assignment），实现/证据入口：`src/business.py`、`notebooks/05_segmentation_and_roi.ipynb`。

2) 阈值敏感性分析（baseline_threshold P30-P70 → 分群占比/均值稳定性），证据入口：`notebooks/05_segmentation_and_roi.ipynb`、`outputs/figures/fig_07d_baseline_sensitivity.png`。

3) 离线 ROI 仿真与预算扫描（Full vs Random vs Precision；Budget vs Cumulative uplift），实现/证据入口：`src/business.py`、`notebooks/05_segmentation_and_roi.ipynb`、`outputs/figures/fig_08*.png`。

## 4. Key Artifacts

- Segmentation + ROI notebook: `notebooks/05_segmentation_and_roi.ipynb`
- Business layer utilities (segmentation + ROI simulation): `src/business.py`

- Figures (Phase 3):
  - Quadrant visualization: `outputs/figures/fig_07_quadrant_scatter.png`
  - Segment diagnostics:
    - `outputs/figures/fig_07b_segment_baseline_ratio.png`
    - `outputs/figures/fig_07b_segment_conversion.png`
    - `outputs/figures/fig_07c_segment_distribution.png`
    - `outputs/figures/fig_07d_baseline_sensitivity.png`
  - ROI results:
    - `outputs/figures/fig_08_roi_comparison.png`
    - `outputs/figures/fig_08b_budget_uplift_curve.png`

- Optional persisted output (local rerun; gitignored):
  - ROI simulation results: `data/processed/roi_simulation.json`

## 5. End-to-End Pipeline Sketch

下面用真实产物把 Phase 3 的端到端链路串起来：从特征表得到 CATE（本 Notebook 内部复跑 uplift learner 并选优），把 CATE 翻译为四象限分群，再把分群与 CATE 排序用于 ROI 仿真与预算扫描，最终将图表落盘以便审阅。

```mermaid
flowchart LR
  A[Feature table<br/>data/processed/hillstrom_features.csv] --> B[Fit uplift learners + select best CATE<br/>notebooks/05_segmentation_and_roi.ipynb]
  B --> C[CATE vector<br/>shape=(64000,)]
  C --> D[Quadrant segmentation<br/>src/business.segment_users]
  D --> D1[Figures<br/>outputs/figures/fig_07*.png]
  D --> E[ROI simulation<br/>src/business.simulate_roi]
  E --> E1[Figures<br/>outputs/figures/fig_08*.png]
  E --> E2[roi_simulation.json<br/>data/processed/roi_simulation.json]
```

## 6. Verify in 2 Minutes

GitHub 浏览（不跑代码）也能快速核验本报告的关键主张：

1) 打开 `notebooks/05_segmentation_and_roi.ipynb`，在 stdout/表格输出中核验：
   - `X-Learner Qini Coef = 1.72, CATE shape = (64000,), CATE range = [-0.049814, 0.045046]` 与 `Selected best learner CATE: X-Learner`。
   - 分群 summary 表（四象限的 Count/Pct/Mean CATE/Mean Baseline）及敏感性分析表（P30-P70）。
   - ROI stdout：`ROI = 0.004285` vs `ROI = 0.008893`、`节省预算 75.0%`、`保留增量 51.9%`、以及 `Precision reaches ≥95% of full uplift at budget ≈ 60%`；这些数字在本阶段都应解读为 offline policy simulation 下的 proxy / estimate。

2) 打开 `outputs/figures/` 核验 Phase 3 图表是否落盘：
   - 分群/诊断：`outputs/figures/fig_07_quadrant_scatter.png`、`outputs/figures/fig_07c_segment_distribution.png`、`outputs/figures/fig_07d_baseline_sensitivity.png`
   - ROI：`outputs/figures/fig_08_roi_comparison.png`、`outputs/figures/fig_08b_budget_uplift_curve.png`

## 7. Results (Verifiable)

### 7.1 Segmentation Summary (Quadrants)

`notebooks/05_segmentation_and_roi.ipynb` 的输出表格给出了四象限的可核验统计（节选关键列）：

| Segment | Count | Pct | Mean CATE | Mean Baseline (proxy) |
|---|---:|---:|---:|---:|
| Lost Causes | 23,407 | 0.365734 | 0.002465 | 0.002058 |
| Persuadables | 16,000 | 0.250000 | 0.008893 | 0.000000 |
| Sure Things | 16,000 | 0.250000 | 0.006848 | 0.001491 |
| Sleeping Dogs | 8,593 | 0.134266 | -0.004106 | 0.034046 |

同一表格还打印了两组辅助诊断列（建议与图一起看）：

- `Baseline Ratio (vs global control)`：Lost Causes `0.359492`、Persuadables `0.000000`、Sure Things `0.260463`、Sleeping Dogs `5.945731`
- `Overall Conversion (T/C mix)`：Lost Causes `0.003845`、Persuadables `0.013187`、Sure Things `0.009250`、Sleeping Dogs `0.015012`

注：这里的 baseline 是 proxy（按 CATE 分桶后在 control 内求均值），会出现 “Persuadables mean baseline = 0” 这类离散化结果；这在低转化率 + 分桶统计中是可预期现象，详见后续“阈值敏感性”。

### 7.2 Threshold Sensitivity (baseline_threshold)

`notebooks/05_segmentation_and_roi.ipynb` 对 `baseline_threshold` 做了 P30-P70 的敏感性分析，并直接输出分群占比表：

| threshold | Persuadables_pct | Sure Things_pct | Lost Causes_pct | Sleeping Dogs_pct |
|---:|---:|---:|---:|---:|
| 0.3 | 0.00 | 0.50 | 0.365734 | 0.134266 |
| 0.4 | 0.00 | 0.50 | 0.365734 | 0.134266 |
| 0.5 | 0.25 | 0.25 | 0.365734 | 0.134266 |
| 0.6 | 0.30 | 0.20 | 0.365734 | 0.134266 |
| 0.7 | 0.35 | 0.15 | 0.365734 | 0.134266 |

这为默认选择 `baseline_threshold=0.5` 提供了可解释性依据：它给出“Persuadables/Sure Things 各 25%”的均衡样本量，也避免了 P30/P40 下 Persuadables 退化为 0 的离散化边界情况（Notebook 在文字说明中也解释了该现象来自 `baseline_prob` 的分桶离散取值）。

### 7.3 Offline Policy Simulation (Full vs Precision)

`notebooks/05_segmentation_and_roi.ipynb` 的 stdout 直接打印了核心离线 policy simulation 结果：

- `全量投放: 投放 64,000 人，expected incremental conversions proxy = 274.27，ROI proxy = 0.004285`
- `精准投放: 投放 16,000 人（仅 Persuadables），expected incremental conversions proxy = 142.29，ROI proxy = 0.008893`
- `离线策略模拟: 预计节省预算 75.0%，预计保留增量转化 51.9%`

结合 `src/business.py` 的 CATE-sum 定义，这些数字应被解读为在归一化 `cost_per_contact` 下的 offline expected policy value proxy；同一 Notebook 的 Markdown “核心商业结论”对应的口径一致结论可写成：`ROI proxy ratio = 2.08×`。

此外，预算扫描曲线的 stdout 打印：`Precision reaches ≥95% of full uplift at budget ≈ 60%`，并落盘到 `outputs/figures/fig_08b_budget_uplift_curve.png`。

## 8. Method Notes

### 8.1 Quadrant Definitions Used Here

本阶段的“四象限”是一组策略分层规则：它把连续 CATE 向量（边际增量）离散成四个可执行标签，并附带一个 baseline 的 proxy 轴，用于区分“高增量但基线更低/更高”。实现见 `src/business.py`。

- LaTeX（baseline proxy：在同一 CATE 分位桶里，用 control 的经验转化率近似基线概率）：
  $$\widehat{b}_i = \mathbb{E}[Y\mid T=0,\;\mathrm{bin}(\widehat{\tau})=\mathrm{bin}(\widehat{\tau}_i)]$$
- Plain text:
  `b_hat_i = E[Y | T=0, bin(tau_hat)=bin(tau_hat_i)]`

默认参数对应的标签逻辑可以概括为：

- Sleeping Dogs：$\widehat{\tau}_i < 0$
- Lost Causes：低 CATE（$\widehat{\tau}_i$ 低于阈值；默认是 CATE 的中位数分割）
- Persuadables：高 CATE 且 baseline proxy 相对更低（在“高 CATE 子群”内用百分位切分）
- Sure Things：高 CATE 且 baseline proxy 相对更高

这里的 “Sure Things / Persuadables” 被解释为相对排序（在高 CATE 子群内部对 baseline 做分割），而不是“绝对会自然转化/绝对不会自然转化”的断言；这对 Hillstrom 这类低基线转化率数据更稳健。

### 8.2 Offline ROI Proxy Accounting: Why CATE-sum

本项目在 `src/business.py` 里把离线 ROI proxy 的增量归因口径固定为 CATE-sum：

- LaTeX：
  $$\widehat{\mathrm{ROI}}_{proxy}(\mathcal{S}) = \frac{\sum_{i\in\mathcal{S}} \widehat{\tau}_i}{c\cdot |\mathcal{S}|}$$
- Plain text：
  `ROI_proxy_hat(S) = sum_{i in S} tau_hat_i / (c * |S|)`

其中 $c$ 是单位触达成本（Notebook 使用 `cost_per_contact=1.0` 作为归一化口径）。这样做的核心好处是“内部一致性”：预算扫描也是按 CATE 排序累加增量，因此用同一套增量归因系统，能把策略比较变成可审计的 deterministic 结果（而不是一次抽样的随机波动）。同时需要强调，这里得到的是 offline policy value proxy，而不是已上线实现的 realized finance ROI。

## 9. Key Method Decisions

以下为 Phase 3 的关键方法选择（每条都能在仓库中找到可核验证据入口），用于解释“为什么这样做”和“为什么结果可信”。

- baseline 不训练单独的 propensity/baseline model，而用“CATE 分桶 + control 经验转化率”作为 proxy，是为了保持 business layer 的模块边界清晰（`segment_users(...)` 不依赖协变量矩阵 X），并降低计算复杂度；实现见 `src/business.py`。
- “Sure Things 可能很少甚至为空”在低转化率场景是高概率事件；为避免极端空桶，本实现用“高 CATE 子群内的 baseline 百分位”做自适应切分（默认 P50），而不是用全局基线的固定倍数阈值；代码注释与旧策略问题说明见 `src/business.py`。
- ROI 仿真用 `sum(CATE)` 而不是 `ATE * N` 是为了显式保留异质性：若把每个用户都当成“平均 uplift”，就失去了 uplift modeling 的商业意义；实现说明见 `src/business.py` 的 NOTE。
- 随机投放（Random targeting）使用“期望值计算”而不是 Monte Carlo 抽样，是为了让对比更稳定、可复现；实现见 `src/business.py`（`random_targeting` 直接按均值计算）。

## 10. Interpretation and Limits

Phase 3 的输出应被解读为“基于离线 CATE 排序的策略层结果”，其边界包括：

- 四象限标签用于组织投放优先级，而不是对用户天然属性的绝对定义。
- `baseline_prob` 是 proxy：它来自同一 CATE 分位桶内 control 组的经验转化率，而不是单独训练的个体级 baseline 模型。
- ROI 仿真使用 `cost_per_contact=1.0` 的归一化成本口径，因此更适合做相对比较（Full vs Random vs Precision），而不应直接替代真实财务预算表。
- `sum(CATE)` / `ROI proxy` 的输出应被解释为 offline expected policy value proxy；若要进一步对应 realized business ROI，仍需通过线上 holdout、delivery 与 finance 口径完成闭环验证。

## 11. Concise Summary

### 11.1 Short Summary

Phase 3 的核心工作，是把 Phase 2 的 CATE 从“模型输出”翻译成“可执行策略”。

具体而言，本阶段先用 X-Learner 产出全样本 CATE（`n=64,000`，range `[-0.049814, 0.045046]`），再通过 `src/business.segment_users` 将人群切分为四象限。敏感性分析进一步表明，默认阈值（`baseline_threshold=P50`）能够得到稳定且可解释的分群结构。

随后，`src/business.simulate_roi` 在统一成本口径下对比“全量投放 vs 随机投放 vs 精准投放（Persuadables）”，得到一组可核验的 offline policy simulation 结论：仅投放 `25%` 的 Persuadables，预计可节省 `75%` 预算，同时预计保留 `51.9%` 的增量转化，`ROI proxy ratio` 为 `2.08×`。预算扫描曲线还显示，在约 `60%` 预算时即可获得 `≥95%` 的全量增量效果。

### 11.2 Structured Recap

- Context：输入为全样本 CATE 向量，目标是将模型输出转成可执行的投放规则。
- Objective：构建稳定、可解释的四象限分群，并量化 Precision Targeting 相对 Full / Random 的 offline ROI proxy 差异。
- Outcome：Persuadables 占 `25%`；Precision 的 `ROI proxy` 为 `0.008893`，相对 Full 的 `0.004285` 比值为 `2.08×`；在约 `60%` 预算时可覆盖 `≥95%` 的全量增量效果。
