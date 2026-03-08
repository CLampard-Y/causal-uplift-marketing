# Phase 1 Execution Report


本报告记录 Phase 1 的实际实现、可核验证据与主要结论，供仓库审阅、项目归档和后续复现参考。文中仅引用可在仓库中直接验证的结果（Notebook stdout/Markdown、配置文件、代码常量、已落盘图表）。

## 1. Overview

在 Hillstrom RCT（`n=64000`）中，邮件将转化率从 `0.5726%` 提升到 `1.0681%`，总体绝对 uplift（difference-in-means）为 `Naive ATE = +0.4955%`。同时，协变量平衡性检查显示各项 SMD 均远小于 `0.1`，因此这一差异可以作为因果基线来解释。

但总体转化均值仅为 `0.9031%`，且 `spend` 的零值比率高达 `99.10%`，说明若直接用“平均值”讨论 ROI，很容易被稀疏事件和统计口径差异带偏。更关键的是，按渠道分层后的 uplift 在 `+0.3573%` 到 `+0.8609%` 之间波动，表明“总体平均”会掩盖明显的投放效率差异。因此，Phase 1 的核心结论是：邮件整体有效，但若要回答“哪些分层具有更高的预期处理效率”，必须进入 uplift/CATE 分析。

- LaTeX（把 uplift 翻译为增量转化量级；假设同一人群“全量触达 vs 不触达”）：
  $$\widehat{\Delta N} = n \cdot \widehat{ATE}$$
- Plain text：
  `DeltaN_hat = n * ATE_hat`
- Using verifiable values（用于量级换算，不替代 ROI 结论）：`n=64000`，`ATE_hat=0.004955`（对应 `0.4955%`），则 `DeltaN_hat = 64000 * 0.004955 = 317.12`。

## 2. Evidence Policy (Verifiable Numbers Only)

本报告中的数值遵循以下规则：
- 仅使用在 `notebooks/*.ipynb` 输出、`configs/config.yml`、`src/*.py`、或 `outputs/` 中可直接核验的数值。
- 避免引用只出现在历史说明文本、或无法从当前仓库产物复核的数字。
- 可由可核验数字推导出的“显式计算”（例如 `0.9031% * 64000`）会写明计算过程与来源。

## 3. Scope

Phase 1 的工作范围聚焦以下内容：数据摄入/清洗、EDA、朴素 ATE（naive difference-in-means）、处理效应异质性（HTE）展示、RCT 随机化平衡性检查、ATE 偏差分解框架、特征工程决策（特别是中介变量 `visit` 的剔除，以及 `spend` 的“辅助指标”定位）。

## 4. Key Artifacts

- Configuration: `configs/config.yml`
- Data pipeline (cleaning + features): `src/data_utils.py`
- EDA notebook: `notebooks/01_data_ingestion_and_eda.ipynb`
- Naive ATE + HTE + RCT validation notebook: `notebooks/02_bias_exposure_and_naive_ate.ipynb`
- Phase 1 regression / DoD notebook: `notebooks/Phase1_DoD.ipynb`
- Figures (Phase 1):
  - `outputs/figures/eda_treatment_control_counts.png`
  - `outputs/figures/eda_history_dist.png`
  - `outputs/figures/eda_recency_dist.png`
  - `outputs/figures/eda_channel_dist.png`
  - `outputs/figures/eda_zipcode_dist.png`
  - `outputs/figures/eda_conversion_rate.png`
  - `outputs/figures/eda_spend_dist.png`
  - `outputs/figures/eda_covariate_comparison.png`
  - `outputs/figures/eda_correlation_heatmap.png`
  - `outputs/figures/fig_01_naive_comparison.png`
  - `outputs/figures/fig_01b_ate_heterogeneity.png`
  - `outputs/figures/fig_01c_covariate_balance_rct.png`

## 5. End-to-End Pipeline Sketch

下图把 Phase 1 的“可复现执行路径”用真实产物串起来：数据从原始 CSV 进入清洗与断言，再产出 EDA/因果基线/分层异质性与特征表；`notebooks/Phase1_DoD.ipynb` 作为回归门禁用于复核关键可核验数值与图表落盘（注意：`data/raw/` 与 `data/processed/` 为本地复现目录，默认 gitignored，详见 `data/README.md`）。

```mermaid
flowchart LR
  A[Raw CSV<br/>data/raw/hillstrom.csv] --> B[load_and_clean(...)<br/>src/data_utils.py]
  B --> C[Cleaned table<br/>data/processed/hillstrom_cleaned.csv]
  C --> D[EDA + DQ signals<br/>notebooks/01_data_ingestion_and_eda.ipynb]
  D --> E[EDA figures<br/>outputs/figures/eda_*.png]
  C --> F[Naive ATE + HTE + RCT balance<br/>notebooks/02_bias_exposure_and_naive_ate.ipynb]
  C --> G[build_features(df, config)<br/>src/data_utils.py]
  G --> H[Feature table<br/>data/processed/hillstrom_features.csv]
  F --> I[Phase 1 verifiable claims<br/>ATE/HTE/SMD]
  H --> J[Regression / DoD gate<br/>notebooks/Phase1_DoD.ipynb]
  I --> J
```

## 6. Key Method Decisions

以下为 Phase 1 的关键方法选择（均已在仓库中落地，并附可直接核验的证据入口），用于解释“为什么这样做”。

- 本阶段将 `segment` 映射为二元处理变量 `treatment`（`Mens E-Mail`/`Womens E-Mail` -> 1，`No E-Mail` -> 0），以便把后续所有输出统一为 `T in {0,1}` 的因果分析链路。证据：`src/data_utils.py`（映射逻辑）；`notebooks/01_data_ingestion_and_eda.ipynb`（包含新增 `treatment` 的 `shape=(64000, 13)` 输出）。
- 本阶段使用 difference-in-means 作为总体因果基线，是因为 RCT 的可观测协变量平衡性在 effect-size 指标上成立（例如 `history` SMD `0.0071`，并打印/断言 `All covariates have SMD < 0.1`），因此朴素组间差可作为因果基线而非仅作相关性展示。证据：`notebooks/02_bias_exposure_and_naive_ate.ipynb`（SMD 与断言输出）；`notebooks/01_data_ingestion_and_eda.ipynb`（SMD 表 `num_imbalanced = 0`）。
- 本阶段使用 SMD 而不是 p-value 记录平衡性证据，是为了避免在大样本下把“微小差异”误读为“统计显著即重要”，并保持表述更贴近工程决策（effect size 优先）。证据：`notebooks/01_data_ingestion_and_eda.ipynb`（SMD 输出表）；`notebooks/02_bias_exposure_and_naive_ate.ipynb`（SMD 打印与阈值断言）。
- 本阶段明确将 `visit` 排除出特征表/协变量集合，因为它表现为 treatment 的下游中介：treatment 组 visit rate `16.70%` 高于 control `10.62%`（差 `0.0609`），若控制 `visit` 会引入 mediator bias 并低估真实因果路径贡献。证据：`notebooks/01_data_ingestion_and_eda.ipynb`（visit rate 输出）；`src/data_utils.py`（特征表断言不包含 `visit`）；本报告 `## 7.3 Why Drop visit`。
- 本阶段保留 `spend` 但不将其作为 Phase 1 的主结论目标，是因为两周消费存在极端零膨胀（`Zero spend ratio: 99.10%`），Phase 1 优先用更稳健的二值 `conversion` 建立因果基线；`spend` 作为后续 ROI/价值量化输入被保留。证据：`notebooks/02_bias_exposure_and_naive_ate.ipynb`（zero spend ratio 输出）；`src/data_utils.py`（保留 `spend` 并在注释/断言中声明定位）；本报告 `## 7.4 Why Keep spend But Treat It as Auxiliary`。
- 本阶段在分层 ATE 中采用 Wilson/Newcombe-Wilson 区间，是因为整体转化率约 `0.9031%` 属于低比例二项事件，正态近似在这种稀疏率下不稳健，区间构造需要更保守可靠的方案来支持进一步解释。证据：`notebooks/02_bias_exposure_and_naive_ate.ipynb`（相关实现说明与输出表）；本报告 `## 5.1`/`## 5.2`/`## 5.3`。

## 7. Verify in 2 Minutes

如果只用 GitHub 浏览（不跑代码），可以按“证据最短路径”核验本报告的关键数值与图表是否真实存在：打开 `notebooks/Phase1_DoD.ipynb` 作为回归门禁；分别在 `notebooks/01_data_ingestion_and_eda.ipynb` 核验 `shape=(64000, 13)` 与 `visit` 的组间差异（`10.62%` vs `16.70%`），在 `notebooks/02_bias_exposure_and_naive_ate.ipynb` 核验总体 ATE（`+0.4955%`）、渠道分层 HTE 范围（`+0.3573%`~`+0.8609%`）、以及 `Zero spend ratio: 99.10%` 和 `All covariates have SMD < 0.1` 的平衡性断言；图表证据可直接在 `outputs/figures/` 下查看对应 PNG。

如需本地可选复跑（需要本地存在 `data/raw/hillstrom.csv`）：创建虚拟环境并安装依赖后，优先执行 `jupyter nbconvert --execute --to notebook --inplace notebooks/Phase1_DoD.ipynb` 以一次性复核 Phase 1 的关键输出是否可复现；若只做无数据的快速健全性检查，可先跑 `python -m compileall src` 验证 `src/` 语法与导入无误。

## 8. Background and Objective

本项目以 Hillstrom 邮件营销实验数据为载体，目标是在“可复现的工程管道”上建立一条因果推断分析链路：先用干净可信的数据底座与 EDA 建立数据直觉和质量信号，再用朴素 ATE 给出总体效果，然后用分层 ATE 暴露显著异质性，最后用 RCT 平衡性与偏差分解公式解释“为什么这里朴素估计可视为因果基线、但平均值不足以支撑精准投放”。

## 9. Data Ingestion and Cleaning

### 9.1 What Was Done

清洗与摄入由 `src/data_utils.py` 的 `load_and_clean(...)` 完成，并在 `notebooks/01_data_ingestion_and_eda.ipynb` 中以可见输出进行验证。核心动作包括：
- 读取原始 CSV（路径来自 `configs/config.yml` 的 `paths.raw_data`，默认 `data/raw/hillstrom.csv`）。
- 采用 ELT 思路先落“原始文本快照”，再做类型转换与清洗，形成可追溯数据血缘：`data/raw/hillstrom_raw_text_YYYYMMDD_HHMMSS.csv`（见 `src/data_utils.py`）。
- 对数值列进行缺失填充（中位数）与强制类型；对类别列进行缺失填充（众数）。
- 将 `segment` 映射为二元处理变量 `treatment`：`Mens E-Mail`/`Womens E-Mail` -> 1，`No E-Mail` -> 0（见 `src/data_utils.py`）。
- 关键 DQ 防线：
  - `recency` clip 到 `[1, 12]`（见 `src/data_utils.py`）。
  - `spend` 强制非负（负值置 0）。
  - 行数范围断言：`60000 <= n_rows <= 70000`。
  - treatment 比例断言：`0.60 <= mean(treatment) <= 0.70`。

### 9.2 Results (Verifiable)

从 `notebooks/01_data_ingestion_and_eda.ipynb` 的 stdout 可直接验证：
- 数据加载后的形状为 `shape=(64000, 13)`（包含新增 `treatment` 列）。

另外，清洗阶段对 `visit` 做了一个“时序污染/中介一致性”信号检查（并不是把 `visit` 当作协变量，而是用它验证其确实表现为 post-treatment mediator）。在 `notebooks/01_data_ingestion_and_eda.ipynb` 的 stdout 中可核验：
- Control group visit rate: `0.1062 (10.62%)`
- Treatment group visit rate: `0.1670 (16.70%)`
- Difference: `0.0609`

这些数字为后续 Phase 1 的一个关键建模决策提供了证据：`visit` 的确被 treatment 显著“抬升”，更像 treatment 的下游中介变量而非稳定的 pre-treatment confounder。

## 10. Exploratory Data Analysis (EDA)

### 10.1 What Was Done

EDA 主要在 `notebooks/01_data_ingestion_and_eda.ipynb` 完成，产出以 `outputs/figures/eda_*.png` 的形式落盘，覆盖：样本结构（treatment/control）、主要变量分布（`recency/history/spend` 等）、类别分布（`channel/zip_code`）、目标稀疏性（`conversion`）、相关性速览，以及组间协变量平衡诊断（SMD）。

### 10.2 Results (Verifiable)

从 `notebooks/01_data_ingestion_and_eda.ipynb` 的 `df.describe(include='all')` 输出可核验的关键统计包括：
- 样本量：`count = 64000`
- 转化率（均值）：`mean(conversion) = 0.009031`（即 `0.9031%`）
- treatment 比例（均值）：`mean(treatment) = 0.667094`（即 `66.7094%`）
- spend（两周消费）均值：`mean(spend) = 1.050908`，且 `50%/75%` 分位数均为 `0.0`（提示明显零膨胀）
- history（历史消费）均值：`mean(history) = 242.085656`，最大值 `max(history) = 3345.93`（明显右偏长尾）

从 `notebooks/02_bias_exposure_and_naive_ate.ipynb` 的 stdout 可核验：
- Conversion rate: `0.9031%`
- Treatment:Control ratio: `42694:21306`
- Zero spend ratio: `99.10%`

### 10.3 Balance Check Signal in EDA (SMD)

EDA 中对一组关键协变量（`recency/history/mens/womens/newbie`）计算了 SMD。`notebooks/01_data_ingestion_and_eda.ipynb` 的输出表显示：
- `history` SMD = `0.007063`
- `mens` SMD = `0.006611`
- `womens` SMD = `0.006265`
- `recency` SMD = `0.006004`
- `newbie` SMD = `0.000836`
- `imbalanced` 全部为 `False`，且 `num_imbalanced = 0`（注意：Notebook 的英文提示语句存在口误，但数值与布尔列可直接证明“没有协变量超过 0.1 阈值”）。

这一步用于：不依赖 p-value（样本大时易“显著”）而使用 effect-size 指标（SMD）来判断平衡性，给出“RCT 随机化质量”的可视化证据链。

## 11. Naive ATE (Difference-in-Means)

### 11.1 Definition and Formula

本阶段使用最朴素的 difference-in-means 作为总体处理效应基线。

- LaTeX:
  $$\mathrm{ATE}_{\text{naive}} = \mathbb{E}[Y\mid T=1] - \mathbb{E}[Y\mid T=0]$$
- Plain text:
  `ATE_naive = mean(Y | T=1) - mean(Y | T=0)`

其中 `Y = conversion`，`T = treatment`。

### 11.2 Results (Verifiable)

`notebooks/02_bias_exposure_and_naive_ate.ipynb` 的 stdout 给出总体结果：
- Treatment conversion rate: `1.0681%`
- Control conversion rate: `0.5726%`
- Naive ATE (abs): `0.4955%`
- Relative Lift: `86.53%`

解读上需要同时强调“绝对提升”和“相对提升”：在极低基线转化率（`0.9031%`）下，相对提升很容易看起来很大，但业务决策更应以绝对 uplift（百分点）与成本约束共同评估。

## 12. Heterogeneous Treatment Effects (HTE) via Stratified ATE

### 12.1 Why Stratify

在 RCT 平衡成立的前提下，总体朴素 ATE 可以作为无偏基线，但它不足以回答“哪些分层具有更高的预期处理效率”。因此 Phase 1 通过分层 ATE（按单个维度分组）来暴露异质性，并为 Phase 2 的个体级 CATE/uplift modeling 提供动机与方向。

同时，由于转化率约为 `0.9%` 的稀疏事件，Notebook 使用 Wilson/Newcombe-Wilson 的区间方式来构造比例差的置信区间（见 `notebooks/02_bias_exposure_and_naive_ate.ipynb` 中 `Calculate ATE and Wilson confidence interval...` 的实现说明）。

### 12.2 Key Formula (Wilson Score Interval for a Proportion)

该公式用于单组转化率 `p` 的区间估计，是“低比例二项事件”中比正态近似更稳健的常用方案。

- LaTeX (Wilson interval for $\hat{p}$ with sample size n and z-score z):
  $$\frac{\hat{p}+\frac{z^2}{2n} \pm z\sqrt{\frac{\hat{p}(1-\hat{p})}{n}+\frac{z^2}{4n^2}}}{1+\frac{z^2}{n}}$$
- Plain text:
  `(p_hat + z^2/(2n) +/- z*sqrt(p_hat*(1-p_hat)/n + z^2/(4n^2))) / (1 + z^2/n)`

### 12.3 Results (Verifiable)

分层结果直接来自 `notebooks/02_bias_exposure_and_naive_ate.ipynb` 的 stdout：

**By Channel**

| Subgroup | ATE (abs) | 95% CI | n_T | n_C |
|---|---:|---|---:|---:|
| Multichannel | +0.8609% | [+0.3602%, +1.3136%] | 5,156 | 2,606 |
| Web | +0.5330% | [+0.3091%, +0.7417%] | 18,844 | 9,373 |
| Phone | +0.3573% | [+0.1462%, +0.5517%] | 18,694 | 9,327 |

**By History (quantile bins, q=3)**

| Subgroup | ATE (abs) | 95% CI | n_T | n_C |
|---|---:|---|---:|---:|
| Low | +0.4380% | [+0.2100%, +0.6466%] | 14,264 | 7,071 |
| Medium | +0.4119% | [+0.1788%, +0.6252%] | 14,190 | 7,143 |
| High | +0.6358% | [+0.3331%, +0.9173%] | 14,240 | 7,092 |

**By Newbie**

| Subgroup | ATE (abs) | 95% CI | n_T | n_C |
|---|---:|---|---:|---:|
| Existing Customer | +0.3569% | [+0.1284%, +0.5697%] | 21,245 | 10,611 |
| New Customer | +0.6330% | [+0.4491%, +0.8068%] | 21,449 | 10,695 |

**By Recency (bins: 1-6 vs 7-12)**

| Subgroup | ATE (abs) | 95% CI | n_T | n_C |
|---|---:|---|---:|---:|
| Active (1-6) | +0.4561% | [+0.2416%, +0.6578%] | 24,381 | 12,204 |
| Dormant (7-12) | +0.5496% | [+0.3634%, +0.7239%] | 18,313 | 9,102 |

业务上，这些分层结果说明：即便总体 ATE 只有 `+0.4955%`，不同子群体对邮件的响应仍存在显著差异（例如按渠道分层时从 `+0.3573%` 到 `+0.8609%`）。这就是“平均数会掩盖决策空间”的直接证据。

## 13. RCT Balance Check and Bias Decomposition Framework

### 13.1 SMD Definition and Formula

SMD 用于衡量 Treatment/Control 组在某个协变量上的均值差异强度（effect size），常用经验阈值为 `abs(SMD) < 0.1` 视为可接受平衡。

- LaTeX:
  $$\mathrm{SMD}(X)=\frac{\mu_T-\mu_C}{\sqrt{(\sigma_T^2+\sigma_C^2)/2}}$$
- Plain text:
  `SMD(X) = (mu_T - mu_C) / sqrt((var_T + var_C)/2)`

### 13.2 RCT Validation Results (Verifiable)

`notebooks/02_bias_exposure_and_naive_ate.ipynb` 的 stdout 打印了 RCT 平衡性检查：
- `history` SMD: `0.0071`
- `mens` SMD: `0.0066`
- `womens` SMD: `0.0063`
- `recency` SMD: `0.0060`
- `newbie` SMD: `0.0008`
- 并通过断言：`All covariates have SMD < 0.1`

这形成了一条完整证据链：处理分配在可观测协变量层面高度平衡，符合 RCT 随机分配的预期。

### 13.3 ATE Bias Decomposition (Conceptual Framework)

Phase 1 将朴素组间差异拆解为“因果效应 + 选择偏差”两部分，作为从 RCT 迁移到观察性数据时的共同语言。

- LaTeX:
  $$\begin{aligned}
  \mathbb{E}[Y\mid T=1]-\mathbb{E}[Y\mid T=0]
  &= \underbrace{\{\mathbb{E}[Y(1)\mid T=1]-\mathbb{E}[Y(0)\mid T=1]\}}_{\text{ATT}}
  + \underbrace{\{\mathbb{E}[Y(0)\mid T=1]-\mathbb{E}[Y(0)\mid T=0]\}}_{\text{Selection Bias}}
  \end{aligned}$$
- Plain text:
  `E[Y|T=1] - E[Y|T=0] = ATT + (E[Y(0)|T=1] - E[Y(0)|T=0])`

在本项目的 RCT 语境下，平衡性检验支持“Selection Bias 近似为 0”的判断，因此朴素 difference-in-means 可作为因果效应的基线估计；但分层结果同时提示，业务上不应止步于总体平均，而要进入个体/细分层面的 uplift 建模。

## 14. Feature Engineering Decisions (Phase 1 Readiness)

### 14.1 What Was Done

特征工程由 `src/data_utils.py` 的 `build_features(df, config)` 完成，目标是生成 Phase 2 可直接消费的全数值特征表（写入 `config.paths.features_data`，默认 `data/processed/hillstrom_features.csv`）。主要决策如下：
- One-hot 编码：`channel` -> `channel_*`；`zip_code` -> `zip_*`。
- 右偏压缩：构造 `history_log = log(1 + history)`（实现为 `np.log1p(history)`）。
- 交叉购买信号：构造 `is_both_gender = 1(mens>0 and womens>0)`。
- 列删除：`segment/history_segment/channel/zip_code/visit`。
- 列保留：`treatment/conversion/spend`（并通过强制断言保证 `visit` 不会混入特征表）。

### 14.2 Key Formula (Feature Transform)

- LaTeX:
  $$\mathrm{history\_log} = \log(1+\mathrm{history})$$
- Plain text:
  `history_log = log(1 + history)`

### 14.3 Why Drop `visit` (Mediator Rationale)

`visit` 被明确视为 treatment 的下游中介变量：邮件 -> 访问 -> 转化。如果把 `visit` 当作协变量放入匹配/调整，会“控制掉”一部分真实因果路径，导致 ATE 被低估（典型的 mediator bias）。

此外，本仓库在 Phase 1 还用一个可核验的数值信号支持这一点：`notebooks/01_data_ingestion_and_eda.ipynb` 显示 treatment 组 visit rate `16.70%` 明显高于 control `10.62%`（差值 `0.0609`），更符合“post-treatment mediator”的行为模式。

### 14.4 Why Keep `spend` But Treat It as Auxiliary

`notebooks/02_bias_exposure_and_naive_ate.ipynb` 显示 `Zero spend ratio: 99.10%`。在这种极端零膨胀下，Phase 1 不使用 `spend` 作为 ATE 的主目标，以避免均值估计不稳定；但 `build_features` 仍保留 `spend`，用于后续 ROI/价值量化场景（见 `src/data_utils.py` 注释与断言）。

### 14.5 Covariate List in Config (and Collinearity Guard)

`configs/config.yml` 给出了 Phase 2/3 共享的协变量清单（如 `channel_Phone/channel_Web/zip_Surburban/zip_Urban` 等）。其中刻意不包含某些 one-hot 的 reference 类别以避免完全共线性（配置文件注释已说明线性可表示关系）。同时注意 `zip_Surburban` 的拼写与数据值一致（见 `notebooks/01_data_ingestion_and_eda.ipynb` 中 `zip_code` 的 top 值为 `Surburban`）。

## 15. Interpretation

Phase 1 的结果可以归纳为三层：

- 数据层：样本规模为 `64000`，treatment/control 约为 `42694/21306`；目标转化极为稀疏（`0.9031%`），`spend` 也呈现明显零膨胀（零值 `99.10%`）。
- 因果基线层：总体朴素 ATE（转化率差）为 `+0.4955%`，且可观测协变量层面的 RCT 平衡性良好（SMD 全部远小于 `0.1`）。
- 决策层：分层 ATE 显示出明显异质性（例如按渠道从 `+0.3573%` 到 `+0.8609%`），因此“全量一刀切投放”存在效率损失空间，进一步进入 uplift/CATE 分析是合理且必要的。

## 16. Limits

Phase 1 的结论边界如下：

- 分层 ATE 仅基于单一维度做边际分层，未同时控制其他协变量，因此不等价于因果意义上的条件处理效应 `CATE = E[Y(1)-Y(0)|X=x]`。
- RCT 平衡性的证据链基于可观测协变量，不能替代对实验执行层面潜在问题的全面排查（例如未观测变量或样本过滤规则带来的影响）；但它已足以支持“朴素 ATE 可作为基线”的判断。
- `spend` 的价值量化不作为 Phase 1 的因果主结论，以避免在零膨胀场景下过度解读均值变化。

## 17. Concise Summary

### 17.1 Short Summary

Phase 1 首先将数据管道做成可审计、可复现的流程：原始数据先保留一份文本快照，再完成严格的类型转换、缺失处理和断言，最后将 `segment` 映射为 `treatment`。随后，EDA 给出几项关键数据事实：样本量为 `64000`，转化率仅 `0.9031%`，属于稀疏事件；`spend` 零值比率达到 `99.10%`，呈现明显零膨胀；treatment/control 比例约为 `2:1`。

在 RCT 语境下，总体 difference-in-means 给出 `Treatment 1.0681% vs Control 0.5726%`，对应绝对 uplift `0.4955%`。进一步按渠道、历史消费、新老客和活跃度计算分层 ATE（配合 Wilson/Newcombe-Wilson 区间）后，可以直接看到异质性：例如 Multichannel 的 uplift 为 `0.8609%`，明显高于 Phone 的 `0.3573%`。结合 `SMD < 0.1` 的平衡性检查，Phase 1 最终建立了一个清晰的因果基线：邮件整体有效，但总体平均不足以支撑精准投放决策。

### 17.2 Structured Recap

Context: 邮件营销既要回答“活动整体是否有效”，也要判断“不同用户的响应是否一致”；只看总体平均，容易掩盖关键异质性。

Objective: 交付一个可复现、可核验的因果基线，并说明“平均效应不足以直接指导精准投放”。

Approach: 实现可追溯的清洗管道（含断言与 raw snapshot），完成 EDA 并用 SMD 检查平衡性；在 RCT 设定下计算总体 ATE（`0.4955%`），再通过分层 ATE 与 Wilson/Newcombe-Wilson 区间展示异质性；在特征工程上剔除中介变量 `visit`，保留 `spend` 作为 ROI 的辅助输入。

Outcome: 形成一条可复现、可核验的结论链：总体 uplift 为 `0.4955%`，不同渠道 uplift 介于 `0.3573%` 到 `0.8609%` 之间，RCT 平衡性通过（SMD 全部远小于 `0.1`）；这为 Phase 2 的个体级 CATE 建模提供了明确动机和方向。
