# ===============================================
# Causal inference utilities (Phase 2).
# ===============================================
# This module implements MVP 2.1: propensity score estimation via Logistic Regression.

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


def estimate_ps(
    X: pd.DataFrame,
    T: pd.Series,
    random_state: int = 42,
) -> tuple[np.ndarray, LogisticRegression]:
    """
    Estimate propensity scores using Logistic Regression.
    Parameters
    ----------
    X : pd.DataFrame
        covariate matrix (config.data.covariates columns).
    T : pd.Series
        treatment indicator (0/1)
    random_state : int
        default=42
    Returns
    -------
    np.ndarray
        propensity score vector, shape (n,)
        Values are clipped into (0.01, 0.99) to avoid division-by-zero in IPW / X-Learner.
    LogisticRegression
        fitted model object for diagnostics

    DQ Defenses
    ----------
    - Clip boundaries: ps in [0.01, 0.99]
    - Model convergence: model.n_iter_[0] < 1000 (when fitted)
    - Input validation: X must not contain treatment/conversion/spend

    Verification Asserts (executed when applicable)
    -----------------------------------------------
      ASSERT len(ps) == len(T), "PS vector length mismatch"
      ASSERT ps.min() >= 0.01, "PS contains too-small values; clip failed"
      ASSERT ps.max() <= 0.99, "PS contains too-large values; clip failed"
      ASSERT model.n_iter_[0] < 1000, "Logistic Regression did not converge"

    RCT-specific validation (applied only when treatment ratio is consistent with 2:1)
    -------------------------------------------------------------------------------
      ASSERT 0.60 <= ps.mean() <= 0.72, "PS mean deviates from treatment ratio; check feature matrix"
      ASSERT ps.std() < 0.10, "PS std too large; RCT data should not be strongly predictable"
    """

    # -------------------------------------
    # 1) Input validation
    # ------------------------------------
    if X is None or T is None:
        raise ValueError("Input data cannot be empty")

    if not isinstance(X, pd.DataFrame):
        raise TypeError("X must be a pandas DataFrame")

    # Accept list/ndarray-like T, but work with a Series view to avoid mutating caller objects.
    T_series = T if isinstance(T, pd.Series) else pd.Series(T)

    if len(X) == 0 or len(T_series) == 0:
        raise ValueError("Input data cannot be empty")

    if len(X) != len(T_series):
        raise ValueError(f"Length mismatch: X has {len(X)} rows, T has {len(T_series)} rows")

    # X must not contain post-treatment outcomes/targets.
    forbidden_cols = ["treatment", "conversion", "spend","visit"]
    found_forbidden = [c for c in forbidden_cols if c in X.columns]
    if found_forbidden:
        raise ValueError(
            f"X contains forbidden columns: {found_forbidden}. "
            "These columns should not be used as covariates for PS estimation."
        )

    # Scikit-learn requires numeric finite features; fail early with a clear error.
    if X.isnull().any().any():
        raise ValueError("X contains NaN values; PS estimation requires complete covariates")
    if not all(pd.api.types.is_numeric_dtype(X[c]) for c in X.columns):
        raise ValueError("X must contain only numeric columns for Logistic Regression")
    if not np.isfinite(X.to_numpy(dtype=float, copy=False)).all():
        raise ValueError("X contains inf or -inf values; PS estimation requires finite covariates")

    # Treatment must be binary 0/1.
    T_numeric = pd.to_numeric(T_series, errors="coerce")
    if T_numeric.isnull().any():
        raise ValueError("Treatment must be binary (0/1). Found NaN or non-numeric values.")
    unique_t = set(pd.unique(T_numeric))
    if not unique_t.issubset({0, 1}):
        raise ValueError(f"Treatment must be binary (0/1). Found unique values: {sorted(unique_t)}")

    # ------------------------------------------------
    # 2) Edge-case handling (single-class T)
    # ------------------------------------------------
    # If only one class exists, LogisticRegression cannot be fit.
    # Return a constant vector at the clip boundary for downstream IPW safety.
    if unique_t == {1}:
        ps = np.full(shape=(len(T_numeric),), fill_value=0.99, dtype=float)
        model = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=random_state)
        assert len(ps) == len(T_series), "PS vector length mismatch"
        assert ps.min() >= 0.01, "PS contains too-small values; clip failed"
        assert ps.max() <= 0.99, "PS contains too-large values; clip failed"
        return ps, model

    if unique_t == {0}:
        ps = np.full(shape=(len(T_numeric),), fill_value=0.01, dtype=float)
        model = LogisticRegression(max_iter=1000, solver="lbfgs", random_state=random_state)
        assert len(ps) == len(T_series), "PS vector length mismatch"
        assert ps.min() >= 0.01, "PS contains too-small values; clip failed"
        assert ps.max() <= 0.99, "PS contains too-large values; clip failed"
        return ps, model

    # ------------------------------------------------
    # 3) Propensity score estimation
    # ------------------------------------------------
    MAX_ITER = 1000

    model = LogisticRegression(
        max_iter=MAX_ITER,
        solver="lbfgs",
        random_state=random_state,
    )
    # Construct estimator
    model.fit(X, T_numeric.astype(int))

    ps_raw = model.predict_proba(X)[:, 1]
    ps = np.clip(ps_raw, 0.01, 0.99)

    # ------------------------------------------------
    # 4) Verification asserts (per spec)
    # ------------------------------------------------
    assert len(ps) == len(T_series), "PS vector length mismatch"
    assert ps.min() >= 0.01, "PS contains too-small values; clip failed"
    assert ps.max() <= 0.99, "PS contains too-large values; clip failed"

    # Check if model converged
    actual_iters = model.n_iter_[0]
    if actual_iters >= MAX_ITER:
        raise ValueError(
        f"Logistic Regression failed to converge within {MAX_ITER} iterations. "
        f"Actual iterations: {actual_iters}. "
        "Consider: (1) increasing max_iter, (2) standardizing features, "
        "(3) checking for perfect separation, or (4) using regularization."
    )

    # RCT-specific validation: enforce only when the treatment ratio indicates a 2:1 RCT-like design.
    # This keeps the function reusable for non-RCT/synthetic unit tests while preserving the Phase 2 narrative checks.
    t_rate = float(T_numeric.mean())
    if 0.60 <= t_rate <= 0.72:
        assert 0.60 <= float(ps.mean()) <= 0.72, "PS mean deviates from treatment ratio; check feature matrix"
        assert float(ps.std()) < 0.10, "PS std too large; RCT data should not be strongly predictable"

    return ps, model

