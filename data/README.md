# Data

Local-only data layout for this project.
本仓库不提交 Hillstrom 原始数据文件；`data/` 目录用于本地复现与产物落盘（默认被 gitignore）。

## What is tracked

- `data/raw/`: input CSV + optional timestamped snapshots
- `data/processed/`: deterministic pipeline artifacts (cleaned data, features, matching panels, CATE/Qini results)

说明：`data/raw/` 与 `data/processed/` 默认不会提交到 Git（见 `.gitignore`），目的是避免数据版权/体积问题，同时保持代码仓库轻量。

## Expected Layout

```text
data/
  raw/
    hillstrom.csv
  processed/
    (generated outputs)
```

- `data/raw/hillstrom.csv`
  - Hillstrom Email Marketing dataset (CSV)
  - 你需要手动放置该文件；仓库只提供代码与分析流程，不提供原始数据

## Processed Artifacts

Common files generated after running the notebooks.
下列文件是运行 notebooks 后会常见出现的落盘产物（用于复现、审计与下游复用）。

- `data/raw/hillstrom_raw_text_年月日_具体时间.csv`
  - Raw dataset (data_utils.py)
  - 未经过清晰, 直接全部以 TEXT 类型入库的原始数据, 用于后续数据溯源
- `data/processed/hillstrom_cleaned.csv`
  - Cleaned dataset (Notebook 01)
  - 清洗后的“事实表”，用于统一后续所有分析阶段输入
- `data/processed/hillstrom_features.csv`
  - Feature matrix (Notebook 01/02)
  - 特征工程后的建模输入（含 one-hot/multi-hot 等编码结果）
- `data/processed/hillstrom_matched.csv`
  - 1:1 PSM matched pairs (Notebook 03 via `src.causal.match_ps`)
  - 倾向性得分匹配后的配对样本，用于在“overlap 子样本”上估计 ATE 并做诊断
- `data/processed/psm_match_panel.json`
  - Match-rate monitoring panel (Notebook 03 diagnostics)
  - 含 coverage 指标（如 `match_rate_max`, `treated_utilization`）与配对完整性标记
  - 业务解释：coverage 低意味着 common support 有限，此时估计目标会被限制在匹配/重叠子样本（trimmed estimand）
- `data/processed/cate_vectors.npz`
  - Saved CATE vectors for meta-learners (Notebook 04)
  - 便于快速复现实验（无需重复训练即可重画分布/做 ROI 模拟）
- `data/processed/qini_results.json`
  - AUUC/Qini evaluation results (Notebook 04)
  - uplift 排序指标的结果快照，便于回归对比（防止排序方向/分箱边界回归）
- `data/processed/placebo_results.json`
  - Placebo / permutation test results (Notebook 06)
  - 置换 T 后如果效果仍显著，说明存在实现错误/数据泄漏/评估偏差等高风险问题

## How To Run

Run from repo root.
请在仓库根目录运行。

1) Put the dataset at `data/raw/hillstrom.csv`.
2) Run notebooks in order under `notebooks/` (01 -> 05).
3) Optional: run `notebooks/06_robustness_checks.ipynb` to generate `data/processed/placebo_results.json`.

Minimal acceptance gate:
最小验收门禁是 `notebooks/Phase1_DoD.ipynb`（用于端到端回归检查与产物完整性确认）。

## Notes

- Git ignore: `data/raw/` and `data/processed/` are gitignored by design (see `.gitignore`).
- Auditability: the pipeline may create timestamped raw snapshots under `data/raw/`.
  - 说明：时间戳快照用于审计与复现（同一份分析结果能追溯到具体哪次 raw 输入）。
