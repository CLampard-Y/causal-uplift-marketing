# ==========================================
# Business layer utilities
# ==========================================
from __future__ import annotations

from typing import Literal, Sequence

import numpy as np
import pandas as pd


_SEGMENTS = {"Persuadables", "Sure Things", "Lost Causes", "Sleeping Dogs"}


def segment_users(
    cate: np.ndarray,
    Y: pd.Series,
    T: pd.Series,
    method: Literal["quantile", "threshold"] = "quantile",
    cate_threshold_pct: float = 50.0,
    baseline_threshold: float = 0.5,
    n_baseline_bins: int = 20,
) -> pd.DataFrame:
    """
    Segment users into four business quadrants using a CATE vector.
    Parameters
    ----------
    cate : np.ndarray
        CATE vector, shape (n,)
        Expected magnitude: roughly within [-0.02, 0.02] on Hillstrom RCT.
    Y : pd.Series
        outcome (conversion, 0/1)
    T : pd.Series
        treatment indicator (0/1)
    method : Literal["quantile", "threshold"]
        CATE estimation method
        quantile: use quantile binning
        threshold: use absolute threshold
    cate_threshold_pct : float
        CATE threshold for "high CATE"
        default=50.0
    baseline_threshold : float
        Percentile cutoff within the high-CATE subgroup to define "high baseline".
        With default=0.5, users whose baseline_prob >= P50 of the high-CATE group
        are classified as Sure Things (top 50% baseline within high-CATE users).
    n_baseline_bins : int
        Number of CATE-quantile bins for computing baseline_prob.
        Default=20 balances statistical robustness (each bin ~3200 users in Hillstrom)
        and discretization granularity. For small samples (<10K), consider reducing
        to max(10, n // 1000).
    Returns
    -------
    segments_df : pd.DataFrame
        shape: (~64K, 3+)
        columns:
        - cate: float — original CATE value
        - baseline_prob: float — control conversion rate among users in the same CATE-quantile bin
        - segment: str — segment label {"Persuadables", "Sure Things", "Lost Causes", "Sleeping Dogs"}
        - optional _warning: str — warning if segmentation is not "good"
    """
    try:
        # ------------------------------------------
        # 1) Input Validation & Type Conversion
        # ------------------------------------------
        # .reshape: dimension defense
        cate_arr = np.asarray(cate, dtype=float).reshape(-1)
        if cate_arr.ndim != 1 or cate_arr.size == 0:
            raise ValueError("cate must be a non-empty 1D array")
        if not np.isfinite(cate_arr).all():
            raise ValueError("CATE contains NaN/inf values")

        t_series = T if isinstance(T, pd.Series) else pd.Series(T)
        y_series = Y if isinstance(Y, pd.Series) else pd.Series(Y)

        if pd.api.types.is_bool_dtype(t_series):
            t_series = t_series.astype(int)
        if pd.api.types.is_bool_dtype(y_series):
            y_series = y_series.astype(int)

        t = pd.to_numeric(t_series, errors="coerce").astype(float)
        y = pd.to_numeric(y_series, errors="coerce").astype(float)

        if t.isnull().any():
            raise ValueError("T contains NaN/non-numeric values")
        if y.isnull().any():
            raise ValueError("Y contains NaN/non-numeric values")

        t = t.astype(int)
        y = y.astype(int)

        if len(t) != len(cate_arr) or len(y) != len(cate_arr):
            raise ValueError("Length mismatch among cate, Y, T")
        if not set(pd.unique(t)).issubset({0, 1}):
            raise ValueError("T must be binary (0/1)")
        if not set(pd.unique(y)).issubset({0, 1}):
            raise ValueError("Y must be binary (0/1)")

        if method not in {"quantile", "threshold"}:
            raise ValueError("method must be 'quantile' or 'threshold'")
        if not (0.0 < float(cate_threshold_pct) <= 100.0):
            raise ValueError("cate_threshold_pct must be in (0, 100]")
        if not (float(baseline_threshold) > 0.0):
            raise ValueError("baseline_threshold must be > 0")
        if not (2 <= int(n_baseline_bins) <= 100):
            raise ValueError("n_baseline_bins must be in [2, 100]")

        n = int(len(cate_arr))
        n_control = int((t == 0).sum())
        n_treated = int(n - n_control)
        if n_control <= 0 or n_treated <= 0:
            raise ValueError("Both control and treated groups must be non-empty")

        # ------------------------------------------
        # 2) Compute Overall Control Conversion Rate
        # ------------------------------------------
        control_conversion_rate = float(y[t == 0].mean())

        # ------------------------------------------
        # 3) Compute CATE Threshold
        # ------------------------------------------
        if method == "quantile":
            cate_threshold = float(np.percentile(cate_arr, 100.0 - float(cate_threshold_pct)))
        else:
            cate_threshold = 0.0

        # ------------------------------------------
        # 4) Compute Baseline Probability
        # ------------------------------------------
        # Assign each row to a CATE-quantile bin (0..n_bins-1)
        # Handle duplicates robustly via rank-based qcut
        cate_rank = pd.Series(cate_arr).rank(method="first")
        try:
            cate_bin = pd.qcut(cate_rank, q=n_baseline_bins, labels=False, duplicates="drop").astype(int)
        except Exception:
            # Fallback: if qcut fails (pathological constant CATE), put everyone in one bin.
            cate_bin = pd.Series(np.zeros(n, dtype=int))

        # Compute control conversion rate per bin, then map to all users in that bin.
        tmp = pd.DataFrame({"bin": cate_bin.to_numpy(), "t": t.to_numpy(), "y": y.to_numpy()})
        ctrl_rates = (
            tmp[tmp["t"] == 0]                      # control user
            .groupby("bin", observed=True)["y"]     # `observed=True` to avoid compute empty/NaN bins
            .mean()                                 # bin-level baseline probability
            .astype(float)
            .to_dict()
        )

        # Search control conversion rate for this user in the bin.
        # (Empirical Bayes)If bin not exist, fallback to the global control conversion rate.
        # The choice about control conversion rate baseline:
        #   1. ideal method (individual-level baseline): Compute individual-level control conversion rate by trained model.
        #   2. Why not individual-level baseline:
        #      - Modular design: Parameters not include X (covariates), add model & covariates will make function more complex.
        #      - CATE already includes coveraiate-related information
        #      - Computational Efficiency: avoid use model.predict_proba() to reduce computational cost.
        baseline_prob = np.array([ctrl_rates.get(int(b), control_conversion_rate) for b in tmp["bin"]], dtype=float)
        baseline_prob = np.clip(baseline_prob, 0.0, 1.0)
        assert np.isfinite(baseline_prob).all(), "baseline_prob contains NaN/inf"

        # -----------------------------------------
        # 5) Quadrant Assignment.
        # -----------------------------------------
        cate_high = cate_arr >= cate_threshold

        """ 
        NOTICE: THIS IS THE OLD STRATEGY A

        ISSUE:
            1. Categorized users into "Persuadables" once CATE cate >= cate_threshold, neglect baseline_prob
            2. Contribute to "Sure Things" sample is low (even 0 in this dataset)

        Applicable Scenarios:
            Increase conversion rates is the only one goal, neglect treatment cost
            (Even if the user would have converted it themselves)

        This is not what we want: 
            1. Limited budge, require precise treatment
            2. Uplift Modeling core objective: maximize treatment ROI

        
        # Business-aligned interpretation:
        # - Sleeping Dogs: cate < 0 (negative treatment effect)
        # - Persuadables: cate >= cate_threshold (high uplift)
        # - Sure Things: cate >= 0 but not high uplift, and baseline is high
        # - Lost Causes: cate >= 0 but not high uplift, and baseline is low
    
        segments = np.empty(n, dtype=object)
        segments[:] = "Lost Causes"
        segments[cate_arr < 0.0] = "Sleeping Dogs"
        segments[(cate_arr >= 0.0) & cate_high] = "Persuadables"
        segments[(cate_arr >= 0.0) & (~cate_high) & baseline_high] = "Sure Things"
        segments[(cate_arr >= 0.0) & (~cate_high) & (~baseline_high)] = "Lost Causes"
        """

        """
        NOTICE: THIS IS THE OLD STRATEGY B

        ISSUE: wrong setting of baseline_high
            1. In this dataset, the baseline_prob of user whose cate > cate_threshold is far lower than control_conversion_rate
            2. Contributes to "Sure Things" sample is still 0


        # Business-aligned interpretation: 
        # - Sleeping Dogs:  CATE < 0  (marketing hurts conversion)
        # - Persuadables:   CATE >= threshold AND baseline low  (true marginal users)
        # - Sure Things:    CATE >= threshold AND baseline high (would convert anyway)
        # - Lost Causes:    CATE in [0, threshold)             (low uplift)

         baseline_high = baseline_prob >= baseline_pct
        
        """

        # 基于本数据集基线高低阈值: 在高 CATE 子群内部使用百分位数分割
        # 为什么用百分位而非绝对倍数阈值：
        #   baseline_prob 是按 CATE 分位数分桶后计算的控制组转化率。
        #   高 CATE 分桶本身就意味着"处理效应大"，这恰恰说明该桶的控制组转化率低
        #   （正是因为基线低，处理后提升才大，CATE 才高）。
        #   因此，在高 CATE 子群内部使用绝对阈值（如之前旧策略 A,B 中使用的 1.5 倍全局控制组转化率）
        #   永远无法触达，导致 Sure Things 为空。
        #   使用子群内百分位数能自适应该子群的条件分布，产生有意义的 Sure Things 分割。
        #
        # baseline_threshold 参数语义（默认 0.5）：
        #   在高 CATE 用户中，定义 baseline_prob 排名前 (1 - baseline_threshold) 的用户为 Sure Things
        #   0.5 → 高 CATE 子群内 baseline_prob 排名前 50% = Sure Things
        #   0.3 → 高 CATE 子群内 baseline_prob 排名前 70% = Sure Things（更宽松）
        #   0.7 → 高 CATE 子群内 baseline_prob 排名前 30% = Sure Things（更严格）

        high_cate_baseline = baseline_prob[cate_high & (cate_arr >= 0.0)]
        if len(high_cate_baseline) > 0:
            baseline_pct = float(np.percentile(
                high_cate_baseline,
                float(baseline_threshold) * 100.0,
            ))
        else:
            # Edge case: 当高 CATE 子群为空时（极端负向实验），强制所有用户为 Lost Causes/Sleeping Dogs
            # 使用 inf 确保 baseline_high 全为 False，避免将 Sleeping Dogs 误分类为 Sure Things
            baseline_pct = float('inf')
            warnings.append("High-CATE subgroup empty; all users classified as low-CATE")
        baseline_high = baseline_prob >= baseline_pct

        segments = np.empty(n, dtype=object)
        segments[:] = "Lost Causes"
        segments[cate_arr < 0.0] = "Sleeping Dogs"
        segments[(cate_arr >= 0.0) & cate_high & (~baseline_high)] = "Persuadables"
        segments[(cate_arr >= 0.0) & cate_high & baseline_high] = "Sure Things"
        segments[(cate_arr >= 0.0) & (~cate_high)] = "Lost Causes"

        segments_df = pd.DataFrame(
            {
                "cate": cate_arr.astype(float),
                "baseline_prob": baseline_prob.astype(float),
                "segment": pd.Series(segments, dtype="string"),
            }
        )
        
        # -----------------------------------------
        # 6) DQ & Validation
        # -----------------------------------------
        # DQ: empty quadrant defense.
        counts = segments_df["segment"].value_counts()
        warnings: list[str] = []
        for seg in ["Persuadables", "Sure Things", "Lost Causes", "Sleeping Dogs"]:
            if int(counts.get(seg, 0)) < 100:
                warnings.append(f"{seg} < 100")
        if warnings:
            segments_df["_warning"] = "; ".join(warnings)

        # DQ: Sleeping Dogs ratio sanity (RCT should not be dominated by negative uplift).
        sleeping_dog_pct = float(counts.get("Sleeping Dogs", 0)) / float(n)

        # Validation assertions (PRD)
        assert len(segments_df) == len(cate_arr), "Segment count mismatch"
        assert set(segments_df["segment"].dropna().unique()).issubset(_SEGMENTS), "Unknown segment"
        assert segments_df["segment"].notna().all(), "Missing segment assignment"
        assert int(counts.sum()) == len(cate_arr), "After segmentation, sample count mismatch"
        assert sleeping_dog_pct < 0.50, f"Sleeping Dogs ratio {sleeping_dog_pct:.1%} too high"
        persuadable_cates = segments_df.loc[segments_df["segment"] == "Persuadables", "cate"]
        if len(persuadable_cates) > 0:
            assert float(persuadable_cates.min()) >= 0.0, "Persuadables contains negative CATE"

        return segments_df

    except Exception as exc:
        raise RuntimeError(f"segment_users failed: {exc}") from exc


def simulate_roi(
    segments_df: pd.DataFrame,
    Y: pd.Series,
    T: pd.Series,
    budget_pcts: Sequence[float] = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    cost_per_contact: float = 1.0,
    random_state: int = 42,
) -> dict:
    """
    Simulate ROI under three targeting strategies:
      1) Full targeting (contact everyone)
      2) Random targeting (contact K% of users)
      3) Precision targeting (contact only Persuadables)
    Parameters
    ----------
    segments_df : pd.DataFrame (output of segment_users())
        用户分群结果 (segment_users() 的输出)
        shape: (~64K, 3+)
        columns:
        - cate: float — 原始 CATE 值
        - baseline_prob: float — 控制组转化率 (同 CATE 分位数桶)
        - segment: str — 分组标签 {"Persuadables", "Sure Things", "Lost Causes", "Sleeping Dogs"}
        - optional _warning: str — 分组质量警告 (如果分组不合理)
    Y : pd.Series
        实际转化效果 (conversion, 0/1)
    T : pd.Series
        处理组 (实际营销宣传) 标记 (0/1)
    budget_pcts : list[float] = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        模拟不同预算比例 (即投放人数占总人数的比例) 下的投放效果
    cost_per_contact : float = 1.0
        每次触达的单位成本 (归一化为 1)
    random_state : int = 42
        投放策略的随机种子
    Returns
    -------
    roi_results : dict
        包含三种策略的 ROI 效果

    NOTE 业务架构说明 (增量归因系统设计)
    --------------------------------
    - 增量转化是因果量，本函数使用 **CATE-sum 归因** 作为主核算系统：
      * 全量投放增量 = sum(cate) 对所有用户求和
      * 随机投放增量（期望值）= mean(cate) × 触达用户数
      * 精准投放增量 = sum(cate) 对 Persuadables 求和 (只对 Persuadables 投放)
    - 我们仍然从 (Y, T) 计算观测到的 RCT ATE 作为诊断指标，但不强制 sum(cate) == ATE × N：
      * sum(cate): 个体因果增量的聚合
                   反映的是 "如果真的给这 N 个用户投放, 模型预测会新增多少变化" (围观因果推断的直接输出)
      * ATE × N: 总体平均效应, 假设所有用户的 uplift 都等于平均值
                 忽略了异质性 (有些用户的 CATE 是 0.8, 有些是 -0.2)
      * 实际业务中，模型给出的 CATE 向量是估计值，由于校准误差，可能不会精确聚合到观测 ATE
      * 这种不一致性是可接受的，因为我们关注的是个体层面的因果增量排序，而非总体平均效应
    - budget_sweep 使用 CATE 排序模拟"预算越多，优先触达 uplift 越高的用户"，与上述归因系统保持内部一致性
    """
    try:
        # -------------------------------------------
        # 0) Input Validation & Type Conversion
        # -------------------------------------------
        if not isinstance(segments_df, pd.DataFrame) or segments_df.empty:
            raise ValueError("segments_df must be a non-empty pandas.DataFrame")
        if "cate" not in segments_df.columns or "segment" not in segments_df.columns:
            raise ValueError("segments_df must contain 'cate' and 'segment' columns")

        if not (isinstance(cost_per_contact, (int, float)) and float(cost_per_contact) > 0.0):
            raise ValueError("cost_per_contact must be > 0")

        if budget_pcts is None or len(budget_pcts) == 0:
            raise ValueError("budget_pcts must be a non-empty sequence")

        budget_list = [float(x) for x in budget_pcts]
        if any((not np.isfinite(p)) for p in budget_list):
            raise ValueError("budget_pcts contains NaN/inf")
        if any((p <= 0.0 or p > 1.0) for p in budget_list):
            raise ValueError("budget_pcts values must be in (0, 1]")

        # Assumes the sweep reaches 100% so we can validate the endpoint.
        if 1.0 not in budget_list:
            raise ValueError("budget_pcts must include 1.0 to validate full-budget endpoint")

        cate_arr = pd.to_numeric(segments_df["cate"], errors="coerce").to_numpy(dtype=float, copy=False).reshape(-1)
        if np.isnan(cate_arr).any():
            raise ValueError("segments_df['cate'] contains NaN/non-numeric values")
        if not np.isfinite(cate_arr).all():
            raise ValueError("segments_df['cate'] contains inf/-inf values")

        seg_series = segments_df["segment"].astype(str)
        if seg_series.isnull().any():
            raise ValueError("segments_df['segment'] contains NaN values")
        if not set(pd.unique(seg_series)).issubset(_SEGMENTS):
            raise ValueError("segments_df contains unknown segment label(s)")

        t_series = T if isinstance(T, pd.Series) else pd.Series(T)
        y_series = Y if isinstance(Y, pd.Series) else pd.Series(Y)

        if pd.api.types.is_bool_dtype(t_series):
            t_series = t_series.astype(int)
        if pd.api.types.is_bool_dtype(y_series):
            y_series = y_series.astype(int)

        t = pd.to_numeric(t_series, errors="coerce")
        y = pd.to_numeric(y_series, errors="coerce")
        if t.isnull().any():
            raise ValueError("T contains NaN/non-numeric values")
        if y.isnull().any():
            raise ValueError("Y contains NaN/non-numeric values")

        t = t.astype(int)
        y = y.astype(int)

        if len(segments_df) != len(t) or len(segments_df) != len(y):
            raise ValueError("Length mismatch among segments_df, Y, T")
        if not set(pd.unique(t)).issubset({0, 1}):
            raise ValueError("T must be binary (0/1)")
        if not set(pd.unique(y)).issubset({0, 1}):
            raise ValueError("Y must be binary (0/1)")

        n = int(len(segments_df))
        n_treated = int((t == 1).sum())
        n_control = int(n - n_treated)
        if n_treated <= 0 or n_control <= 0:
            raise ValueError("Both treated and control groups must be non-empty")

        # -------------------------------------------
        # 1) Strategy 1: Full Targeting (contact everyone)
        # -------------------------------------------
        # treated/control conversion rate
        treated_rate = float(y[t == 1].mean())
        control_rate = float(y[t == 0].mean())

        # Observed ATE compute from trated/control rate
        ate_observed = treated_rate - control_rate

        # 业务核算逻辑：增量转化 = sum(CATE)，而非 ATE × N
        #   - sum(CATE): 个体 uplift 的聚合，反映真实的因果增量
        #   - ATE × N: 总体平均效应，可能因模型校准误差与 sum(CATE) 不完全一致
        #   - 使用 CATE-sum 确保与 budget_sweep（也基于 CATE 排序）的内部一致性
        full_incremental = float(cate_arr.sum())

        # ATE compute from CATE
        ate_from_cate = float(full_incremental / float(n))
        full_cost = float(n * float(cost_per_contact))
        full_roi = float(full_incremental / full_cost) if full_cost > 0 else 0.0

        # -------------------------------------------
        # 2) Strategy 2: Random Targeting (budget sweep)
        # -------------------------------------------
        # 业务模拟逻辑：随机投放使用期望值（确定性），而非随机抽样
        #   - 随机投放增量 = mean(CATE) × 触达用户数（期望值）
        #   - 不使用随机抽样是因为我们关注的是策略的期望 ROI，而非单次实验的随机波动
        #   - 如果用随机抽样, 每次模拟的结果会因为抽样方差而波动, 反而掩盖不同策略本身的系统性差异
        #   - 这与精准投放/预算扫描使用相同的增量归因系统（CATE-sum）

        # Keep signature stable
        # Prepare for future stochastic simulations
        _ = int(random_state)  

        random_results: list[dict] = []
        for pct in budget_list:
            n_target = int(round(n * pct))
            n_target = max(1, min(n, n_target))

            # Compute expected incremental conversion
            inc = float(ate_from_cate * n_target)
            cost = float(n_target * float(cost_per_contact))
            roi = float(inc / cost) if cost > 0 else 0.0
            random_results.append(
                {
                    "budget_pct": float(pct),
                    "n_targeted": int(n_target),
                    "n_incremental_conv": float(inc),
                    "roi": float(roi),
                }
            )

        # -------------------------------------------
        # 3) Strategy 3: Precision Targeting (Persuadables only)
        # -------------------------------------------
        persuadables_mask = seg_series.to_numpy(dtype=str, copy=False) == "Persuadables"
        n_persuadables = int(persuadables_mask.sum())

        precision_incremental = float(cate_arr[persuadables_mask].sum()) if n_persuadables > 0 else 0.0
        precision_cost = float(n_persuadables * float(cost_per_contact))
        precision_roi = float(precision_incremental / precision_cost) if precision_cost > 0 else 0.0

        # 业务 KPI 计算：
        #   - 预算节省率 = (1 - Persuadables 占比) × 100%
        #     衡量精准投放相比全量投放节省了多少营销预算
        #   - 增量转化保留率 = (精准投放增量 / 全量投放增量) × 100%
        #     衡量精准投放在节省预算的同时，保留了多少增量转化效果
        budget_saving_pct = float((1.0 - (n_persuadables / n)) * 100.0)
        if full_incremental > 0:
            conversion_retention_pct = float((precision_incremental / full_incremental) * 100.0)
        else:
            conversion_retention_pct = 0.0

        precision_payload: dict = {
            "n_targeted": int(n_persuadables),
            "n_incremental_conv": float(precision_incremental),
            "total_cost": float(precision_cost),
            "roi": float(precision_roi),
            "budget_saving_pct": float(budget_saving_pct),
            "conversion_retention_pct": float(conversion_retention_pct),
        }
        if precision_incremental < 0.0:
            precision_payload["_warning"] = "Precision targeting has negative incremental conversions (sum(CATE) < 0)"

        # -------------------------------------------
        # 4) Budget Ccan: by CATE Ranking (high -> low)
        # -------------------------------------------
        # 业务逻辑：按 CATE 降序排列，模拟"预算越多，优先触达 CATE 越高的用户"
        #   - 这是最优投放策略的理论上界（Oracle）
        #   - 实际业务中，需要用 Uplift Model 预测 CATE 来近似这个排序
        order = np.argsort(-cate_arr, kind="mergesort")  # stable for ties

        budget_sweep: list[dict] = []
        for pct in budget_list:
            n_target = int(round(n * pct))
            n_target = max(1, min(n, n_target))

            # EXtract top n_target users after CATE sort (Descending)
            top_sum = float(cate_arr[order[:n_target]].sum())
            budget_sweep.append(
                {
                    "budget_pct": float(pct),
                    "n_targeted": int(n_target),
                    "cumulative_uplift": float(top_sum),
                }
            )

        roi_results = {
            "full_targeting": {
                "n_targeted": int(n),
                "n_incremental_conv": float(full_incremental),
                "total_cost": float(full_cost),
                "roi": float(full_roi),
            },
            "random_targeting": random_results,
            "precision_targeting": precision_payload,
            "budget_sweep": budget_sweep,
        }

        # ============================================
        # 5) Final Validation assertions
        # ============================================
        assert roi_results["precision_targeting"]["budget_saving_pct"] > 0.0, "Precision targeting failed to save budget (budget_saving_pct <= 0)"
        assert roi_results["precision_targeting"]["roi"] >= roi_results["full_targeting"]["roi"], (
            "Precision targeting ROI is lower than full targeting - check segmentation logic"
        )

        # Sweep endpoint should match full targeting (allow small numeric discrepancy).
        sweep_end = next((x for x in budget_sweep if abs(float(x["budget_pct"]) - 1.0) <= 1e-12), None)
        if sweep_end is None:
            raise AssertionError("Budget sweep missing 100% endpoint (budget_pct=1.0)")
        assert abs(float(sweep_end["cumulative_uplift"]) - full_incremental) < 1.0, "Budget sweep endpoint does not match full targeting incremental"

        cr = float(roi_results["precision_targeting"]["conversion_retention_pct"])
        assert 0.0 <= cr <= 150.0, "Conversion retention percentage out of bounds: {cr}% (expected [0, 150])"

        # Add lightweight diagnostics without affecting downstream usage.
        # (Optional fields; safe for JSON persistence.)
        roi_results["_meta"] = {
            "ate_observed": float(ate_observed),
            "ate_from_cate": float(ate_from_cate),
            "full_incremental_observed": float(ate_observed * n),
            "full_incremental_from_cate": float(full_incremental),
        }

        return roi_results

    except Exception as exc:
        raise RuntimeError(f"simulate_roi failed: {exc}") from exc
