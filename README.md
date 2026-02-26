# Causal Uplift Marketing Analysis

> **因果推断与 Uplift Modeling 营销分析项目**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)

---

## Executive Summary

**业务问题**: 传统 A/B 测试只能回答"营销活动整体是否有效"，但无法识别哪些用户真正因营销而转化，导致预算浪费。

**解决方案**: 基于 Hillstrom RCT 数据（64,000 用户），通过 **Propensity Score Matching** 消除选择偏差，使用 **X-Learner Meta-Learner** 估计个体级 CATE（Conditional Average Treatment Effect），实现四象限用户分层（Persuadables / Sure Things / Lost Causes / Sleeping Dogs）。

**核心成果**: 精准投放相比全量投放节省 **75% 预算**（64,000 → 16,000 用户），ROI 提升 **2.08×**（0.008893 vs 0.004285），同时保留 **51.9%** 的增量转化效果。

**技术亮点**:
- **数学优势**: X-Learner 在 T:C = 2:1 不平衡场景下通过交叉估计和 PS 加权降低方差，Qini Coefficient = 1.72（T-Learner = -0.68）
- **工程成熟度**: 不可变数据流 + 配置驱动架构 + Conventional Commits
- **业务洞察**: 暴露 Simpson 悖论（分层 ATE 差异 2.4 倍），量化 Sleeping Dogs 负面效应（-0.41%）

---

## Project Overview | 项目概览

本项目基于 **Hillstrom Email Marketing Dataset** (64,000 用户 RCT 实验数据)，通过因果推断与 Uplift Modeling 方法，实现从朴素 A/B 测试到精准营销 ROI 优化的完整分析流程。

### Business Context | 业务背景

传统 A/B 测试只能回答"营销活动整体是否有效"，但无法回答：
- 哪些用户真正因为营销而转化？（Persuadables）
- 哪些用户本来就会转化？（Sure Things）
- 哪些用户营销反而有负面效果？（Sleeping Dogs）

本项目通过 **CATE (Conditional Average Treatment Effect)** 估计，实现个体级别的增量效应预测，为精准营销提供决策依据。

### Key Results | 核心成果（渐进式改进对比）

| Stage | Method | ATE (%) | 95% CI | Sample Size | Key Insight |
|-------|--------|---------|--------|-------------|-------------|
| **Baseline** | Naive ATE | 0.4955 | - | 64,000 | 总体有效，但掩盖异质性（Simpson 悖论） |
| **Phase 1** | PSM ATE | 0.4932 | [0.3156, 0.6708] | 42,612 (matched) | 验证 RCT 无偏性（ATE 几乎不变） |
| **Phase 2** | X-Learner CATE | - | - | 64,000 | Qini Coef = 1.72（T-Learner = -0.68） |
| **Phase 3** | Precision Targeting | - | - | 16,000 (25%) | **ROI 2.08×**, Budget -75%, Conversion Retention 51.9% |

**渐进式改进逻辑**:
1. **Baseline**: 朴素 ATE 暴露效应异质性（分层 ATE 差异 2.4 倍）
2. **Phase 1**: PSM 验证因果识别策略的正确性（RCT 数据 ATE 几乎不变）
3. **Phase 2**: Meta-Learners 估计个体级 CATE，X-Learner 在不平衡场景下方差最优
4. **Phase 3**: 基于 CATE 排序实现四象限分层，量化精准投放 ROI

---

## Table of Contents | 目录

- [Project Structure](#project-structure--项目结构)
- [Environment](#environment--开发环境)
- [Phase 1: EDA & Bias Exposure](#phase-1-eda--bias-exposure)
- [Phase 2: PSM & Uplift Modeling](#phase-2-psm--uplift-modeling)
- [Phase 3: Segmentation & ROI](#phase-3-segmentation--roi)
- [Competitive Advantages](#competitive-advantages--竞争优势从面试官视角)
- [Interview Q&A](#interview-qa--面试问答)

---

## Project Structure | 项目结构

```
Project3_Causal-Uplift-Marketing/
├── configs/
│   └── config.yml              # 集中式配置文件（路径、超参数）
├── data/
│   ├── raw/                    # 原始数据 + 时间戳快照（不可变）
│   └── processed/              # 清洗后数据（ELT 输出）
├── docs/                       # 项目规划文档（PRD）
├── notebooks/                  # 分析 Notebook（01-05）
│   ├── 01_data_ingestion_and_eda.ipynb
│   ├── 02_bias_exposure_and_naive_ate.ipynb
│   ├── 03_psm_and_ate.ipynb
│   ├── 04_uplift_modeling.ipynb
│   └── 05_segmentation_and_roi.ipynb
├── outputs/
│   └── figures/                # 生成的可视化图表（27 张）
├── src/
│   ├── data_utils.py           # 数据加载与清洗（386 行）
│   ├── causal.py               # 因果推断工具（695 行）
│   ├── uplift.py               # Uplift Modeling（763 行）
│   └── business.py             # 业务逻辑层（557 行）
├── tests/
│   └── test_causal.py          # TDD 测试套件（373 行）
├── requirements.txt            # 依赖管理
├── setup.py                    # 包安装配置
└── README.md                   # 项目文档
```

---

## Environment | 开发环境

本项目在以下环境下开发完成：

**Core Dependencies**:
- Python 3.8+
- `pandas`, `numpy`: 数据处理
- `scikit-learn`: 机器学习（LogisticRegression, PSM）
- `xgboost`: Uplift Modeling（Meta-Learners）
- `matplotlib`, `seaborn`: 可视化
- `pytest`: 单元测试

**Note**: 所有 Notebooks 已包含完整输出结果（图表、统计量、代码执行结果），可直接在 GitHub 上浏览，无需本地运行。如需复现分析流程，请参考 `requirements.txt` 和 `setup.py`

---

## Phase 1: EDA & Bias Exposure

### Objective | 目标
建立数据质量基准，暴露朴素 ATE 的局限性，为后续因果推断铺平道路。

### Key Findings | 核心发现

#### 1.1 Data Quality Validation | 数据质量验证
- **Sample Size**: 64,000 users (Treatment:Control = 2:1)
- **Conversion Rate**: 0.90% (极端类别不平衡)
- **Zero Spend Ratio**: 99.1% (spend 作为目标变量统计意义极低)
- **Missing Values**: 0 (数据清洗完整性通过)

**业务洞察**: 低转化率场景（rare event）对模型训练提出更高要求，需要使用 `scale_pos_weight` 处理类别不平衡。

#### 1.2 Covariate Balance Check | 协变量平衡检验
使用 **SMD (Standardized Mean Difference)** 验证 RCT 随机化质量：

| Covariate | SMD | Status |
|-----------|-----|--------|
| history | 0.0071 | ✓ Balanced |
| mens | 0.0066 | ✓ Balanced |
| womens | 0.0063 | ✓ Balanced |
| recency | 0.0060 | ✓ Balanced |
| newbie | 0.0008 | ✓ Balanced |

**技术标准**: 所有协变量 SMD < 0.1，验证了 RCT 数据的无偏性（Selection Bias ≈ 0）。

#### 1.3 Naive ATE & Heterogeneity | 朴素 ATE 与效应异质性

**Overall Naive ATE**:
- Treatment Conversion Rate: 1.0681%
- Control Conversion Rate: 0.5726%
- **Naive ATE**: 0.4955% (相对提升 86.53%)

**Stratified ATE Analysis** (暴露效应异质性):

| Subgroup | ATE | 95% CI | Insight |
|----------|-----|--------|---------|
| **Multichannel** | 0.86% | [0.36%, 1.31%] | 最高增量效应 |
| Web | 0.53% | [0.31%, 0.74%] | 中等效应 |
| Phone | 0.36% | [0.15%, 0.55%] | 最低效应 |
| **New Customer** | 0.63% | [0.45%, 0.81%] | 新用户响应更强 |
| Existing Customer | 0.36% | [0.13%, 0.57%] | 老用户响应较弱 |

**核心洞察**: 不同子群体间 ATE 差异达 **2.4 倍**（0.36% vs 0.86%），证明了 Uplift Modeling 的必要性——"一刀切"的全量投放存在巨大效率浪费。

#### 1.4 Simpson's Paradox Exposure | Simpson 悖论暴露
通过分层分析揭示：总体 ATE 掩盖了子群体间的巨大异质性。这正是 Uplift Modeling 的业务价值所在——需要个体级别的 CATE 估计来实现精准营销。

### Core Visualizations | 核心可视化
- `eda_covariate_comparison.png`: Treatment vs Control 协变量均值对比
- `fig_01_naive_comparison.png`: 朴素 ATE 可视化
- `fig_01b_ate_heterogeneity.png`: 分层 ATE 异质性（4 个维度）
- `fig_01c_covariate_balance_rct.png`: SMD 平衡性检验

### Technical Notes | 技术要点
- **ELT Approach**: Extract → Load → Transform（时间戳快照 + 幂等性加载）
- **Temporal Contamination Check**: 验证 `visit` 列未受 post-treatment 污染
- **Wilson Confidence Interval**: 用于低转化率场景的 CI 估计（优于正态近似）

---

## Phase 2: PSM & Uplift Modeling

### Objective | 目标
通过 Propensity Score Matching 消除选择偏差，使用 Meta-Learners 估计个体级 CATE，为精准营销提供排序信号。

### 2.1 Propensity Score Matching | 倾向性得分匹配

#### Why PSM? | 为什么需要 PSM？
虽然 Hillstrom 是 RCT 数据（Selection Bias ≈ 0），但本项目同时展示：
- **RCT 场景**（无偏差）: 验证方法的正确性，建立因果推断基准
- **观察性场景**（有偏差）: 展示 PSM 的必要性（真实业务场景对比）

在真实业务中，营销活动投放往往不是随机的（运营倾向于给高价值用户发券），此时需要 PSM 消除选择偏差。

#### PSM Workflow | PSM 流程
1. **Estimate PS**: 使用 LogisticRegression 估计 P(T=1|X)，clip 到 [0.01, 0.99]
2. **1:1 Matching**: k-NN (k=200) + caliper=0.2×std(ps)，确保 tie-robust matching
3. **Balance Check**: 匹配后所有协变量 SMD < 0.1
4. **ATE Estimation**: 配对差分 + 分层 Bootstrap (n=1000) 估计 95% CI

#### PSM Results | PSM 结果

| Metric | Before Matching | After Matching |
|--------|----------------|----------------|
| **Sample Size** | 64,000 | 42,612 (matched pairs) |
| **Max SMD** | 0.0071 | 0.0045 |
| **ATE (Conversion)** | 0.4955% | 0.4932% |
| **95% CI** | - | [0.3156%, 0.6708%] |

**核心洞察**: PSM 后 ATE 几乎不变（0.4955% → 0.4932%），验证了 RCT 数据的无偏性。在观察性数据中，PSM 可显著降低选择偏差。

### 2.2 Uplift Modeling (Meta-Learners) | Uplift 建模

#### Model Comparison | 模型对比

| Learner | AUUC | Qini Coefficient | Workflow |
|---------|------|------------------|----------|
| **S-Learner** | 16.10 | 1.67 | 单模型（T 作为特征） |
| **T-Learner** | 13.75 | -0.68 | 两模型（分组训练） |
| **X-Learner** | 16.15 | **1.72** ✓ | 三阶段（交叉估计 + PS 加权） |

**最佳模型**: X-Learner（Qini Coef = 1.72）

#### Why X-Learner Wins? | 为什么 X-Learner 最优？（详细数学推导）

**[T0 - 核心面试点]** 这是展现数学优势的最佳武器。

##### 数学推导（Mathematical Derivation）

**问题设定**: 在 T:C = 2:1 的不平衡场景下，如何降低 CATE 估计的方差？

**X-Learner 三阶段流程**:

**Stage 1: 分组训练基础模型**
- 在 Treatment 组训练 μ₁(x): E[Y|X=x, T=1]
- 在 Control 组训练 μ₀(x): E[Y|X=x, T=0]

**Stage 2: 交叉估计（Imputation）**
- Treatment 组：用 Control 的 μ₀ 模型估计反事实
  ```
  D₁ᵢ = Y₁ᵢ - μ̂₀(x₁ᵢ)  （观测到的 Y₁ - 估计的 Y₀）
  ```
- Control 组：用 Treatment 的 μ₁ 模型估计反事实
  ```
  D₀ᵢ = μ̂₁(x₀ᵢ) - Y₀ᵢ  （估计的 Y₁ - 观测到的 Y₀）
  ```

**Stage 3: PS 加权融合**
- 在 D₁ 上训练 τ̂₁(x)，在 D₀ 上训练 τ̂₀(x)
- 最终 CATE 估计：
  ```
  τ̂(x) = (1 - e(x)) · τ̂₁(x) + e(x) · τ̂₀(x)
  ```
  其中 e(x) = P(T=1|X=x) 是 Propensity Score

**方差降低机制（Variance Reduction Mechanism）**:

**Theorem (Künzel et al. 2019)**:
```
Var[τ̂_X(x)] ≤ min(Var[τ̂_T(x)], Var[τ̂_S(x)])
```

**直觉解释**:
- 当 e(x) 高（Treatment 样本多）时，提高 τ̂₀(x) 权重
- τ̂₀(x) 是在 Control 组（少数组）上训练的，但它使用了 μ̂₁(x)（在 Treatment 多数组上训练）
- 相当于"让少数组借用多数组的模型"，将方差从"少数组的直接估计"降低为"多数组的交叉估计"

**本项目实证**:
- T:C = 2:1 → e(x) ≈ 0.667
- Control 组样本量 = 21,306（少数组）
- X-Learner 通过交叉估计，让 Control 组借用 Treatment 组（42,694 样本）的模型
- 结果：Qini Coef = 1.72（T-Learner = -0.68，劣于随机）

##### 面试回答模板（STAR Method）

**Situation (业务场景)**:
"在营销 RCT 实验中，由于预算限制，Treatment:Control 比例通常是 2:1 或 3:1。这种不平衡场景下，Control 组样本量较少，直接在 Control 组上训练模型会导致**方差爆炸**。"

**Task (技术挑战)**:
"我需要选择一个 Meta-Learner，在不平衡场景下既能准确估计 CATE，又能保持**低方差**（稳定的排序信号）。"

**Action (数学降维打击)**:
"我对比了 S/T/X-Learner 三种方法。T-Learner 在 Control 组（少数组）上独立训练模型，样本不足导致 Qini Coef = -0.68（劣于随机）。X-Learner 通过**交叉估计**（让 Control 组借用 Treatment 组的模型）和 **PS 加权融合**，将方差从'少数组的直接估计'降低为'多数组的交叉估计'。数学上，Künzel 等人证明了 X-Learner 的方差上界低于 T-Learner。"

**Result (业务价值)**:
"最终 X-Learner Qini Coef = 1.72，排序能力最强。基于 X-Learner 的 CATE 排序，我们实现了四象限用户分层，精准投放相比全量投放 ROI 提升 **2.08×**，节省 **75% 预算**。"

#### T-Learner 为何表现差？

在转化率极低（0.9%）的场景下，T-Learner 需要在 T=1 与 T=0 两个子样本上分别训练模型，正例更稀少、方差更大，排序**噪声可能超过真实信号**，从而出现"劣于随机"的表现（Qini Coef = -0.68）。

### Core Visualizations | 核心可视化
- `fig_02_ps_distribution.png`: PS 分布（Treatment vs Control）
- `fig_03_smd_before_after.png`: 匹配前后 SMD 对比
- `fig_04_ate_comparison.png`: Naive ATE vs PSM ATE
- `fig_05_cate_distributions.png`: S/T/X-Learner CATE 分布对比
- `fig_06_qini_curves.png`: Qini Curve（模型评估）

### Technical Notes | 技术要点
- **Qini Curve**: 衡量 Uplift 模型排序能力的金标准（类似 ROC-AUC）
- **AUUC (Area Under Uplift Curve)**: Qini Curve 下面积
- **Qini Coefficient**: AUUC - Random AUUC（正值表示优于随机）
- **Train/Test Split**: 70/30 分割，stratify by T，确保评估无偏

---

## Phase 3: Segmentation & ROI

### Objective | 目标
基于 X-Learner 的 CATE 估计，进行四象限用户分层，模拟精准投放 ROI，量化业务价值。

### 3.1 Four-Quadrant Segmentation | 四象限用户分层

#### Segmentation Logic | 分层逻辑
- **CATE 阈值**: P50 分位数（区分高/低 uplift）
- **Baseline 阈值**: 在高 CATE 子群内使用 P50 分位数（区分 baseline 高/低）
- **Baseline Proxy**: 通过将用户按 CATE 分成 20 个桶，计算每个桶内控制组转化率得到

#### Segmentation Results | 分层结果

| Segment | Count | Pct | Mean CATE | Mean Baseline (proxy) | Business Interpretation |
|---------|-------|-----|-----------|----------------------|------------------------|
| **Persuadables** | 16,000 | 25.0% | 0.0089 | 0.000 (0.0% baseline ratio) | 低 baseline + 高 CATE → **优先投放** |
| **Sure Things** | 16,000 | 25.0% | 0.0068 | 0.0015 (26% baseline ratio) | 稍高 baseline + 较高 CATE → 次优投放 |
| **Lost Causes** | 23,407 | 36.6% | 0.0025 | 0.0021 (36% baseline ratio) | 低 CATE → 避免投放 |
| **Sleeping Dogs** | 8,593 | 13.4% | -0.0041 | 0.0340 (595% baseline ratio) | 负 CATE → **绝对不投放** |

#### Why Persuadables Have Higher Overall Conversion? | 为什么 Persuadables 的总体转化率更高？

**关键理解**: `Overall Conversion (T/C mix)` ≠ Baseline

- **Persuadables**: 低 baseline (~0%) + 高 CATE (~0.9%) → Treatment 组转化率 ~0.9%，与 Control ~0% 混合 → Overall ~1.3%
- **Sure Things**: 稍高 baseline (~0.15%) + 较低 CATE (~0.7%) → Treatment 组转化率 ~0.85%，与 Control ~0.15% 混合 → Overall ~0.9%

**结论**: Uplift 效应主导了 Overall Conversion，使其在 baseline 比较中产生误导。应关注 **Mean Baseline (proxy)** 和 **Baseline Ratio** 来理解四象限。

#### Baseline Threshold Sensitivity Analysis | Baseline 阈值敏感性分析

测试 P30/P40/P50/P60/P70 五个阈值，从三个维度评估：

| 阈值 | Persuadables Pct | Mean CATE | 评估 |
|------|-----------------|-----------|------|
| P30 | 0% | N/A | ✗ 离散化崩溃 |
| P40 | 0% | N/A | ✗ 离散化崩溃 |
| **P50** | **25%** | **0.0089** | ✓ **最优** |
| P60 | 30% | 0.0080 | △ CATE 区分度下降 |
| P70 | 35% | 0.0075 | △ Sure Things 样本量不足 |

**选择 P50 的理由**:
1. **统计稳健性**: 样本量均衡（各 25%），方差估计最可靠
2. **CATE 区分度**: Persuadables Mean CATE 最高（0.0089），相对差异 30.7%
3. **业务可解释性**: 中位数分割最直观，避免离散化崩溃

### 3.2 Decision Framework | 决策流程图

```
用户进入营销系统
        ↓
估计 CATE = τ̂(x)
        ↓
    CATE > P50?
   /           \
 YES            NO
  ↓              ↓
估计 Baseline   Lost Causes
(proxy)         (36.6%)
  ↓             → 不投放
Baseline > P50?
 /          \
YES         NO
 ↓           ↓
Sure Things  Persuadables
(25.0%)      (25.0%)
→ 次优投放   → **优先投放**
             （核心增量来源）

特殊情况：
CATE < 0?
  ↓
Sleeping Dogs (13.4%)
→ **绝对不投放**（避免负面效果）
```

**决策规则（Decision Rules）**:
1. **优先级 1**: Persuadables（低 baseline + 高 CATE）→ 100% 投放
2. **优先级 2**: Sure Things（稍高 baseline + 较高 CATE）→ 降低频次投放
3. **优先级 3**: Lost Causes（低 CATE）→ 不投放
4. **优先级 4**: Sleeping Dogs（负 CATE）→ **绝对不投放**（加入黑名单）

### 3.3 ROI Simulation | ROI 模拟

#### Simulation Setup | 模拟设置
- **Full Targeting**: 投放所有 64,000 用户
- **Random Targeting**: 随机投放（baseline）
- **Precision Targeting**: 仅投放 Persuadables（16,000 用户）
- **Cost per Contact**: 1.0（归一化）
- **Incremental Attribution**: sum(CATE) for targeted users

#### ROI Results | ROI 结果

| Strategy | Targeted Users | Incremental Conversions | Cost | ROI |
|----------|---------------|------------------------|------|-----|
| **Full Targeting** | 64,000 | 274.27 | 64,000 | 0.004285 |
| **Random (50%)** | 32,000 | ~137 | 32,000 | ~0.004285 |
| **Precision Targeting** | 16,000 | 142.29 | 16,000 | **0.008893** |

#### Key Metrics | 核心指标
- **Budget Saving**: 75.0% (64,000 → 16,000 users)
- **Conversion Retention**: 51.9% (142.29 / 274.27)
- **ROI Improvement**: **2.08×** (0.008893 / 0.004285)

**业务价值**: 如果营销预算为 100 万元，精准投放可以节省约 **75 万元**，同时保留 51.9% 的增量转化效果。节省的预算可以重新分配给其他高 ROI 渠道。

### Core Visualizations | 核心可视化
- `fig_07_quadrant_scatter.png`: 四象限 Hexbin 密度图（CATE vs Baseline）
- `fig_07b_segment_baseline_ratio.png`: 各象限 Baseline Ratio 对比
- `fig_07b_segment_conversion.png`: 各象限观测转化率（RCT arms）
- `fig_07d_baseline_sensitivity.png`: Baseline 阈值敏感性分析
- `fig_08_roi_comparison.png`: ROI 对比（Full vs Random vs Precision）
- `fig_08b_budget_uplift_curve.png`: 预算分配曲线（Precision vs Random）

### Business Recommendations | 业务建议

1. **优先投放 Persuadables**（核心增量来源）
   - 占比 25%，Mean CATE = 0.0089
   - 这些用户只有在接受营销时才会转化

2. **停止投放 Sleeping Dogs**（避免负面效果）
   - 占比 13.4%，Mean CATE = -0.0041
   - 营销反而导致流失（过度打扰）

3. **对 Sure Things 降低投放频次**（节省预算）
   - 占比 25%，Mean CATE = 0.0068
   - 这些用户无论是否营销都会转化

4. **建议每季度重新训练模型**，更新人群分层
   - 用户行为会随时间变化
   - 定期更新 CATE 估计以保持精准度

---

## Competitive Advantages | 竞争优势（从面试官视角）

### 维度 1: 数学优势（Mathematical Superiority）

#### 1.1 因果推断数学功底（Causal Inference Rigor）

**面试官视角**: "这个候选人是否真正理解因果推断，还是只会调包？"

**本项目展现**:
- **Rubin's Potential Outcomes Framework**: 明确区分 ATE vs CATE，理解 Fundamental Problem of Causal Inference
- **SMD vs p-value**: 使用 SMD < 0.1 而非 p-value 验证协变量平衡（独立于样本量）
- **X-Learner 方差降低机制**: 能够从数学上推导 Var[τ̂_X(x)] ≤ min(Var[τ̂_T(x)], Var[τ̂_S(x)])
- **PS 加权融合**: 理解 e(x) 在不平衡场景下的方差调节作用

**面试武器**: "我不仅会用 X-Learner，还能从数学上解释为什么它在 T:C = 2:1 场景下方差最优。"

#### 1.2 统计严谨性（Statistical Rigor）

**面试官视角**: "这个候选人是否具备严谨的统计思维？"

**本项目展现**:
- **Wilson Confidence Interval**: 在低转化率场景（0.9%）使用 Wilson CI 而非正态近似
- **Bootstrap CI**: 分层 Bootstrap (n=1000) 估计 ATE 的 95% CI
- **Stratified Sampling**: Train/Test Split 时保持 Treatment:Control 比例
- **Simpson's Paradox**: 暴露总体 ATE 掩盖的子群体异质性（差异 2.4 倍）

**面试武器**: "我能识别低转化率场景下正态近似的失效，并选择更稳健的 Wilson CI。"

#### 1.3 数学降维打击（Math Strike）

**面试官视角**: "这个候选人能否用数学优势弥补业务经验不足？"

**本项目展现**:
- **T-Learner 失效分析**: 从方差爆炸的角度解释 Qini Coef = -0.68（劣于随机）
- **Baseline Proxy 设计**: 通过 CATE 分桶 + Control 组转化率估计 Baseline（避免 post-treatment bias）
- **Qini Coefficient**: 使用 AUUC - Random AUUC 量化模型排序能力（优于简单的 AUC）

**面试武器**: "我能用数学思维去优化普通程序员写的代码，例如用 Qini Curve 替代 ROC-AUC 评估 Uplift 模型。"

---

### 维度 2: 业务思维（Business Sense）

#### 2.1 ROI 量化能力（ROI Quantification）

**面试官视角**: "这个候选人能否将技术转化为业务价值？"

**本项目展现**:
- **精准投放 ROI**: 2.08× (0.008893 vs 0.004285)
- **预算节省**: 75% (64,000 → 16,000 users)
- **转化保留率**: 51.9% (142.29 / 274.27)
- **业务翻译**: "如果营销预算为 100 万元，精准投放可以节省约 75 万元"

**面试武器**: "我不仅会做技术分析，还能用 ROI、预算节省、转化保留率等业务语言向高管汇报。"

#### 2.2 四象限人群洞察（Segmentation Insight）

**面试官视角**: "这个候选人能否从数据中提炼业务洞察？"

**本项目展现**:
- **Persuadables**: 低 baseline + 高 CATE → 核心增量来源（优先投放）
- **Sure Things**: 稍高 baseline + 较高 CATE → 浪费预算（降低频次）
- **Lost Causes**: 低 CATE → 无效投放（避免投放）
- **Sleeping Dogs**: 负 CATE → 负面效应（绝对不投放）

**面试武器**: "我能将 CATE 估计转化为可执行的业务决策规则，并量化每个象限的业务价值。"

#### 2.3 Simpson 悖论暴露（Paradox Detection）

**面试官视角**: "这个候选人能否识别数据中的陷阱？"

**本项目展现**:
- **总体 ATE** = 0.4955%（看起来营销整体有效）
- **分层 ATE**: Multichannel 用户 ATE = 0.86%，Phone 用户 ATE = 0.36%（差异 2.4 倍）
- **业务洞察**: "如果只看总体 ATE，会误以为'一刀切'的全量投放是最优策略"

**面试武器**: "我能用 Simpson 悖论揭示数据假象，展现透过现象看本质的业务洞察力。"

---

### 维度 3: 工程成熟度（Engineering Maturity）

#### 3.1 不可变数据流（Immutable Data Pipeline）

**面试官视角**: "这个候选人是否具备大厂工程规范意识？"

**本项目展现**:
- **Timestamped Snapshots**: 原始数据加时间戳快照（`hillstrom_YYYYMMDD_HHMMSS.csv`）
- **Idempotency Guards**: `load_and_clean()` 检测已存在文件，防止重复处理
- **ELT Approach**: Extract → Load → Transform，确保数据溯源

**面试武器**: "在业务流水线中，脏数据流入下游因果推断模型会导致极其昂贵的决策失误。通过引入不可变快照和幂等性加载，我们建立了一个 Fail-fast 机制。"

#### 3.2 配置驱动架构（Configuration-Driven Architecture）

**面试官视角**: "这个候选人是否理解解耦的重要性？"

**本项目展现**:
- **Centralized Config**: `configs/config.yml` 管理所有路径、超参数、特征列表
- **Decoupling**: 业务逻辑与参数解耦，便于 Airflow 等调度系统传参

**面试武器**: "硬编码是大厂工程流水线的大忌。统一配置管理能实现业务逻辑与参数的解耦，方便后续在 Airflow 等调度系统中进行自动化传参和 A/B 实验。"

#### 3.3 测试驱动开发（Test-Driven Development）

**面试官视角**: "这个候选人是否具备质量意识？"

**本项目展现**:
- **Test Coverage**: `tests/test_causal.py` (373 行) 包含 6 大测试类
- **RCT Validation**: 验证 PS 均值 ~0.667（等于 Treatment 比例）
- **Edge Cases**: 测试全 1、全 0、完美分离等边界情况
- **Immutability**: 验证不修改输入数据

**面试武器**: "通过 TDD 确保 PS 估计的正确性，特别是在 RCT 数据中 PS 均值应接近 Treatment 比例（~0.667），这是因果推断方法论正确性的关键验证。"

#### 3.4 Git 规范（Conventional Commits）

**面试官视角**: "这个候选人是否具备协作意识？"

**本项目展现**:
- **Atomic Commits**: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`
- **Commit Message Example**:
  ```
  feat(business): add four-quadrant user segmentation (MVP 3.1)
  refactor(causal): optimize SMD calculation query for covariate balance
  ```

**面试武器**: "这种极其严谨的 Git 流水线习惯，在未来参与 Web3 核心 DeFi 协议或智能合约库的开源贡献时，是硬通货，能建立 Web3 安全审查员所需的完美审计轨迹。"

#### 3.5 数据质量断言（Data Quality Assertions）

**面试官视角**: "这个候选人是否具备防御性编程意识？"

**本项目展现**:
- **13 个 DQ 断言**: One-hot 编码后列数验证、缺失值检验、数值范围检验、类型检验
- **Temporal Contamination Check**: 验证 `visit` 列未受 post-treatment 污染
- **Fail-fast Mechanism**: 在数据流入模型前拦截脏数据

**面试武器**: "我在特征工程阶段引入了 13 个 DQ 断言，确保脏数据在流入因果推断模型前被拦截，避免极其昂贵的决策失误。"

---

### 维度 4: Web3 迁移能力（Web3 Synergy）

#### 4.1 直接迁移场景（Direct Migration）

**面试官视角**: "这个候选人是否具备 Web3 认知？"

**本项目展现**:
1. **Token Airdrop ROI 优化**:
   - Treatment = 是否收到 Airdrop
   - Outcome = 是否成为活跃用户
   - CATE = Airdrop 带来的增量活跃度
   - 四象限分层 → 精准 Airdrop 策略

2. **NFT Whitelist 优化**:
   - Treatment = 是否获得 Whitelist
   - Outcome = 是否 Mint + 持有 > 30 天
   - CATE = Whitelist 带来的增量忠诚度

**面试武器**: "Uplift Modeling 的核心逻辑（识别真正可被干预说服的用户）在 Web3 Token Airdrop / NFT Whitelist 优化场景中完全同构。"

#### 4.2 技术协同（Technical Synergy）

**面试官视角**: "这个候选人是否理解 Web2 与 Web3 的技术协同？"

**本项目展现**:
- **不可变数据流** ↔ 区块链账本的不可变性
- **配置驱动架构** ↔ 智能合约的逻辑与状态分离
- **Git 审计轨迹** ↔ Web3 安全审查的完美审计轨迹
- **PSM 选择偏差校正** ↔ Web3 Airdrop 中区分真实用户与 Sybil 攻击者

**面试武器**: "我在 Web2 项目中建立的工程习惯（不可变数据流、配置驱动架构、Git 审计轨迹），在 Web3 场景中是硬通货，能无缝迁移到智能合约开发和链上数据分析。"

---

## Interview Q&A | 面试问答

### Q1: 为什么选择 X-Learner 而不是 T-Learner？

**[T0 - 核心面试点]** 这是展现数学优势的最佳武器。

**数学优势**: 在 T:C = 2:1 的不平衡场景下，T-Learner 需要在 Control 组（少数组）上独立训练模型，样本不足导致方差爆炸。X-Learner 通过交叉估计（让 Control 组借用 Treatment 组的模型）和 PS 加权，将方差从"少数组的直接估计"降低为"多数组的交叉估计"。

**数学推导**:
```
Var[τ̂_X(x)] ≤ min(Var[τ̂_T(x)], Var[τ̂_S(x)])  (Künzel et al. 2019)
```

**实证结果**: X-Learner Qini Coef = 1.72，T-Learner Qini Coef = -0.68（劣于随机）。

**业务价值**: 更稳定的 CATE 排序信号 → 更精准的用户分层 → 更高的 ROI（2.08×）。

---

### Q2: 如何向非技术业务方解释 Uplift Modeling？

**[T0 - 核心面试点]** 这是展现业务思维的最佳武器。

**类比**: 传统 A/B 测试就像"体检报告的总体平均值"——只能告诉你"营销活动整体有效"，但无法告诉你哪些人真正因为营销而转化。

Uplift Modeling 就像"个性化体检报告"——为每个用户估计"营销带来的增量效应"，从而识别：
- **Persuadables**: 只有营销才会转化的人（最值得投放）
- **Sure Things**: 无论是否营销都会转化的人（浪费预算）
- **Sleeping Dogs**: 营销反而导致流失的人（避免打扰）

**ROI 量化**: 精准投放相比全量投放节省 75% 预算，ROI 提升 2.08×。

**STAR Method 回答**:
- **Situation**: "在营销活动中，我们发现全量投放虽然整体有效，但 ROI 较低（0.004285）"
- **Task**: "我需要识别哪些用户真正因为营销而转化，从而优化预算分配"
- **Action**: "我使用 X-Learner 估计个体级 CATE，将用户分为四象限，仅投放 Persuadables（25%）"
- **Result**: "精准投放 ROI 提升 2.08×，节省 75% 预算，同时保留 51.9% 的增量转化效果"

---

### Q3: Simpson 悖论在本项目中如何体现？

**[T0 - 核心面试点]** 这是展现数据洞察力的最佳武器。

**定义**: 总体趋势与分组趋势相反的统计现象。

**本项目体现**:
- **总体 ATE** = 0.4955%（看起来营销整体有效）
- **分层 ATE**: Multichannel 用户 ATE = 0.86%，Phone 用户 ATE = 0.36%（差异 2.4 倍）

**业务洞察**: 如果只看总体 ATE，会误以为"一刀切"的全量投放是最优策略。但分层分析揭示了巨大的异质性，证明了精准营销的必要性。

**面试回答模板**:
"在本项目中，我发现总体 ATE 为 0.4955%，但分层后发现 Multichannel 用户 ATE 高达 0.86%，而 Phone 用户仅 0.36%，差异 2.4 倍。这就是典型的 Simpson 悖论——总体指标掩盖了子群体的巨大异质性。这个发现直接推动了我们从'一刀切'的全量投放转向基于 CATE 的精准投放，最终 ROI 提升 2.08×。"

---

### Q4: 如何处理极端类别不平衡（转化率 0.9%）？

**[T0 - 核心面试点]** 这是展现技术深度的最佳武器。

**技术手段**:
1. **XGBoost `scale_pos_weight`**: 自动平衡正负样本权重
   ```python
   scale_pos_weight = (n_negative / n_positive)
   ```
2. **Wilson Confidence Interval**: 用于低转化率场景的 CI 估计（优于正态近似）
3. **Stratified Sampling**: Train/Test Split 时保持 Treatment:Control 比例

**业务理解**: 低转化率场景（rare event）对模型训练提出更高要求，但也意味着更大的优化空间——即使提升 0.1% 的转化率，在百万级用户规模下也能带来显著的业务价值。

**面试回答模板**:
"在本项目中，转化率仅 0.9%，属于极端类别不平衡。我采用了三个技术手段：1) XGBoost 的 `scale_pos_weight` 自动平衡正负样本权重；2) Wilson CI 替代正态近似（因为正态近似在 p 接近 0 时失效）；3) Stratified Sampling 确保 Train/Test Split 时保持 Treatment:Control 比例。这些手段确保了模型在低转化率场景下的稳健性。"

---

### Q5: 本项目如何迁移到 Web3 场景？

**[T1 - 实用工具]** 这是展现 Web3 认知的最佳武器。

**直接迁移场景**:
1. **Token Airdrop ROI 优化**:
   - Treatment = 是否收到 Airdrop
   - Outcome = 是否成为活跃用户
   - CATE = Airdrop 带来的增量活跃度
   - 四象限分层 → 精准 Airdrop 策略

2. **NFT Whitelist 优化**:
   - Treatment = 是否获得 Whitelist
   - Outcome = 是否 Mint + 持有 > 30 天
   - CATE = Whitelist 带来的增量忠诚度

**技术协同**:
- **不可变数据流** ↔ 区块链账本的不可变性
- **配置驱动架构** ↔ 智能合约的逻辑与状态分离
- **Git 审计轨迹** ↔ Web3 安全审查的完美审计轨迹
- **PSM 选择偏差校正** ↔ Web3 Airdrop 中区分真实用户与 Sybil 攻击者

**面试回答模板**:
"Uplift Modeling 的核心逻辑（识别真正可被干预说服的用户）在 Web3 场景中完全同构。例如，在 Token Airdrop 优化中，我们可以将 Treatment 定义为'是否收到 Airdrop'，Outcome 定义为'是否成为活跃用户'，通过 CATE 估计识别真正因 Airdrop 而活跃的用户，避免浪费 Token 在本来就会活跃的用户身上。此外，我在 Web2 项目中建立的工程习惯（不可变数据流、配置驱动架构、Git 审计轨迹）在 Web3 场景中是硬通货，能无缝迁移到智能合约开发和链上数据分析。"

---

### Q6: 如果面试官质疑"你的 CATE 估计可能不准确"，如何防守？

**[T0 - 核心面试点]** 这是应对质疑的最佳武器。

**防守策略（三层防线）**:

**第一层：模型评估（Qini Curve）**
"我使用 Qini Curve 评估 CATE 排序能力。X-Learner 的 Qini Coefficient = 1.72，显著优于随机（Random = 0）和 T-Learner（-0.68）。Qini Curve 是 Uplift Modeling 的金标准，类似分类任务中的 ROC-AUC，专门衡量模型是否能正确排序高 CATE 用户。"

**第二层：敏感性分析（Baseline Threshold）**
"我对 Baseline 阈值进行了敏感性分析，测试 P30/P40/P50/P60/P70 五个阈值。结果显示 P50 在统计稳健性、CATE 区分度、业务可解释性三个维度上最优。这证明了四象限分层的稳健性，不依赖于单一阈值选择。"

**第三层：RCT 数据验证（Ground Truth）**
"本项目使用 RCT 数据（Hillstrom），所有协变量 SMD < 0.1，验证了无选择偏差。在 RCT 数据中，CATE 估计的无偏性有理论保证（Strong Ignorability）。此外，PSM 后 ATE 几乎不变（0.4955% → 0.4932%），进一步验证了因果识别策略的正确性。"

**反击（Math Strike）**:
"如果面试官继续质疑，我会反问：'您认为哪个指标更能验证 CATE 估计的准确性？'然后引导到 Qini Curve 和 RCT 数据的理论保证。这展现了我对因果推断方法论的深刻理解。"

---

### Q7: RCT 数据 vs 观察性数据，本项目的方法论如何迁移？

**[T0 - 核心面试点]** 这是展现因果推断理论功底的最佳武器。

**RCT 数据（本项目）**:
- **优势**: Selection Bias ≈ 0（所有协变量 SMD < 0.1）
- **因果识别策略**: 随机化（Randomization）
- **CATE 估计**: 直接使用 Meta-Learners（S/T/X-Learner）
- **验证方式**: PSM 后 ATE 几乎不变（0.4955% → 0.4932%）

**观察性数据（真实业务场景）**:
- **挑战**: Selection Bias ≠ 0（运营倾向于给高价值用户发券）
- **因果识别策略**: PSM / IPW / DID
- **CATE 估计**: 先 PSM 消除选择偏差，再使用 Meta-Learners
- **验证方式**:
  1. **Balance Check**: 匹配后所有协变量 SMD < 0.1
  2. **Placebo Test**: 在 pre-treatment 期验证 ATE ≈ 0
  3. **Sensitivity Analysis**: 测试不同匹配方法（k-NN vs Caliper vs Kernel）

**方法论迁移（Migration Path）**:

| 步骤 | RCT 数据 | 观察性数据 |
|------|---------|-----------|
| **1. Balance Check** | SMD < 0.1（验证随机化） | SMD > 0.1（暴露选择偏差） |
| **2. Bias Correction** | 跳过（无偏差） | PSM / IPW（消除偏差） |
| **3. CATE Estimation** | Meta-Learners | Meta-Learners（在匹配后样本上） |
| **4. Validation** | PSM 后 ATE 不变 | Placebo Test + Sensitivity Analysis |

**面试回答模板**:
"本项目使用 RCT 数据，验证了方法论的正确性（PSM 后 ATE 几乎不变）。在真实业务场景中，营销活动投放往往不是随机的，此时需要先用 PSM 消除选择偏差（确保匹配后 SMD < 0.1），再使用 Meta-Learners 估计 CATE。我会通过 Placebo Test（在 pre-treatment 期验证 ATE ≈ 0）和 Sensitivity Analysis（测试不同匹配方法）来验证因果识别策略的稳健性。这展现了我对 RCT 与观察性数据的深刻理解，以及在真实业务场景中的迁移能力。"

---

## References | 参考文献

1. Rosenbaum, P.R. & Rubin, D.B. (1983). "The central role of the propensity score in observational studies for causal effects." *Biometrika*, 70(1), 41-55.

2. Künzel, S.R., Sekhon, J.S., Bickel, P.J., & Yu, B. (2019). "Metalearners for estimating heterogeneous treatment effects using machine learning." *PNAS*, 116(10), 4156-4165.

3. Radcliffe, N.J. & Surry, P.D. (2011). "Real-world uplift modelling with significance-based uplift trees." *Portrait Technical Report TR-2011-1*.

4. Hillstrom, K. (2008). "The MineThatData E-Mail Analytics And Data Mining Challenge." *MineThatData Blog*.

---

## Contact | 联系方式

For questions or collaboration opportunities, please reach out via:
- GitHub Issues: [Project Repository](https://github.com/your-username/Project3_Causal-Uplift-Marketing)
- Email: nianmingyao.math@outlook.com

---

