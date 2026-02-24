# ==========================================
# Uplift / CATE estimation utilities (Phase 2 MVP 2.4).
# ==========================================
from __future__ import annotations

from typing import Tuple, Optional

import numpy as np
import pandas as pd

# Helper: validate X, T, Y inputs
def _validate_xy_t_inputs(X: pd.DataFrame, T: pd.Series, Y: pd.Series) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    if X is None or T is None or Y is None:
        raise ValueError("X, T, Y cannot be None")
    if not isinstance(X, pd.DataFrame):
        raise TypeError("X must be a pandas.DataFrame")
    if X.empty:
        raise ValueError("X cannot be empty")

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

    if len(X) != len(t) or len(X) != len(y):
        raise ValueError(f"Length mismatch: len(X)={len(X)}, len(T)={len(t)}, len(Y)={len(y)}")

    if X.isnull().any().any():
        raise ValueError("X contains NaN values")
    if not all(pd.api.types.is_numeric_dtype(X[c]) for c in X.columns):
        raise ValueError("X must contain only numeric columns")
    if not np.isfinite(X.to_numpy(dtype=float, copy=False)).all():
        raise ValueError("X contains inf/-inf values")

    if not set(pd.unique(t)).issubset({0, 1}):
        raise ValueError("T must be binary (0/1)")
    if not set(pd.unique(y)).issubset({0, 1}):
        raise ValueError("Y must be binary (0/1)")

    return X, t, y

def _fit_classifier_with_spw(
    X: pd.DataFrame,
    y: pd.Series,
    *,
    n_estimators: int,
    max_depth: int,
    random_state: int,
    scale_pos_weight: float,
):
    """
    Fit a probabilistic binary classifier with an imbalance weight.

    Preferred backend: xgboost.XGBClassifier
    Fallback backend (if xgboost is not installed): 
        sklearn.linear_model.LogisticRegression
    """
    if not isinstance(n_estimators, int) or n_estimators <= 0:
        raise ValueError("n_estimators must be a positive int")
    if not isinstance(max_depth, int) or max_depth <= 0:
        raise ValueError("max_depth must be a positive int")

    try:
        from xgboost import XGBClassifier

        # Customized XGBoost parameters to suit the Hillstrom RCT.
        # XGBoost default parameters are not suitable for RCT.
        model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            min_child_weight=20.0,                  # Avoide overfitting
            reg_lambda=10.0,
            reg_alpha=0.0,
            max_delta_step=1.0,                     # Avoide risky splits
            random_state=random_state,
            scale_pos_weight=scale_pos_weight,      # Balance class imbalance
            objective="binary:logistic",
            eval_metric="logloss",
            n_jobs=-1,
        )
        model.fit(X, y)
        return model
    except Exception:
        # Fallback: well-calibrated linear probabilities.
        # Model choice: why not RandomForestClassifier
        from sklearn.linear_model import LogisticRegression

        # Why not `class_weight="balanced"` (sklearn default):
        #    1. Will systematically raise predicted probabilities
        #    2. No other hyperparameters to balance (e.g., `max_depth`, `min_child_weight`)
        #    3. Damage probability calibration ( CATE rely on calibrated probabilities )
        model = LogisticRegression(
            max_iter=1000,
            solver="lbfgs",
            random_state=random_state,
        )
        model.fit(X, y)

        return model

# Helper: Correct for scale_pos_weight if used.
def _correct_weighted(
    p: np.ndarray,
    spw_used: float,
    model
) -> np.ndarray:
    p_arr = np.asarray(p, dtype=float).reshape(-1)
    if p_arr.size == 0:
        return p_arr
    if not np.isfinite(p_arr).all():
        raise ValueError("Predicted probabilities contain NaN/inf")

    spw = spw_used
    if spw is None or (isinstance(spw, float) and (not np.isfinite(spw))):
        spw = None

    if spw is None and hasattr(model, "get_xgb_params"):
        try:
            spw = float(model.get_xgb_params().get("scale_pos_weight", 1.0))
        except Exception:
            spw = None

    if spw is None or (not np.isfinite(spw)) or spw <= 0 or abs(spw - 1.0) <= 1e-12:
        return p_arr

    eps = 1e-6
    pc = np.clip(p_arr, eps, 1.0 - eps)
    logit = np.log(pc / (1.0 - pc))
    logit = np.clip(logit - np.log(spw), -50.0, 50.0)
    return 1.0 / (1.0 + np.exp(-logit))

# Helper: X-Learner stage 3 (pseudo-outcome regression)
def _fit_regressor(
    X: pd.DataFrame,
    y: np.ndarray,
    *,
    n_estimators: int,
    max_depth: int,
    random_state: int,
):
    if not isinstance(n_estimators, int) or n_estimators <= 0:
        raise ValueError("n_estimators must be a positive int")
    if not isinstance(max_depth, int) or max_depth <= 0:
        raise ValueError("max_depth must be a positive int")

    y_arr = np.asarray(y, dtype=float)
    if y_arr.ndim != 1:
        raise ValueError("Regressor target must be 1D")
    if len(y_arr) != len(X):
        raise ValueError("Length mismatch between X and regressor target")
    if not np.isfinite(y_arr).all():
        raise ValueError("Regressor target contains NaN/inf")

    try:
        from xgboost import XGBRegressor

        # Keep this intentionally conservative to reduce pseudo-outcome overfitting spikes.
        model = XGBRegressor(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            min_child_weight=20.0,
            reg_lambda=10.0,
            reg_alpha=0.0,
            random_state=random_state,
            objective="reg:squarederror",
            n_jobs=-1,
        )
        model.fit(X, y_arr)
        return model
    
    except Exception:

        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler

        model = make_pipeline(
            StandardScaler(),
            Ridge(alpha=10.0, random_state=random_state),
        )
        model.fit(X, y_arr)
        return model
    

def fit_s_learner(
    X: pd.DataFrame,
    T: pd.Series,
    Y: pd.Series,
    X_pred: Optional[pd.DataFrame] = None,
    n_estimators: int = 100,
    max_depth: int = 5,
    random_state: int = 42,
) -> np.ndarray:
    """
    Fit an S-Learner CATE estimator (single model with treatment as a feature).
    Parameters
    ----------
    X : pd.DataFrame
        covariate matrix.
    T : pd.Series
        treatment indicator (0/1)
    Y : pd.Series
        outcome (conversion, 0/1)
    X_pred : pd.DataFrame
        optional, out-of-sample predictions
    n_estimators : int
        default=100
    max_depth : int
        default=5
    random_state : int
        default=42
    Returns
    -------
    cate : np.ndarray
        CATE vector, shape (n,)
        Expected magnitude: roughly within [-0.02, 0.02] on Hillstrom RCT.
    ------------------------------------------------------
    Known limitation
    ------------------------------------------------------
    S-Learner can shrink/ignore the treatment signal when the true effect is small
    (like in Hillstrom RCT, conversion rate roughly 0.9%)
    producing CATE values near zero. This is structural limitation, not implementation bug.
    """
    try:
        X, t, y = _validate_xy_t_inputs(X, T, Y)

        # S-Learner augmentation: append T as an additional feature column
        t_col = "__treatment_feature__"
        X_aug = X.copy()
        X_aug[t_col] = t.to_numpy(dtype=int, copy=False)

        # Handle class imbalance via scale_pos_weight.
        # NOTE (important RCT calibration detail):
        # - On RCT data we do NOT want probability distortion that inflates CATE.
        # - The helper `_fit_classifier_with_spw` applies xgboost when xgboost is available,
        #   but uses an *unweighted* fallback model for calibrated probabilities when xgboost is unavailable.
        n_pos = int((y == 1).sum())
        n_neg = int((y == 0).sum())
        if n_pos <= 0:
            raise ValueError("Y contains no positive samples; cannot compute scale_pos_weight")
        spw = float(n_neg / n_pos)

        model = _fit_classifier_with_spw(
            X_aug,
            y,
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            scale_pos_weight=spw,
        )

        # Prediction on X_pred if provided
        X_out = X if X_pred is None else X_pred
        if not isinstance(X_out, pd.DataFrame):
            raise TypeError("X_pred must be a pandas.DataFrame")
        if list(X_out.columns) != list(X.columns):
            raise ValueError("X_pred columns must match X columns (same order and names)")
        if X_out.isnull().any().any() or not np.isfinite(X_out.to_numpy(dtype=float, copy=False)).all():
            raise ValueError("X_pred contains NaN/inf values")

        # Counterfactual prediction: P(Y=1|X_out, T=1) - P(Y=1|X_out, T=0)
        # Assume all are treated.
        X_treat = X_out.copy()
        X_treat[t_col] = 1

        # Assume all are control.
        X_control = X_out.copy()
        X_control[t_col] = 0

        if not hasattr(model, "predict_proba"):
            raise TypeError("Outcome model does not support predict_proba")
        
        # Predict (conversion) probabilities for each group (treate/control).
        proba_1 = np.asarray(model.predict_proba(X_treat), dtype=float)
        proba_0 = np.asarray(model.predict_proba(X_control), dtype=float)
        if proba_1.ndim != 2 or proba_1.shape[1] < 2 or proba_0.ndim != 2 or proba_0.shape[1] < 2:
            raise ValueError("predict_proba must return shape (n_samples, 2 (or more) columns)")
        
        # Extract all rows and index "1" columns (Positive posibility).
        p1 = proba_1[:, 1]
        p0 = proba_0[:, 1]

        # Correct for scale_pos_weight if present (probability scale/odds shift).
        # See `_correct_weighted` docstring for rationale.
        p1 = _correct_weighted(p1, np.nan, model)
        p0 = _correct_weighted(p0, np.nan, model)

        cate = (np.asarray(p1, dtype=float) - np.asarray(p0, dtype=float)).astype(float)

        # DQ assertions 
        assert len(cate) == len(X_out), "CATE vector length mismatch"
        assert not np.isnan(cate).any(), "CATE contains NaN"
        assert float(np.max(np.abs(cate))) < 0.50, "CATE magnitude too large; check model"

        return cate

    except Exception as exc:
        raise RuntimeError(f"fit_s_learner failed: {exc}") from exc
    
def fit_t_learner(
    X: pd.DataFrame,
    T: pd.Series,
    Y: pd.Series,
    X_pred: Optional[pd.DataFrame] = None,
    n_estimators: int = 100,
    max_depth: int = 5,
    random_state: int = 42,
) -> np.ndarray:
    """
    Fit a T-Learner CATE estimator (two separate models).
    Parameters
    ----------
    X : pd.DataFrame
        covariate matrix.
    T : pd.Series
        treatment indicator (0/1)
    Y : pd.Series
        outcome (conversion, 0/1)
    X_pred : pd.DataFrame
        optional, out-of-sample predictions
    n_estimators : int
        default=100
    max_depth : int
        default=5
    random_state : int
        default=42
    Returns
    -------
    cate : np.ndarray
        CATE vector, shape (n,)
        Expected magnitude: roughly within [-0.02, 0.02]
    """
    try:
        X, t, y = _validate_xy_t_inputs(X, T, Y)

        t_arr = t.to_numpy(dtype=int, copy=False)

        # [0]: Get the row indices of treatment and control groups.
        treat_pos = np.where(t_arr == 1)[0]
        ctrl_pos = np.where(t_arr == 0)[0]
        if len(treat_pos) == 0 or len(ctrl_pos) == 0:
            raise ValueError("Both treatment and control groups must be non-empty")

        X_treat = X.iloc[treat_pos].copy()
        y_treat = y.iloc[treat_pos].copy()
        X_ctrl = X.iloc[ctrl_pos].copy()
        y_ctrl = y.iloc[ctrl_pos].copy()

        n_pos_t = int((y_treat == 1).sum())
        n_neg_t = int((y_treat == 0).sum())
        n_pos_c = int((y_ctrl == 1).sum())
        n_neg_c = int((y_ctrl == 0).sum())
        if n_pos_t <= 0 or n_pos_c <= 0:
            raise ValueError("One group has no positive samples; cannot fit outcome models")
        
        # Compute scale_pos_weight separately per group because rate differ.
        spw_t = float(n_neg_t / n_pos_t)
        spw_c = float(n_neg_c / n_pos_c)

        model_1 = _fit_classifier_with_spw(
            X_treat,
            y_treat,
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            scale_pos_weight=spw_t,
        )
        model_0 = _fit_classifier_with_spw(
            X_ctrl,
            y_ctrl,
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            scale_pos_weight=spw_c,
        )

        # Prediction on X_pred if provided
        X_out = X if X_pred is None else X_pred
        if not isinstance(X_out, pd.DataFrame):
            raise TypeError("X_pred must be a pandas.DataFrame")
        if list(X_out.columns) != list(X.columns):
            raise ValueError("X_pred columns must match X columns (same order and names)")
        if X_out.isnull().any().any() or not np.isfinite(X_out.to_numpy(dtype=float, copy=False)).all():
            raise ValueError("X_pred contains NaN/inf values")


        if not hasattr(model_1, "predict_proba") or not hasattr(model_0, "predict_proba"):
            raise TypeError("Outcome models must support predict_proba")

        p1 = np.asarray(model_1.predict_proba(X_out), dtype=float)[:, 1]
        p0 = np.asarray(model_0.predict_proba(X_out), dtype=float)[:, 1]

        # Same as fit_s_learner: correct for scale_pos_weight to avoid probability scale distortion.
        p1 = _correct_weighted(p1, np.nan, model_1)
        p0 = _correct_weighted(p0, np.nan, model_0)

        # CATE = mu_1(x) - mu_0(x)
        cate = (p1 - p0).astype(float)

        assert len(cate) == len(X_out), "CATE vector length mismatch"
        assert not np.isnan(cate).any(), "CATE contains NaN"
        assert float(np.max(np.abs(cate))) < 0.50, "CATE magnitude too large; check model"

        return cate

    except Exception as exc:
        raise RuntimeError(f"fit_t_learner failed: {exc}") from exc
    

def fit_x_learner(
    X: pd.DataFrame,
    T: pd.Series,
    Y: pd.Series,
    ps: np.ndarray,
    X_pred: Optional[pd.DataFrame] = None,
    ps_pred: Optional[np.ndarray] = None,
    n_estimators: int = 100,
    max_depth: int = 5,
    random_state: int = 42,
) -> np.ndarray:
    """
    Fit an X-Learner CATE estimator.
    Parameters
    ----------
    X : pd.DataFrame
        covariate matrix.
    T : pd.Series
        treatment indicator (0/1)
    Y : pd.Series
        outcome (conversion, 0/1)
    ps : np.ndarray
        propensity scores 
    X_pred : pd.DataFrame
        optional, out-of-sample predictions
    ps_pred : np.ndarray
        optional, out-of-sample propensity scores
    n_estimators : int
        default=100
    max_depth : int
        default=5
    random_state : int
        default=42
    Returns
    -------
    cate : np.ndarray
        CATE vector, shape (n,)
        Expected magnitude: roughly within [-0.02, 0.02]
    """
    try:
        X, t, y = _validate_xy_t_inputs(X, T, Y)

        ps_train = np.asarray(ps, dtype=float).reshape(-1)
        if len(ps_train) != len(X):
            raise ValueError("ps length mismatch")
        if not np.isfinite(ps_train).all():
            raise ValueError("ps contains NaN/inf")
        ps_train = np.clip(ps_train, 0.01, 0.99)

        treated_mask = t.to_numpy(dtype=int, copy=False) == 1
        control_mask = ~treated_mask
        if treated_mask.sum() <= 0 or control_mask.sum() <= 0:
            raise ValueError("Both treated and control groups must be non-empty for X-Learner")

        X_treat = X.loc[treated_mask].copy()
        y_treat = y.loc[treated_mask].copy()
        X_control = X.loc[control_mask].copy()
        y_control = y.loc[control_mask].copy()

        # Group-specific imbalance weights for outcome models.
        n_pos_t = int((y_treat == 1).sum())
        n_neg_t = int((y_treat == 0).sum())
        n_pos_c = int((y_control == 1).sum())
        n_neg_c = int((y_control == 0).sum())
        if n_pos_t <= 0 or n_pos_c <= 0:
            raise ValueError("One group contains no positive samples; cannot compute scale_pos_weight")
        spw_treat = float(n_neg_t / n_pos_t)
        spw_control = float(n_neg_c / n_pos_c)

        # Step 1: outcome models
        model_1 = _fit_classifier_with_spw(
            X_treat,
            y_treat,
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            scale_pos_weight=spw_treat,
        )
        model_0 = _fit_classifier_with_spw(
            X_control,
            y_control,
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
            scale_pos_weight=spw_control,
        )

        if not hasattr(model_0, "predict_proba") or not hasattr(model_1, "predict_proba"):
            raise TypeError("Outcome model does not support predict_proba")

        # Step 2: pseudo-outcomes
        mu0_on_treat = np.asarray(model_0.predict_proba(X_treat), dtype=float)[:, 1]
        mu1_on_control = np.asarray(model_1.predict_proba(X_control), dtype=float)[:, 1]

        # Correct probability scale shifts from scale_pos_weight before forming pseudo-outcomes.
        mu0_on_treat = _correct_weighted(mu0_on_treat, np.nan, model_0)
        mu1_on_control = _correct_weighted(mu1_on_control, np.nan, model_1)

        # Pseudo-outcomes: 
        #   D_1 = Y_1 - mu0(X_1)
        #   D_0 = mu1(X_0) - Y_0
        D_1 = y_treat.to_numpy(dtype=float, copy=False) - mu0_on_treat
        D_0 = mu1_on_control - y_control.to_numpy(dtype=float, copy=False)

        if not np.isfinite(D_1).all() or not np.isfinite(D_0).all():
            raise ValueError("Pseudo-outcomes contain NaN/inf")

        # Step 3: tau models (regression)
        tau_1_model = _fit_regressor(
            X_treat,
            D_1,
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
        )
        tau_0_model = _fit_regressor(
            X_control,
            D_0,
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=random_state,
        )

        # Step 4: combine on X_out with PS weighting
        X_out = X if X_pred is None else X_pred
        if not isinstance(X_out, pd.DataFrame):
            raise TypeError("X_pred must be a pandas.DataFrame")
        if list(X_out.columns) != list(X.columns):
            raise ValueError("X_pred columns must match X columns (same order and names)")
        if X_out.isnull().any().any() or not np.isfinite(X_out.to_numpy(dtype=float, copy=False)).all():
            raise ValueError("X_pred contains NaN/inf values")

        ps_out = ps_train if ps_pred is None else np.asarray(ps_pred, dtype=float).reshape(-1)
        if len(ps_out) != len(X_out):
            raise ValueError("ps_pred length mismatch")
        if not np.isfinite(ps_out).all():
            raise ValueError("ps_pred contains NaN/inf")
        ps_out = np.clip(ps_out, 0.01, 0.99)

        if not hasattr(tau_1_model, "predict") or not hasattr(tau_0_model, "predict"):
            raise TypeError("Tau model does not support predict")
        tau_1 = np.asarray(tau_1_model.predict(X_out), dtype=float).reshape(-1)
        tau_0 = np.asarray(tau_0_model.predict(X_out), dtype=float).reshape(-1)
        if len(tau_1) != len(X_out) or len(tau_0) != len(X_out):
            raise ValueError("Tau prediction length mismatch")

        cate = ((1.0 - ps_out) * tau_1 + ps_out * tau_0).astype(float)

        # DQ assertions (Phase2.md, shared across learners)
        assert len(cate) == len(X_out), "CATE vector length mismatch"
        assert not np.isnan(cate).any(), "CATE contains NaN"
        assert float(np.max(np.abs(cate))) < 0.50, "CATE magnitude too large; check model"

        return cate

    except Exception as exc:
        raise RuntimeError(f"fit_x_learner failed: {exc}") from exc


def compute_qini(
    cate: np.ndarray,
    T: pd.Series,
    Y: pd.Series,
    n_bins: int = 20,
) -> dict:
    """
    Compute Qini curve / AUUC on a test set.
    Parameters
    ----------
    cate : np.ndarray
        CATE estimates on the *test set*, shape (N,). Higher means "more uplift", so we sort descending.
    T : pd.Series
        Treatment indicator on test set, binary 0/1, shape (N,).
    Y : pd.Series
        Outcome (conversion) on test set, binary 0/1, shape (N,).
    n_bins : int
        Number of bins to use for the histogram.
        Default is 20.
    Returns
    -------
    qini : dict
        Qini curve / AUUC on a test set .   
        dict with:
        - qini_x: list[float]   targeting fractions from 0 to 1
        - qini_y: list[float]   cumulative incremental conversions (Qini curve)
        - random_y: list[float] random baseline line
        - auuc: float           area under qini curve
        - random_auuc: float    area under random line
        - qini_coefficient: float  auuc - random_auuc
    """
    try:
        # -------------------------------------------
        # 1) Validation
        # -------------------------------------------
        cate_arr = np.asarray(cate, dtype=float).reshape(-1)
        if cate_arr.ndim != 1:
            raise ValueError("cate must be a 1D array")
        if cate_arr.size == 0:
            raise ValueError("cate cannot be empty")
        if not np.isfinite(cate_arr).all():
            raise ValueError("cate contains NaN/inf values")
        if not isinstance(n_bins, int) or n_bins <= 1:
            raise ValueError("n_bins must be an int >= 2")

        # Type conversion
        t_series = T if isinstance(T, pd.Series) else pd.Series(T)
        y_series = Y if isinstance(Y, pd.Series) else pd.Series(Y)

        if pd.api.types.is_bool_dtype(t_series):
            t_series = t_series.astype(int)
        if pd.api.types.is_bool_dtype(y_series):
            y_series = y_series.astype(int)

        # coerce: Convert not-a-number values to NaN
        t = pd.to_numeric(t_series, errors="coerce").astype(float)
        y = pd.to_numeric(y_series, errors="coerce").astype(float)

        # Check for NaN/non-numeric values
        if t.isnull().any():
            raise ValueError("T contains NaN/non-numeric values")
        if y.isnull().any():
            raise ValueError("Y contains NaN/non-numeric values")

        t = t.astype(int)
        y = y.astype(int)

        if len(t) != len(cate_arr) or len(y) != len(cate_arr):
            raise ValueError("Length mismatch among cate, T, Y")
        if not set(pd.unique(t)).issubset({0, 1}):
            raise ValueError("T must be binary (0/1)")
        if not set(pd.unique(y)).issubset({0, 1}):
            raise ValueError("Y must be binary (0/1)")

        n = int(len(cate_arr))
        n_t = int((t == 1).sum())
        n_c = int(n - n_t)
        if n_t <= 0 or n_c <= 0:
            raise ValueError("Both treated and control groups must be non-empty")

        # -------------------------------------------
        # 2) Sort Uplift (CATE) Descending
        # -------------------------------------------
        # Sort by predicted uplift (CATE) descending
        # mergesort: stable, reproducible, O(N log N) sort
        # -cate_arr: descending order by CATE
        sorted_idx = np.argsort(-cate_arr, kind="mergesort")
        t_sorted = t.to_numpy(dtype=int, copy=False)[sorted_idx]
        y_sorted = y.to_numpy(dtype=int, copy=False)[sorted_idx]

        # Total incremental conversions for the full population (random baseline endpoint)
        y_t_rate = float(y[t == 1].mean())
        y_c_rate = float(y[t == 0].mean())
        total_uplift = (y_t_rate - y_c_rate) * float(n_c)

        qini_x: list[float] = [0.0]
        qini_y: list[float] = [0.0]
        random_y: list[float] = [0.0]

        # -------------------------------------------
        # 3) Construct Bin Boundaries
        # -------------------------------------------
        # Bin boundaries: cumulative top-k fractions
        # Using linspace avoids rounding drift and guarantees the last point hits N
        # Why not np.arrange(0, n, n // n_bins):
        #   When n can no be evenly divided by n_bins, the last bin will be smaller
        boundaries = np.linspace(0, n, n_bins + 1)
        boundaries = np.round(boundaries).astype(int)

        # Ensure boundaries are non-decreasing and within [0, n]
        boundaries[0] = 0
        boundaries[-1] = n

        # -------------------------------------------
        # 4) Compute Bins 
        # -------------------------------------------
        # Ensure boundaries are non-decreasing and within [0, n]
        boundaries = np.clip(boundaries, 0, n)
        for k in range(1, n_bins + 1):
            end = int(boundaries[k])
            if end <= 0:
                fraction = float(k) / float(n_bins)
                qini_x.append(fraction)
                qini_y.append(0.0)
                random_y.append(total_uplift * fraction)
                continue

            t_k = t_sorted[:end]
            y_k = y_sorted[:end]

            n_t_k = int(t_k.sum())
            n_c_k = int(len(t_k) - n_t_k)

            # DQ: division-by-zero guard
            if n_t_k > 0 and n_c_k > 0:
                # Phase2.md formula (keep denominators as FULL-population N_T/N_C):
                # uplift_k = (sum(Y_treat_topk)/N_T - sum(Y_ctrl_topk)/N_C) * N_C
                sum_y_t_k = float(y_k[t_k == 1].sum())
                sum_y_c_k = float(y_k[t_k == 0].sum())
                uplift_k = (sum_y_t_k / float(n_t) - sum_y_c_k / float(n_c)) * float(n_c)
            else:
                uplift_k = 0.0

            fraction = float(k) / float(n_bins)
            qini_x.append(fraction)
            qini_y.append(float(uplift_k))
            random_y.append(float(total_uplift) * fraction)

        # -------------------------------------------
        # 5) Compute AUUC and Qini Coefficient
        # -------------------------------------------
        # NumPy 2.x: np.trapz was removed in favor of np.trapezoid.
        auuc = float(np.trapezoid(np.asarray(qini_y, dtype=float), np.asarray(qini_x, dtype=float)))
        random_auuc = float(np.trapezoid(np.asarray(random_y, dtype=float), np.asarray(qini_x, dtype=float)))
        qini_coefficient = float(auuc - random_auuc)

        result = {
            "qini_x": [float(v) for v in qini_x],
            "qini_y": [float(v) for v in qini_y],
            "random_y": [float(v) for v in random_y],
            "auuc": auuc,
            "random_auuc": random_auuc,
            "qini_coefficient": qini_coefficient,
        }

        # Required assertions
        assert len(result["qini_x"]) == n_bins + 1, "Qini edge points count mismatch"
        assert result["qini_x"][-1] == 1.0, "Qini edge points not at 100%"
        assert abs(result["qini_y"][-1] - result["random_y"][-1]) < 1.0, "Qini edge points not converging"

        return result

    except Exception as exc:
        raise RuntimeError(f"compute_qini failed: {exc}") from exc
