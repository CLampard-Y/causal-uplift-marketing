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
    Fallback backend (if xgboost is not installed): sklearn.ensemble.RandomForestClassifier
    """
    if not isinstance(n_estimators, int) or n_estimators <= 0:
        raise ValueError("n_estimators must be a positive int")
    if not isinstance(max_depth, int) or max_depth <= 0:
        raise ValueError("max_depth must be a positive int")

    try:
        # Prefer XGBoost when available (Phase2 spec).
        # NOTE:
        # - `scale_pos_weight` is necessary to handle extreme class imbalance.
        # - But it can distort probability calibration. We correct predict_proba()
        #   in the public learner functions (see Chinese comments there).
        from xgboost import XGBClassifier

        model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=0.05,
            subsample=0.9,
            colsample_bytree=0.9,
            min_child_weight=20.0,
            reg_lambda=10.0,
            reg_alpha=0.0,
            max_delta_step=1.0,
            random_state=random_state,
            scale_pos_weight=scale_pos_weight,
            objective="binary:logistic",
            eval_metric="logloss",
            n_jobs=-1,
        )
        model.fit(X, y)
        return model
    except Exception:
        # Fallback: well-calibrated linear probabilities.
        from sklearn.linear_model import LogisticRegression

        model = LogisticRegression(
            max_iter=1000,
            solver="lbfgs",
            random_state=random_state,
        )
        model.fit(X, y)
        return model
    
def _fit_regressor(
    X: pd.DataFrame,
    y: np.ndarray,
    *,
    n_estimators: int,
    max_depth: int,
    random_state: int,
):
    """
    Fit a regression model for pseudo-outcomes (imputed treatment effects).

    Preferred backend: xgboost.XGBRegressor
    Fallback backend (if xgboost is not installed): sklearn.pipeline(StandardScaler + Ridge)
    """
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
    producing CATE values near zero. This is a structural limitation, not an implementation bug.
    """
    try:
        X, t, y = _validate_xy_t_inputs(X, T, Y)

        # S-Learner augmentation: append T as an additional feature column.
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
        X_treat = X_out.copy()
        X_treat[t_col] = 1
        X_control = X_out.copy()
        X_control[t_col] = 0

        if not hasattr(model, "predict_proba"):
            raise TypeError("Outcome model does not support predict_proba")
        proba_1 = np.asarray(model.predict_proba(X_treat), dtype=float)
        proba_0 = np.asarray(model.predict_proba(X_control), dtype=float)
        if proba_1.ndim != 2 or proba_1.shape[1] < 2 or proba_0.ndim != 2 or proba_0.shape[1] < 2:
            raise ValueError("predict_proba must return shape (n_samples, 2+)")
        p1 = proba_1[:, 1]
        p0 = proba_0[:, 1]

        spw_used = None
        if hasattr(model, "get_xgb_params"):
            try:
                spw_used = float(model.get_xgb_params().get("scale_pos_weight", 1.0))
            except Exception:
                spw_used = None

        if spw_used is not None and np.isfinite(spw_used) and spw_used > 0 and abs(spw_used - 1.0) > 1e-12:
            eps = 1e-6
            p1c = np.clip(np.asarray(p1, dtype=float), eps, 1.0 - eps)
            p0c = np.clip(np.asarray(p0, dtype=float), eps, 1.0 - eps)
            logit1 = np.log(p1c / (1.0 - p1c))
            logit0 = np.log(p0c / (1.0 - p0c))
            logit1 = np.clip(logit1 - np.log(spw_used), -50.0, 50.0)
            logit0 = np.clip(logit0 - np.log(spw_used), -50.0, 50.0)
            p1 = 1.0 / (1.0 + np.exp(-logit1))
            p0 = 1.0 / (1.0 + np.exp(-logit0))

        cate = (np.asarray(p1, dtype=float) - np.asarray(p0, dtype=float)).astype(float)

        # DQ assertions 
        assert len(cate) == len(X_out), "CATE vector length mismatch"
        assert not np.isnan(cate).any(), "CATE contains NaN"
        assert float(np.max(np.abs(cate))) < 0.50, "CATE magnitude too large; check model"

        return cate

    except Exception as exc:
        raise RuntimeError(f"fit_s_learner failed: {exc}") from exc