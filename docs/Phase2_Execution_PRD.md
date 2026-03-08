# Phase 2 Execution Report


本报告记录 Phase 2 的实际实现、可核验证据与主要结论，供仓库审阅、项目归档和后续复现参考。文中仅引用可在仓库中直接验证的结果（Notebook stdout/Markdown、配置文件、代码常量、已落盘图表与 JSON/CSV/NPZ）。

## 1. Overview

Phase 2 在 Phase 1 的“RCT 因果基线”之上，进一步落地了一条可审计的 PSM + Uplift 工程链路。该链路先用 Logistic Regression 估计 propensity score，再通过 1:1 最近邻匹配（no replacement + caliper）构造 matched pairs，并结合 SMD 与 pair-level bootstrap，为估计可信度提供可核验证据。

从结果看，RCT 的 common support 很强：`OVL=0.9880`、PS 区间重叠比 `95.79%`、极端 IPW 权重比例 `0.00% (0/64,000)`（见 `notebooks/03_propensity_score_matching.ipynb`）。匹配后得到 `n_pairs=21,305`，PSM 的 ATE 为 `0.502%`，95% CI 为 `[0.324%, 0.690%]`，与 RCT 的朴素 benchmark `0.495%` 仅相差 `0.007%`。

在 uplift/CATE 侧，Phase 2 对比了 S/T/X-Learner，并用 Qini 曲线对 uplift 排序能力做量化评估。在 30% test 集上（`n_test=19,200`），X-Learner 的 Qini Coefficient 为 `1.719097`，优于 S-Learner 的 `1.670222`；T-Learner 为负（`-0.679497`）（见 `notebooks/04_uplift_modeling.ipynb`；如本地复跑，结果也会落盘到 `data/processed/qini_results.json` 便于回归对比）。

因此，Phase 2 的输出已经从“总体效果验证”扩展到“可支持个体/分层排序的 targeting 信号”。

- LaTeX（propensity score 定义）：
  $$e(x)=\mathbb{P}(T=1\mid X=x)$$
- Plain text：
  `e(x) = P(T=1 | X=x)`

## 2. Evidence Policy (Verifiable Numbers Only)

本报告中的数值遵循以下规则：

- 仅使用在 `notebooks/03_propensity_score_matching.ipynb`、`notebooks/04_uplift_modeling.ipynb`、`configs/config.yml`、`src/causal.py`、`src/uplift.py`、或 `outputs/figures/` 中可直接核验的数值（GitHub 可直接查看）。
- 若本地复跑生成了 `data/processed/psm_match_panel.json`、`data/processed/qini_results.json` 等落盘产物（默认 gitignored，详见 `data/README.md`），也可作为额外审计痕迹用于复核。
- 若某个数字只能“推测”或需要跑代码但当前产物不可核验，则不写；对可由可核验数字推导出的显式计算会写明公式与来源。

## 3. Scope

Phase 2 的范围聚焦在“把因果识别与 uplift 建模落成可复现链路”，覆盖两块内容：

1) PSM（propensity score estimation → overlap/positivity 诊断 → matching → balance check → matched ATE + bootstrap CI），实现/证据入口：`notebooks/03_propensity_score_matching.ipynb`、`src/causal.py`。

2) Uplift/CATE（S/T/X-Learner → CATE 分布对比 → Qini 曲线与 AUUC/Qini Coefficient 评估 → 落盘 CATE 向量与评估结果），实现/证据入口：`notebooks/04_uplift_modeling.ipynb`、`src/uplift.py`。

本阶段的“可视化证据”以 PNG 落盘在 `outputs/figures/`，并在 Notebook stdout 中打印了保存路径。

## 4. Key Artifacts

- Configuration (paths + covariates + hyperparams): `configs/config.yml`
- PSM notebook (MVP 2.1-2.3): `notebooks/03_propensity_score_matching.ipynb`
- Causal utilities (PS, matching, SMD, pair bootstrap ATE): `src/causal.py`
- Uplift notebook (MVP 2.4): `notebooks/04_uplift_modeling.ipynb`
- Uplift utilities (S/T/X learners + Qini/AUUC): `src/uplift.py`

- Produced tables / serialized outputs (Phase 2):
  
  注：以下为本地复跑生成的落盘产物，`data/` 默认 gitignored（详见 `data/README.md`）。

  - Matched sample: `data/processed/hillstrom_matched.csv`
  - Matching diagnostics: `data/processed/psm_match_panel.json`
  - Persisted CATE vectors: `data/processed/cate_vectors.npz`
  - Persisted Qini results: `data/processed/qini_results.json`

- Figures (Phase 2):
  - PS diagnostics (from `notebooks/03_propensity_score_matching.ipynb`):
    - `outputs/figures/fig_02_ps_distribution.png`
    - `outputs/figures/fig_02b_ps_overlap.png`
  - Matching + balance (from `notebooks/03_propensity_score_matching.ipynb`):
    - `outputs/figures/fig_03b_matched_ps_dist.png`
    - `outputs/figures/fig_03_smd_before_after.png`
  - Matched ATE + uncertainty (from `notebooks/03_propensity_score_matching.ipynb`):
    - `outputs/figures/fig_04b_bootstrap_ci.png`
    - `outputs/figures/fig_04_ate_comparison.png`
  - CATE + uplift evaluation (from `notebooks/04_uplift_modeling.ipynb`):
    - `outputs/figures/fig_05_cate_distributions.png`
    - `outputs/figures/fig_06_qini_curves.png`

## 5. End-to-End Pipeline Sketch

下面用真实产物把 Phase 2 的端到端链路串起来：特征表进入 PS 估计与诊断，再进入匹配与平衡性检查并输出 matched ATE；同一份特征表也进入 uplift learner 的训练/预测与 Qini 评估，最终把 CATE 向量与 Qini 曲线结果落盘，供 Phase 3/4 的分群与 ROI 仿真消费。

```mermaid
flowchart LR
  A[Feature table<br/>data/processed/hillstrom_features.csv] --> B[PS estimation<br/>src/causal.estimate_ps]
  B --> C[PS diagnostics<br/>OVL/IPW/overlap<br/>notebooks/03_propensity_score_matching.ipynb]
  C --> C1[Figures<br/>outputs/figures/fig_02*.png]

  B --> D[PS matching (1:1 NN + caliper)<br/>src/causal.match_ps]
  D --> E[Matched sample<br/>data/processed/hillstrom_matched.csv]
  D --> F[Match panel<br/>data/processed/psm_match_panel.json]
  E --> G[Balance check (SMD)<br/>src/causal.check_balance]
  G --> G1[Figure<br/>outputs/figures/fig_03_smd_before_after.png]
  E --> H[ATE on matched pairs + pair bootstrap<br/>src/causal.compute_ate]
  H --> H1[Figures<br/>outputs/figures/fig_04*.png]

  A --> I[S/T/X-Learner CATE<br/>src/uplift.fit_*_learner]
  I --> I1[Figure<br/>outputs/figures/fig_05_cate_distributions.png]
  I --> J[Qini / AUUC<br/>src/uplift.compute_qini]
  J --> J1[Figure<br/>outputs/figures/fig_06_qini_curves.png]
  I --> K[CATE vectors<br/>data/processed/cate_vectors.npz]
  J --> L[Qini results<br/>data/processed/qini_results.json]
```

## 6. Key Method Decisions

以下为 Phase 2 的关键方法选择（每条都能在仓库中找到可核验证据入口），用于解释“为什么这样做”和“为什么结果可信”。

- PS 用 Logistic Regression 并对输出做 clip（`[0.01, 0.99]`），是为了在 IPW/X-Learner 权重计算中避免除零与极端数值爆炸；实现与断言见 `src/causal.py`。
- Common support 不只用“图看起来重叠”讲，而是同时输出 OVL、PS range overlap ratio、以及 IPW 极端权重比例（`weight>10`）；这把 positivity/overlap 从“主观判断”变成了可审计指标（见 `notebooks/03_propensity_score_matching.ipynb`）。
- 匹配采用 1:1 nearest neighbor + no replacement，并把 caliper 固化为 `0.2 * std(ps)`（配置为 `psm.caliper_factor=0.2`、`psm.matching_ratio=1`，见 `configs/config.yml`；实现见 `src/causal.py`）；同时在实现上用 k-NN（`k=min(200, n_treated)`）来解决 RCT 下 PS 极度集中导致的 tie collision；这解释了为什么在 `ps.std(full)=0.0039` 的情况下仍能得到接近满覆盖的匹配结果（见 `src/causal.py` 与 `data/processed/psm_match_panel.json`）。
- 平衡性用 SMD（effect size）而不是 p-value，是为了避免大样本下把“微小差异”误读成“重要偏差”；SMD 的 pooled SD 计算与阈值断言见 `src/causal.py`，Love plot 见 `outputs/figures/fig_03_smd_before_after.png`。
- 不确定性估计采用 pair-level bootstrap（按 `match_id` 重采样，`n_bootstrap=1000`），是为了保留 matched pairs 的依赖结构；行级 bootstrap 会破坏配对并夸大方差（实现见 `src/causal.py`，图见 `outputs/figures/fig_04b_bootstrap_ci.png`）。
- Uplift 侧同时运行 S/T/X-Learner，并用 Qini coefficient 选优；learner 的基础超参由配置提供：`uplift.n_estimators=100`、`uplift.max_depth=5`、`general.random_state=42`（见 `configs/config.yml`），并在 `notebooks/04_uplift_modeling.ipynb` 中以 `test_size=0.3` 做了 train/test split。结果也显示 X-Learner 的 Qini Coefficient `1.719097` 最高（见 `notebooks/04_uplift_modeling.ipynb` 与 `data/processed/qini_results.json`）。

## 7. Verify in 2 Minutes

GitHub 浏览（不跑代码）也能快速核验本报告的关键主张：

1) 打开 `notebooks/03_propensity_score_matching.ipynb`，在 stdout 里核验：
   - Setup：`df.shape=(64000, 16) | X.shape=(64000, 9) | T.mean=0.6671 | Y.mean=0.9031%`。
   - Positivity：`OVL=0.9880`、`Overlap Ratio: 95.79%`、`Extreme weights: 0.00% (0/64,000)`。
   - Matching：`Matched samples: Control=21,305 | Treated=21,305`。
   - ATE：`ATE (PSM) = 0.502% | 95% CI = [0.324%, 0.690%]` 与 `ATE (Naive RCT benchmark) = 0.495% | abs diff = 0.007%`。

2) 打开 `notebooks/04_uplift_modeling.ipynb`，在 stdout/表格输出中核验：
   - Split：`train=(44800, 9) | test=(19200, 9)`，以及 `ps.std(full)=0.0039`。
   - Qini summary 表：X 的 Qini Coefficient `1.719097` 为最佳，S 为 `1.670222`，T 为 `-0.679497`。

3) 直接查看图表落盘是否存在：
   - `outputs/figures/fig_02b_ps_overlap.png`（PS overlap）
   - `outputs/figures/fig_03_smd_before_after.png`（Love plot）
   - `outputs/figures/fig_04b_bootstrap_ci.png`（bootstrap CI）
   - `outputs/figures/fig_06_qini_curves.png`（Qini 曲线）

可选：本地复跑（需要本地存在 `data/raw/hillstrom.csv`，且 `data/` 默认 gitignored）：

- `jupyter nbconvert --execute --to notebook --inplace notebooks/03_propensity_score_matching.ipynb`
- `jupyter nbconvert --execute --to notebook --inplace notebooks/04_uplift_modeling.ipynb`

复跑后可额外查看落盘审计产物：`data/processed/psm_match_panel.json`、`data/processed/qini_results.json`、`data/processed/cate_vectors.npz`。

---

## 8. Mathematical Core (What Was Used)

本节把 Phase 2 用到的关键公式统一写清楚，便于在文档审阅与后续复现时使用同一套符号；每个公式同时给出 LaTeX 与 plain text。

### 8.1 Propensity Score e(x)

- LaTeX:
  $$e(x)=\mathbb{P}(T=1\mid X=x)$$
- Plain text:
  `e(x) = P(T=1 | X=x)`

实现位置：`src/causal.py` 的 `estimate_ps(...)`（LogisticRegression，且把 `ps` clip 到 `[0.01, 0.99]`）。

### 8.2 Caliper (as implemented)

本阶段在 PS 空间做距离约束（而不是 logit(PS) 空间），caliper 被实现为全局 PS 标准差的缩放：

- LaTeX:
  $$c=0.2\cdot \mathrm{SD}(ps)\\
  \text{match if } |ps_i-ps_j|\le c$$
- Plain text:
  `c = 0.2 * std(ps)`
  `match if abs(ps_i - ps_j) <= c`

证据入口：`configs/config.yml`（`psm.caliper_factor: 0.2`）、`src/causal.py`（`caliper = 0.2 * std(ps)`）。

### 8.3 Overlap Coefficient (OVL)

- LaTeX:
  $$\mathrm{OVL}=\int \min\big(f_1(p), f_0(p)\big)\,dp,\quad p\in[0,1]$$
- Plain text:
  `OVL = integral min(f_treated(p), f_control(p)) dp`

证据入口：`notebooks/03_propensity_score_matching.ipynb` stdout 打印 `Overlap Coefficient (OVL): 0.9880`，并把阈值检查写成 `OVL ≥ 0.8: PASS`。

### 8.4 Standardized Mean Difference (SMD)

- LaTeX:
  $$\mathrm{SMD}(X)=\frac{|\bar{X}_1-\bar{X}_0|}{\sqrt{\frac{s_1^2+s_0^2}{2}}}$$
- Plain text:
  `SMD = abs(mean(X|T=1) - mean(X|T=0)) / sqrt((var1 + var0)/2)`

实现位置：`src/causal.py` 的 `check_balance(...)`。

### 8.5 ATE on Matched Pairs

本阶段把 matched pairs 的每一对差值当作统计单元：

- LaTeX:
  $$\widehat{ATE}_{\mathrm{PSM}}=\frac{1}{n_{pairs}}\sum_{k=1}^{n_{pairs}}\Big(Y_{k,1}-Y_{k,0}\Big)$$
- Plain text:
  `ATE_PSM = (1/n_pairs) * sum_k (Y_treated_in_pair_k - Y_control_in_pair_k)`

实现位置：`src/causal.py` 的 `compute_ate(...)`（通过 `match_id` pivot 后计算 diffs）。

### 8.6 Pair-Level Bootstrap (by match_id)

- LaTeX（用 match_id 作为重采样单位）：
  $$\widehat{ATE}^{*(b)}=\frac{1}{n_{pairs}}\sum_{k\in\mathcal{S}_b}\Delta_k,\quad \mathcal{S}_b\text{ is a bootstrap sample of pairs}$$
  $$\mathrm{CI}_{95\%}=[Q_{2.5\%}(\widehat{ATE}^*),\;Q_{97.5\%}(\widehat{ATE}^*)]$$
- Plain text：
  `Resample match_ids with replacement; recompute ATE on resampled pairs; CI = [p2.5, p97.5] of bootstrap_ates`

实现与参数：`src/causal.py` 的 `compute_ate(...)` 默认 `n_bootstrap=1000`；该数值在 `notebooks/03_propensity_score_matching.ipynb` 中也被显式设为 `n_bootstrap = 1000` 并打印了结果。

### 8.7 X-Learner Weighting

本阶段的 X-Learner 最终组合权重使用 propensity score：

- LaTeX:
  $$\hat{\tau}(x)=(1-e(x))\,\hat{\tau}_1(x)+e(x)\,\hat{\tau}_0(x)$$
- Plain text:
  `tau_hat(x) = (1 - e(x)) * tau1_hat(x) + e(x) * tau0_hat(x)`

实现位置：`src/uplift.py` 的 `fit_x_learner(...)`（代码为 `cate = (1-ps_out)*tau_1 + ps_out*tau_0`）。

### 8.8 Qini Coefficient

本阶段将 Qini 系数定义为 AUUC 与 random baseline AUUC 的差：

- LaTeX:
  $$\mathrm{AUUC}=\int_0^1 Q(u)\,du,\quad \mathrm{QiniCoef}=\mathrm{AUUC}-\mathrm{AUUC}_{\mathrm{random}}$$
- Plain text:
  `AUUC = area_under(QiniCurve)`
  `QiniCoef = AUUC - RandomAUUC`

实现位置：`src/uplift.py` 的 `compute_qini(...)`（`n_bins=20`，AUUC 使用 `np.trapezoid` 计算），可核验结果落盘在 `data/processed/qini_results.json`。

---

## 9. Results (Verifiable)

### 9.1 PSM: Overlap / Positivity Was Quantified

`notebooks/03_propensity_score_matching.ipynb` 的 stdout 提供了可核验的 positivity 证据：

- `OVL = 0.9880`（阈值检查 `OVL ≥ 0.8: PASS`）。
- PS range overlap：Treatment `[0.6555, 0.6995]`，Control `[0.6557, 0.6978]`，Overlap ratio `95.79%`。
- 极端 IPW 权重比例：`0.00% (0 / 64,000 samples)`（`weight > 10`）。

解释上，这组指标在 RCT 里体现了 very strong overlap；它的价值不在于重复证明 RCT（Phase 1 已经说明），而在于：当 pipeline 迁移到观察性数据时，positivity 诊断能直接暴露“估计在 support 外漂移”的风险。

### 9.2 PSM: Matching Coverage and Estimand Was Made Explicit

匹配规模与覆盖率可以从两处核验：

- Notebook stdout（`notebooks/03_propensity_score_matching.ipynb`）：
  - Total: Control=`21,306`，Treated=`42,694`
  - Matched: Control=`21,305`，Treated=`21,305`
  - `Match rate ≈ 100.00%`

- JSON 面板（`data/processed/psm_match_panel.json`）：
  - `n_pairs=21305`，`max_pairs=21306`
  - `match_rate_max=0.999953...`
  - `treated_utilization=0.499016...`（2:1 设计下，匹配天然只会用掉约一半 treated）

解释上，文档明确给出 `treated_utilization`，是为了避免被“match rate=100%”误导：在 treated 大于 control 的情况下，控制组覆盖率很容易接近 100%；真正决定 estimand 外推范围的是 `n_pairs / min(n_treated, n_control)` 这类 coverage 指标。

### 9.3 PSM: ATE Was Consistent With RCT Benchmark

`notebooks/03_propensity_score_matching.ipynb` 在同一 cell 里并排打印了两条结果：

- `ATE (PSM) = 0.502% | 95% CI = [0.324%, 0.690%]`
- `ATE (Naive RCT benchmark) = 0.495% | abs diff = 0.007%`

解释上，这种“差异很小”支持了该实现链路在 RCT benchmark 上的有效性：`src/causal.py` 的 PS→match→SMD→ATE 链路没有引入系统性偏差，并且 bootstrap CI 是在配对结构下估计的。

### 9.4 Uplift: CATE Was Estimated and Then Evaluated (Not Just Plotted)

`notebooks/04_uplift_modeling.ipynb` 的 setup stdout 明确了数据切分与特征集合：

- `df.shape=(64000, 16)`，`X.shape=(64000, 9)`
- `train=(44800, 9)`，`test=(19200, 9)`（`test_size=0.3`）
- Covariates（`n=9`）：`['recency','history','mens','womens','newbie','channel_Phone','channel_Web','zip_Surburban','zip_Urban']`

三种 learner 的 CATE 分布对比图落盘在 `outputs/figures/fig_05_cate_distributions.png`，同时 Notebook 还打印了 test 集上的描述统计（例如 S-Learner `mean=0.004402`、X-Learner `max(|cate_x|)=0.065357` 等，见 `notebooks/04_uplift_modeling.ipynb` 的各 Section 输出表）。

更关键的是，Phase 2 不把“CATE 分布更宽”当成“更好”，而是用 Qini 去量化“排序 uplift 是否有效”。在 `data/processed/qini_results.json` 中可核验：

- `meta.n_test = 19200`，`meta.n_bins = 20`
- X-Learner：AUUC `16.153513...`，Random AUUC `14.434415...`，Qini Coefficient `1.719097...`
- S-Learner：Qini Coefficient `1.670221...`
- T-Learner：Qini Coefficient `-0.679497...`

解释上，T-Learner 在该实现与该超参下出现负 Qini，说明 uplift 建模不能只看“是否跑通模型”；评估指标本身就是 guardrail。当指标为负时，更合理的动作是回到 feature leakage、概率校准、样本不平衡与 learner 结构假设去定位原因（相关防线在 `src/uplift.py` 的 forbidden columns 校验与概率校正函数 `_correct_weighted(...)`）。

## 10. Interpretation and Limits

Phase 2 的边界需要明确：

- 在 Hillstrom RCT 语境下，PSM 的主要作用是做链路审计与回归验证，而不是替代随机化这一主识别策略。
- Qini / AUUC 衡量的是 test set 上的 uplift 排序质量，本身并不直接给出预算配置或 ROI 决策。
- 本阶段的直接产出是 matched-sample diagnostics、CATE vectors 与 Qini 结果；这些产物将在 Phase 3 中继续用于分群与 ROI 仿真。

## 11. Concise Summary

### 11.1 Short Summary

Phase 2 先将因果识别链路工程化：从 `data/processed/hillstrom_features.csv` 出发，用 `src/causal.estimate_ps` 估计 propensity score，并在 `notebooks/03_propensity_score_matching.ipynb` 中完成 positivity / overlap 的量化诊断，结果为 `OVL=0.9880`、PS overlap ratio `95.79%`、极端 IPW 权重 `0/64,000`。

随后，Phase 2 采用 1:1 no-replacement matching（`caliper=0.2*std(ps)`）构造 `21,305` 个 matched pairs，并通过 SMD / Love plot 复核匹配后未引入新的明显偏差。在 matched pairs 上进一步进行 `1,000` 次 pair-level bootstrap，得到 `PSM ATE=0.502%`、`95% CI=[0.324%,0.690%]`，与 RCT naive benchmark `0.495%` 仅相差 `0.007%`。

在 uplift 建模侧，Phase 2 于 `notebooks/04_uplift_modeling.ipynb` 中对比 S/T/X-Learner，并用 Qini 曲线评估排序能力；在 `n_test=19,200` 的 test 集上，X-Learner 的 Qini Coefficient `1.719097` 表现最佳。

### 11.2 Structured Recap

- Context：数据来自 Hillstrom RCT，目标从“验证总体 ATE”推进到“获得可用于 targeting 的 uplift 排序信号”。
- Objective：将 PSM 与 uplift/CATE 构建为一条可审计、可复现、可回归验证的分析链路。
- Approach：完成 PS 估计与 overlap 诊断（OVL / overlap ratio / extreme weights），再进行 caliper matching、SMD 平衡性检查、matched ATE 与 pair bootstrap，并以 S/T/X-Learner + Qini 评估 uplift 排序能力。
- Outcome：PS overlap 指标全部通过（如 `OVL=0.9880`），PSM ATE 与 naive ATE 高度一致（`0.502%` vs `0.495%`），且 X-Learner 的 Qini Coefficient 最高（`1.719097`）。
