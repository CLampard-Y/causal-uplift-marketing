# ==========================================
# Business layer utilities
# ==========================================
from __future__ import annotations

from typing import Literal

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

        # 基线高低阈值：在高 CATE 子群内部使用百分位数分割
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

