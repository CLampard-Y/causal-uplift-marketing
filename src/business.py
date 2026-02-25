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
        baseline conversion rate for "high baseline" ( 50% + threshold )
        default=0.5
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
        # Stable default for baseline visualization (not exposed as param to keep API minimal)
        n_baseline_bins = 20

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
        # Business-aligned interpretation:
        # - Sleeping Dogs: cate < 0 (negative treatment effect)
        # - Persuadables: cate >= cate_threshold (high uplift)
        # - Sure Things: cate >= 0 but not high uplift, and baseline is high
        # - Lost Causes: cate >= 0 but not high uplift, and baseline is low
        

        # Baseline high/low threshold: relative to global control conversion rate.
        baseline_high = baseline_prob >= (1.0 +float(baseline_threshold)) * control_conversion_rate
        cate_high = cate_arr >= cate_threshold

        segments = np.empty(n, dtype=object)
        segments[:] = "Lost Causes"
        segments[cate_arr < 0.0] = "Sleeping Dogs"
        segments[(cate_arr >= 0.0) & cate_high] = "Persuadables"
        segments[(cate_arr >= 0.0) & (~cate_high) & baseline_high] = "Sure Things"
        segments[(cate_arr >= 0.0) & (~cate_high) & (~baseline_high)] = "Lost Causes"

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

