# ========================================
# Test Suite
# ========================================

import numpy as np
import pandas as pd
import pytest


def _make_synthetic_uplift_data(*, n: int = 1000, random_state: int = 42):
    """
    Generate random uplift-style data (no real files).
    Keep this deterministic and small enough to run fast.
    """
    rng = np.random.default_rng(random_state)
    
    channel = rng.choice(
        ["channel_Phone", "channel_Web","channel_Multichannel"],
        size=n,
        p=[1/3, 1/3,1/3],   
    )

    zipcode = rng.choice(
        ["zip_Surburban", "zip_Urban","zip_Rural"],
        size=n,
        p=[1/3, 1/3,1/3],   
    )

    mix = rng.choice(
        ["mens_only", "womens_only","both"],
        size=n,
        p=[0.45, 0.45, 0.10],     # 概率取自原样本中的分布
    )

    X = pd.DataFrame(
        {
            "recency": rng.integers(1, 13, size=n),
            "history": rng.uniform(0.0, 1000.0, size=n),

            # Not one-hot, instead multi-hot
            # 为什么 mens/womens 不像 channel/zip 一样进行互斥 0/1 编码:
            # mens/womens 在该数据集中并不是用户性别标签, 而是历史购买品类标签 (是否购买过男/女装)
            # 允许同时为 1, 但不允许同时为 0
            "mens":((mix == "mens_only") | (mix == "both")).astype(int),
            "womens":((mix == "womens_only") | (mix == "both")).astype(int),

            "newbie": rng.integers(0, 2, size=n),

            # Channel/Zip 的生成:
            # 一共有三种情况: (0,0), (1,0), (0,1), 其中 (0,0) 表示为剩下的第三个channel/zip
            # 但一定不可能出现 (1,1) 
            "channel_Web": (channel == "channel_Web").astype(int),
            "channel_Phone": (channel == "channel_Phone").astype(int),
            "zip_Surburban": (zipcode == "zip_Surburban").astype(int),
            "zip_Urban": (zipcode == "zip_Urban").astype(int),
        }
    )

    assert ((X["mens"] + X["womens"]) >= 1).all(), "X contains (mens,womens) with (0,0) sample"
    assert ((X["channel_Web"] + X["channel_Phone"]) <= 1).all(), "X contains (channel_Web,channel_Phone) with (1,1) sample"
    assert ((X["zip_Surburban"] + X["zip_Urban"]) <= 1).all(), "X contains (zip_Surburban,zip_Urban) with (1,1) sample"

    # 按照实际数据中的 T/C 比例分布以及转化率设定生成数据服从的分布:
    #   T:C = 2:1 -> T 服从 Bernoulli(0.67)
    #   转化率 = 0.009 -> Y 服从 Bernoulli(0.009)
    if n < 2:
        raise ValueError("n must be >= 2")
    
    T = pd.Series(rng.choice([0, 1], size=n, p=[0.33, 0.67]), name="treatment")
    Y = pd.Series(rng.choice([0, 1], size=n, p=[0.991, 0.009]), name="conversion")

    t_arr = T.to_numpy(dtype=int, copy=False)

    # Guard 1: ensure both groups exist (minimal intervention) ---
    treat_pos = np.flatnonzero(t_arr == 1)
    ctrl_pos = np.flatnonzero(t_arr == 0)

    if treat_pos.size == 0:
        # all control -> flip one to treated
        T.iloc[0] = 1
        t_arr = T.to_numpy(dtype=int, copy=False)
        treat_pos = np.flatnonzero(t_arr == 1)
        ctrl_pos = np.flatnonzero(t_arr == 0)
    if ctrl_pos.size == 0:
        # all treated -> flip one to control
        T.iloc[0] = 0
        t_arr = T.to_numpy(dtype=int, copy=False)
        treat_pos = np.flatnonzero(t_arr == 1)
        ctrl_pos = np.flatnonzero(t_arr == 0)

    # Guard 2: ensure at least one positive outcome per group ---
    # pick one index from each group (now guaranteed non-empty)
    treat_idx = int(treat_pos[0])
    ctrl_idx = int(ctrl_pos[0])
    Y.iloc[treat_idx] = 1
    Y.iloc[ctrl_idx] = 1

    # 此处的 ps 是独立随机数, 并不是由协变量 X 产生, 不满足 ps_i ≈ P(T_i=1 | X_i)
    # 目的是为了后续测试 "PS 加权组合公式" 是否实现正确, 而不是测试 "因果识别"
    ps = rng.uniform(0.01, 0.99, size=n)
    return X, T, Y, ps

class TestSLearnerBasicFunctionality:
    def test_returns_numpy_array(self, monkeypatch: pytest.MonkeyPatch):
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=300, random_state=42)

        class _DummyClassifier:
            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                # Use the injected treatment feature to produce non-zero CATE
                # 防止 T 没有正确传入
                t_col = "__treatment_feature__"
                if t_col not in X_in.columns:
                    raise AssertionError("Missing treatment feature column")

                t = X_in[t_col].to_numpy(dtype=int, copy=False)
                p = np.where(t == 1, 0.20, 0.10).astype(float)
                return np.column_stack([1.0 - p, p])

        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            return _DummyClassifier()

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        cate = uplift.fit_s_learner(X, T, Y, n_estimators=10, max_depth=2, random_state=42)
        assert isinstance(cate, np.ndarray)

    def test_output_shape_matches_input(self, monkeypatch: pytest.MonkeyPatch):
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=300, random_state=42)

        class _DummyClassifier:
            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                t = X_in["__treatment_feature__"].to_numpy(dtype=int, copy=False)
                p = np.where(t == 1, 0.20, 0.10).astype(float)
                return np.column_stack([1.0 - p, p])

        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            return _DummyClassifier()

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        cate_in = uplift.fit_s_learner(X, T, Y, n_estimators=10, max_depth=2, random_state=42)
        assert cate_in.shape == (len(X),)

        X_pred = X.copy(deep=True)
        cate_oos = uplift.fit_s_learner(
            X,
            T,
            Y,
            X_pred,
            n_estimators=10,
            max_depth=2,
            random_state=42,
        )
        assert cate_oos.shape == (len(X_pred),)

    def test_cate_no_nan(self, monkeypatch: pytest.MonkeyPatch):
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=300, random_state=42)

        class _DummyClassifier:
            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                t = X_in["__treatment_feature__"].to_numpy(dtype=int, copy=False)
                p = np.where(t == 1, 0.20, 0.10).astype(float)
                return np.column_stack([1.0 - p, p])

        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            return _DummyClassifier()

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        cate = uplift.fit_s_learner(X, T, Y, n_estimators=10, max_depth=2, random_state=42)
        assert np.isfinite(cate).all()

    def test_cate_range_reasonable(self, monkeypatch: pytest.MonkeyPatch):
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=300, random_state=42)

        class _DummyClassifier:
            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                t = X_in["__treatment_feature__"].to_numpy(dtype=int, copy=False)
                # Keep uplift effect in a small, realistic range
                p = np.where(t == 1, 0.20, 0.10).astype(float)
                return np.column_stack([1.0 - p, p])

        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            return _DummyClassifier()

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        cate = uplift.fit_s_learner(X, T, Y, n_estimators=10, max_depth=2, random_state=42)
        assert float(np.max(np.abs(cate))) < 0.50

    def test_scale_pos_weight_applied(self, monkeypatch: pytest.MonkeyPatch):
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=300, random_state=42)

        class _DummyClassifier:
            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                t = X_in["__treatment_feature__"].to_numpy(dtype=int, copy=False)
                p = np.where(t == 1, 0.20, 0.10).astype(float)
                return np.column_stack([1.0 - p, p])

        captured = {"n": 0, "spw": None}

        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            captured["n"] += 1
            captured["spw"] = float(scale_pos_weight)

            # S-learner must augment X with treatment as a feature.
            assert "__treatment_feature__" in X_in.columns
            return _DummyClassifier()

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        _ = uplift.fit_s_learner(X, T, Y, n_estimators=10, max_depth=2, random_state=42)

        assert captured["n"] == 1

        n_pos = int((Y == 1).sum())
        n_neg = int((Y == 0).sum())
        expected_spw = float(n_neg / n_pos)
        assert captured["spw"] == pytest.approx(expected_spw, abs=1e-12)

class TestXLearnerPSWeighting:
    def test_ps_weighting_formula_correctness(self, monkeypatch: pytest.MonkeyPatch):
        """Validate final PS-weighted combination step.

        X-Learner output must satisfy:
          cate = (1-ps) * tau_1 + ps * tau_0

        Strategy: (用 monkeypatch 把 "机器学习" 问题降维成 "代数恒等式检查")
            1. 把 `src.uplift` 内部真正的训练函数 (fit_x_learner) 替换为一个假的确定的版本
            2. 让 tau_1/tau_0 变量成为已知的固定向量
            3. 最后逐个检查输出的 cate 是否等于公式右边的逐元素计算结果
        
        Why monkeypatch: 为什么要跳过训练过程, 这是不是 "作弊",没做到完全测试?
            1. 这是单元测试的正确步骤, 把不确定的训练过程 mock 掉, 专注验证实现的关键不变量 (PS 加权公式)
            2. 对于模型学习训练, 应该另外通过继承测试/离线评估 (Qini/AUUC) 来验证

        怎么做到 "只测组合，不测训练":
        - monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw): 
            - 把真实分类器训练函数替换成假的
            - 假分类器 _DummyClassifier(p) 的 predict_proba 永远输出固定概率 [1-p, p]
            - 确保 fit_x_learner 的 pseudo-outcome 路径能走通但没有随机训练噪声
        - 用 monkeypatch.setattr(uplift, "_fit_regressor", _fake_fit_regressor):
            - 把真实回归器训练替换成假的。
            - 假回归器 _DummyRegressor(pred) 的 predict 永远返回预先指定的向量 tau_1 / tau_0
        
        关键实现细节:
            - clf_calls["n"] / reg_calls["n"] 计数器用来区分“第 1 次 fit 是 model1 / tau1_model, 第 2 次 fit 是 model0 / tau0_model”。
            - 这条 test 的断言是最强的: np.testing.assert_allclose(..., atol=1e-12)，我们希望结果完全按公式实现，不是趋势正确。
        """
        import src.uplift as uplift

        X, T, Y, ps = _make_synthetic_uplift_data(n=1000, random_state=42)
        rng = np.random.default_rng(123)

        # 手动构造 tau_1/tau_0 向量, 如果通过真实训练得到预测向量:
        #   1. 训练需要时间, 导致测试时间变长
        #   2. 预测得到的结果存在随机噪声, 无法做 "严格等式检查" (只能做宽松的统计检查)
        # scale=0.05: 让数值幅度适中, 不至于太大触发对 CATE magnitude 的断言,也不至于全接近 0
        tau_1 = rng.normal(loc=0.0, scale=0.05, size=len(X))
        tau_0 = rng.normal(loc=0.0, scale=0.05, size=len(X))
        
        class _DummyClassifier:
            """
            本质: 假分类器 _DummyClassifier(p) 

            __init__(p): 把正类概率固定成常数 p (比如 0.20 或 0.30)
            predict_proba(X_in): 无论输入什么 X, 永远只返回一个 n × 2 的概率矩阵
                - 第 0 列: P(Y=0) = 1-p
                - 第 1 列: P(Y=1) = p
            """
            def __init__(self, p: float):
                self._p = float(p)

            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                n = int(len(X_in))
                p = np.full(n, self._p, dtype=float)
                return np.column_stack([1.0 - p, p])

        # Variable counter: record how many times `_fake_fit_classifier_with_spw`` is called
        clf_calls = {"n": 0}
        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            clf_calls["n"] += 1
            # 1st call -> model_1, 2nd call -> model_0
            if clf_calls["n"] == 1:
                return _DummyClassifier(0.20)
            if clf_calls["n"] == 2:
                return _DummyClassifier(0.30)
            raise AssertionError("Unexpected number of classifier fits")

        # Replace src.uplift `_fit_classifier_with_spw` with `_fake_fit_classifier_with_spw`
        # 之后所有 `uplift.fit_x_learner` 实际都是调用 `_fake_fit_classifier_with_spw`
        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        # DummyRegressor: 用于模拟回归器的假类
        # 作用: 无视 X, 直接返回预先设定的 tau_1 / tau_0 向量
        class _DummyRegressor:
            # pred: 手动造的 tau_1 / tau_0 向量
            def __init__(self, pred: np.ndarray):
                self._pred = np.asarray(pred, dtype=float).reshape(-1)

            def predict(self, X_in: pd.DataFrame) -> np.ndarray:
                if int(len(X_in)) != int(len(self._pred)):
                    raise AssertionError("Prediction length mismatch")
                return self._pred

        # Variable counter: record how many times `_fake_fit_regressor`` is called
        reg_calls = {"n": 0}

        # 行为: 无视 X, 直接返回预先设定的 tau_1 / tau_0 向量
        # 作用: 模拟第二次回归器的训练 (实际上并没有进行训练)
        def _fake_fit_regressor(
            X_in: pd.DataFrame,
            y_in: np.ndarray,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
        ):
            reg_calls["n"] += 1
            # 1st call -> tau_1_model, 2nd call -> tau_0_model
            if reg_calls["n"] == 1:
                return _DummyRegressor(tau_1)
            if reg_calls["n"] == 2:
                return _DummyRegressor(tau_0)
            raise AssertionError("Unexpected number of regressor fits")

        monkeypatch.setattr(uplift, "_fit_regressor", _fake_fit_regressor)

        """
        Workflow:
            1. 训练第一阶段 outcome model, 得到可控 (利用 monkeyptach 控制) 的 `mu_1` / `mu_0`
            2. 生成伪残差 D_1/D_0 (这步仍会执行, 但是具体数值我们并不关心)
            3. 训练第二阶段 outcome model: tau_1_model/tau_0_model
                - 被 fake 函数取代, 所以
                - tau_1_model.predict(X_out) == tau_1
                - tau_0_model.predict(X_out) == tau_0
            4. 最后计算 CATE (该 test 函数的目的)
        """
        cate = uplift.fit_x_learner(
            X,
            T,
            Y,
            ps,
            n_estimators=10,
            max_depth=2,
            random_state=42,
        )

        # Expected output (Validating the formula)
        expected = (1.0 - ps) * tau_1 + ps * tau_0
        np.testing.assert_allclose(cate, expected, rtol=0.0, atol=1e-12)

    def test_extreme_ps_near_zero(self, monkeypatch: pytest.MonkeyPatch):
        """When PS is near 0, X-learner should mostly use tau_1(x).

        Validation goal:
            - 当 ps ≈ 0 时, 公式变成: cate ≈ 1*tau_1 + 0*tau_0, 所以输出应该“几乎完全跟着 tau_1 走”。
            - e(x)≈0 => tau_hat(x)≈tau1_hat(x)

        Why correlation: 为什么用相关系数 corr, 而不是像前面一样用 allclose ?
            - cate = 0.99 * tau_1 + 0.01 * tau_0 (PS = 0.01)
            - 因此理论上 cate 并不是完全等于 tau_1 (还混杂了 1% 的tau_0), 但是两者的排序/方向应该高度一致
            - 用 corr(cate, tau_1) > 0.95 是在测“排序/方向性一致”，对尺度微扰更宽容（也更贴近 uplift 的排序目标）

        flaky 风险:
            - 相关系数阈值 (0.95) 本质是统计量，理论上可能受随机抽样影响
            - 数据量 n = 1000 且 tau 独立正态，风险很低
            - 如果需要可以通过 (增大 n / 固定随机种子 / 避免 tau 高相关) 来更进一步降低 flaky
        """
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=1000, random_state=42)
        ps = np.full(len(X), 0.01, dtype=float)

        rng = np.random.default_rng(7)
        tau_1 = rng.normal(loc=0.0, scale=0.05, size=len(X))
        tau_0 = rng.normal(loc=0.0, scale=0.05, size=len(X))

        class _DummyClassifier:
            def __init__(self, p: float):
                self._p = float(p)

            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                n = int(len(X_in))
                p = np.full(n, self._p, dtype=float)
                return np.column_stack([1.0 - p, p])

        clf_calls = {"n": 0}
        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            clf_calls["n"] += 1
            if clf_calls["n"] == 1:
                return _DummyClassifier(0.20)
            if clf_calls["n"] == 2:
                return _DummyClassifier(0.30)
            raise AssertionError("Unexpected number of classifier fits")

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        class _DummyRegressor:
            def __init__(self, pred: np.ndarray):
                self._pred = np.asarray(pred, dtype=float).reshape(-1)

            def predict(self, X_in: pd.DataFrame) -> np.ndarray:
                if int(len(X_in)) != int(len(self._pred)):
                    raise AssertionError("Prediction length mismatch")
                return self._pred

        reg_calls = {"n": 0}
        def _fake_fit_regressor(
            X_in: pd.DataFrame,
            y_in: np.ndarray,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
        ):
            reg_calls["n"] += 1
            if reg_calls["n"] == 1:
                return _DummyRegressor(tau_1)
            if reg_calls["n"] == 2:
                return _DummyRegressor(tau_0)
            raise AssertionError("Unexpected number of regressor fits")

        monkeypatch.setattr(uplift, "_fit_regressor", _fake_fit_regressor)

        cate = uplift.fit_x_learner(
            X,
            T,
            Y,
            ps,
            n_estimators=10,
            max_depth=2,
            random_state=42,
        )

        corr = float(np.corrcoef(cate, tau_1)[0, 1])
        assert np.isfinite(corr)
        assert corr > 0.95

    def test_extreme_ps_near_one(self, monkeypatch: pytest.MonkeyPatch):
        """
        When PS is near 1, X-learner should mostly use tau_0(x)
        Expectation: corr(cate, tau_0_prediction) > 0.95
        """
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=1000, random_state=42)
        ps = np.full(len(X), 0.99, dtype=float)

        rng = np.random.default_rng(8)
        tau_1 = rng.normal(loc=0.0, scale=0.05, size=len(X))
        tau_0 = rng.normal(loc=0.0, scale=0.05, size=len(X))

        class _DummyClassifier:
            def __init__(self, p: float):
                self._p = float(p)

            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                n = int(len(X_in))
                p = np.full(n, self._p, dtype=float)
                return np.column_stack([1.0 - p, p])

        clf_calls = {"n": 0}
        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            clf_calls["n"] += 1
            if clf_calls["n"] == 1:
                return _DummyClassifier(0.20)
            if clf_calls["n"] == 2:
                return _DummyClassifier(0.30)
            raise AssertionError("Unexpected number of classifier fits")

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        class _DummyRegressor:
            def __init__(self, pred: np.ndarray):
                self._pred = np.asarray(pred, dtype=float).reshape(-1)

            def predict(self, X_in: pd.DataFrame) -> np.ndarray:
                if int(len(X_in)) != int(len(self._pred)):
                    raise AssertionError("Prediction length mismatch")
                return self._pred

        reg_calls = {"n": 0}
        def _fake_fit_regressor(
            X_in: pd.DataFrame,
            y_in: np.ndarray,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
        ):
            reg_calls["n"] += 1
            if reg_calls["n"] == 1:
                return _DummyRegressor(tau_1)
            if reg_calls["n"] == 2:
                return _DummyRegressor(tau_0)
            raise AssertionError("Unexpected number of regressor fits")

        monkeypatch.setattr(uplift, "_fit_regressor", _fake_fit_regressor)

        cate = uplift.fit_x_learner(
            X,
            T,
            Y,
            ps,
            n_estimators=10,
            max_depth=2,
            random_state=42,
        )

        corr = float(np.corrcoef(cate, tau_0)[0, 1])
        assert np.isfinite(corr)
        assert corr > 0.95

    def test_uniform_ps_equal_weight(self, monkeypatch: pytest.MonkeyPatch):
        """
        When PS is uniform 0.5, X-learner should average tau_1 and tau_0

        Validation goal:
            - 当 ps = 0.5 常数时, 公式应该退化成简单平均:
            - e(x) = 0.5 => tau_hat(x) = 0.5 * tau1_hat(x) + 0.5 * tau0_hat(x)
            - 这是一个 "对称性检查", 如果把权重写反或漏了, 就会直接报错
        """
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=1000, random_state=42)
        ps = np.full(len(X), 0.50, dtype=float)

        rng = np.random.default_rng(9)
        tau_1 = rng.normal(loc=0.0, scale=0.05, size=len(X))
        tau_0 = rng.normal(loc=0.0, scale=0.05, size=len(X))

        class _DummyClassifier:
            def __init__(self, p: float):
                self._p = float(p)

            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                n = int(len(X_in))
                p = np.full(n, self._p, dtype=float)
                return np.column_stack([1.0 - p, p])

        clf_calls = {"n": 0}
        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            clf_calls["n"] += 1
            if clf_calls["n"] == 1:
                return _DummyClassifier(0.20)
            if clf_calls["n"] == 2:
                return _DummyClassifier(0.30)
            raise AssertionError("Unexpected number of classifier fits")

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        class _DummyRegressor:
            def __init__(self, pred: np.ndarray):
                self._pred = np.asarray(pred, dtype=float).reshape(-1)

            def predict(self, X_in: pd.DataFrame) -> np.ndarray:
                if int(len(X_in)) != int(len(self._pred)):
                    raise AssertionError("Prediction length mismatch")
                return self._pred

        reg_calls = {"n": 0}
        def _fake_fit_regressor(
            X_in: pd.DataFrame,
            y_in: np.ndarray,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
        ):
            reg_calls["n"] += 1
            if reg_calls["n"] == 1:
                return _DummyRegressor(tau_1)
            if reg_calls["n"] == 2:
                return _DummyRegressor(tau_0)
            raise AssertionError("Unexpected number of regressor fits")

        monkeypatch.setattr(uplift, "_fit_regressor", _fake_fit_regressor)

        cate = uplift.fit_x_learner(
            X,
            T,
            Y,
            ps,
            n_estimators=10,
            max_depth=2,
            random_state=42,
        )

        expected = 0.5 * tau_1 + 0.5 * tau_0
        np.testing.assert_allclose(cate, expected, rtol=0.0, atol=1e-12)

class TestQiniBasicFunctionality:
    """
    Validation goal:
        1) 这类验证不是在追求 "数据完全对齐"
        2) 而是验证 `src/uplift.py::compute_qini`的一组不可被打破的性质
            - 输出结构对、边界点对、随机排序不应有提升
            - 完美排序必须优于随机基线
            - 曲线端点必须收敛到同一个总 uplift

    Overall Workflow: "从 API 合同 → 几何边界 → 业务语义" 的测试分层
        1) 先验证 compute_qini 的输出结构 (dict keys/types/长度)
        2) 再验证曲线边界点 (x 从 0 到 1, 起点三条线都是 0)
        3) 然后做两类行为校验：
            - 随机排序: Qini coefficient 期望接近 0
            - 完美排序: Qini coefficient 必须为正且优于反向排序，并且在中间点超过随机线、在终点收敛
    """
    def test_returns_dict_with_required_keys(self):
        """
        Validation goal (schema test): Output type/keys/length Validation
            1) `compute_qini` 返回值必须是 dict
            2) 必须包含这些 key : `qini_x`, `qini_y`, `random_y`, `auuc`, `random_auuc`, `qini_coefficient`
            3) 并且类型/长度要合理:
                - `qini_x`, `qini_y`, `random_y` 必须是 list
                - `len(...) == 21`
                - 所有元素都是 finite, `auuc / random_auuc / qini_coefficient` 必须是 float
        """
        import src.uplift as uplift

        n = 200
        cate = np.linspace(-1.0, 1.0, num=n, dtype=float)
        T = pd.Series(np.tile([1, 0], n // 2).astype(int))
        Y = pd.Series(np.zeros(n, dtype=int))

        # Type validation
        out = uplift.compute_qini(cate=cate, T=T, Y=Y, n_bins=20)
        assert isinstance(out, dict)

        # Key validation
        required = {
            "qini_x",
            "qini_y",
            "random_y",
            "auuc",
            "random_auuc",
            "qini_coefficient",
        }
        assert required.issubset(out.keys())

        # Key columns type/length validation
        assert isinstance(out["qini_x"], list)
        assert isinstance(out["qini_y"], list)
        assert isinstance(out["random_y"], list)
        assert len(out["qini_x"]) == 21
        assert len(out["qini_y"]) == 21
        assert len(out["random_y"]) == 21

        assert np.isfinite(np.asarray(out["qini_x"], dtype=float)).all()
        assert np.isfinite(np.asarray(out["qini_y"], dtype=float)).all()
        assert np.isfinite(np.asarray(out["random_y"], dtype=float)).all()
        assert isinstance(out["auuc"], float)
        assert isinstance(out["random_auuc"], float)
        assert isinstance(out["qini_coefficient"], float)

    def test_qini_x_starts_at_zero(self):
        """
        Validation goal:
            - `qini_x[0] == 0.0`
            - `qini_y[0] == 0.0`
            - `random_y[0] == 0.0`
        
        Why:
            - Qini 曲线起点必须是 0, 否则就是实现里 bin 边界/初始化错了
            - 这属于几何边界不变量
        """
        import src.uplift as uplift

        n = 200
        cate = np.linspace(-1.0, 1.0, num=n, dtype=float)
        T = pd.Series(np.tile([1, 0], n // 2).astype(int))
        Y = pd.Series(np.zeros(n, dtype=int))

        out = uplift.compute_qini(cate=cate, T=T, Y=Y, n_bins=20)

        assert out["qini_x"][0] == 0.0
        assert out["qini_y"][0] == 0.0
        assert out["random_y"][0] == 0.0

    def test_qini_x_ends_at_one(self):
        """
        Validation goal:
            - `qini_x[-1] == 1.0`
        
        Why:
            - targeting fraction 的终点必须覆盖全量人群 (100%)
            - 否则说明 bin 边界计算 (比如 rounding、linspace 边界、clip) 出现 off-by-one bug
            - 这属于几何边界不变量
        """
        import src.uplift as uplift

        n = 200
        cate = np.linspace(-1.0, 1.0, num=n, dtype=float)
        T = pd.Series(np.tile([1, 0], n // 2).astype(int))
        Y = pd.Series(np.zeros(n, dtype=int))

        out = uplift.compute_qini(cate=cate, T=T, Y=Y, n_bins=20)

        assert out["qini_x"][-1] == 1.0

    def test_random_cate_qini_near_random_line(self):
        """
        Workflow:
            1) 用 `_make_synthetic_uplift_data(n=5000)` 生成 T/Y (保证有 treated/control、有正例)
            2) 生成 200 次不同的随机 cate (少数次随机容易发生 flaky)
            3) 取 qini_coefficient 的均值 mean_coef
            4) 断言 abs(mean_coef) < 0.5

        Why:
            - 如果 cate 是随机 (与真实 uplift 无关) 的, 那么其没有排序能力
            - 此时理论上 Qini Coefficient 应接近 0 (与 random baseline 相近)
        """
        import src.uplift as uplift

        _X, T, Y, _ps = _make_synthetic_uplift_data(n=5000, random_state=42)
        rng = np.random.default_rng(42)

        coefs = []
        for _ in range(200):
            cate = rng.uniform(low=-1.0, high=1.0, size=len(T))
            out = uplift.compute_qini(cate=cate, T=T, Y=Y, n_bins=20)
            coefs.append(float(out["qini_coefficient"]))

        mean_coef = float(np.mean(coefs))
        assert abs(mean_coef) < 0.2

    def test_perfect_cate_qini_above_random(self):
        """
        Validation goal: Perfect uplift ranking should beat the random baseline

        Workflow:
            1) 构造一个 "可证明的完美 uplift 排序" 数据：
                - 高 uplift 段: treated 必转化、control 不转化
                - 低 uplift 段: 都不转化
            2) 把 cate 设成段的 indicator (高段=1, 低段=0), 这就是 oracle ranking
            3) 再打乱行顺序 (permute), 确保 compute_qini 必须 "真正按 cate 排序" 才能得到好结果
            4) 断言包含 4 个层次：
                - out["qini_coefficient"] > 0.0:
                    整体优于随机

                - out["qini_coefficient"] > out_bad["qini_coefficient"]:
                    反向排序更差 (sanity check, 防止 sort 方向写反)

                - out["qini_y"][5] > out["random_y"][5]:
                    在某个中间分位点 (第 5 个 bin) oracle 曲线要在随机线之上

                - out["qini_y"][-1] == approx(out["random_y"][-1]):
                    端点收敛 (全量投放时，排序不重要，累计 uplift 和随机基线终点应该一致)
        """
        import src.uplift as uplift

        n_high = 500
        n_low = 1500
        n = n_high + n_low
        n_bins = 20

        # Oracle ranking: high segment should be targeted first.
        cate = np.concatenate([np.ones(n_high, dtype=float), np.zeros(n_low, dtype=float)])

        # Alternate T to guarantee both groups appear in every prefix of sufficient size.
        t = np.tile([1, 0], n // 2).astype(int)
        T = pd.Series(t)

        # Outcomes: only treated in the high segment converts.
        y = np.zeros(n, dtype=int)
        y[:n_high] = t[:n_high]
        Y = pd.Series(y)

        # Shuffle row order so compute_qini must actually sort by `cate`.
        perm = np.random.default_rng(0).permutation(n)
        cate = cate[perm]
        T = T.iloc[perm].reset_index(drop=True)
        Y = Y.iloc[perm].reset_index(drop=True)

        out = uplift.compute_qini(cate=cate, T=T, Y=Y, n_bins=n_bins)

        # Reversing the ranking should be worse (or at least not better).
        out_bad = uplift.compute_qini(cate=-cate, T=T, Y=Y, n_bins=n_bins)

        # Total uplift: treated mean = 0.25, control mean = 0 -> total_uplift = 0.25 * N_C = 250
        assert out["qini_coefficient"] > 0.0
        assert out["qini_coefficient"] > out_bad["qini_coefficient"]
        assert out["qini_y"][5] > out["random_y"][5]
        assert out["qini_y"][-1] == pytest.approx(out["random_y"][-1], abs=1e-12)

class TestInputValidation:
    def test_none_input_raises_error(self):
        """
        Validation Goal:
            - 传入 X 为 None 给 fit_x_learner 时, 必须抛出错误
            - 传入 T 为 None 给 compute_qini 时, 必须抛出错误
            - 传入 Y 为 None 给 compute_qini 时, 必须抛出错误

        Attention: 
            - learner会把 validation error 包装成 RuntimeError
            - 因此这里的断言是 RuntimeError 且 message 包含 "fit_x_learner failed: ..."
        """
        import src.uplift as uplift

        X, T, Y, ps = _make_synthetic_uplift_data(n=100, random_state=42)

        # Learners wrap validation errors into RuntimeError.
        with pytest.raises(RuntimeError, match=r"fit_x_learner failed: X cannot be None"):
            uplift.fit_x_learner(
                None,  # type: ignore[arg-type]
                T,
                Y,
                ps,
                n_estimators=10,
                max_depth=2,
                random_state=42,
            )

        # compute_qini also wraps
        # T/Y = None should always error with deterministic messages.
        cate = np.zeros(len(T), dtype=float)

        with pytest.raises(RuntimeError, match=r"compute_qini failed: T cannot be None"):
            uplift.compute_qini(cate=cate, T=None, Y=Y, n_bins=20)  # type: ignore[arg-type]

        with pytest.raises(RuntimeError, match=r"compute_qini failed: Y cannot be None"):
            uplift.compute_qini(cate=cate, T=T, Y=None, n_bins=20)  # type: ignore[arg-type]

    def test_empty_dataframe_raises_error(self):
        """
        Validation Goal:
            - `fit_s_learner` 遇到空 X 必须报错 "X cannot be empty"
        """
        import src.uplift as uplift

        X_empty = pd.DataFrame()
        T_empty = pd.Series([], dtype=int)
        Y_empty = pd.Series([], dtype=int)

        with pytest.raises(RuntimeError, match=r"fit_s_learner failed: X cannot be empty"):
            uplift.fit_s_learner(
                X_empty,
                T_empty,
                Y_empty,
                n_estimators=10,
                max_depth=2,
                random_state=42,
            )

    def test_non_binary_treatment_raises_error(self):
        """
        Validation Goal:
            - Indicator 列 (T) 必须为二元组合
            - 出现非法取值 (比如 2) 必须报错 "T must be binary (0/1)"
        """
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=100, random_state=42)
        T_bad = T.copy()
        T_bad.iloc[0] = 2

        with pytest.raises(RuntimeError, match=r"fit_t_learner failed: T must be binary \(0/1\)"):
            uplift.fit_t_learner(
                X,
                T_bad,
                Y,
                n_estimators=10,
                max_depth=2,
                random_state=42,
            )

    def test_length_mismatch_raises_error(self):
        """
        Validation Goal:
            - X, Y, T 三列必须等长
            - 这里故意让 T_short 少一行, 必须精准报错
        """
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=10, random_state=42)

        # Mismatch between X and T should be caught in the shared validator.
        T_short = T.iloc[:-1].reset_index(drop=True)
        with pytest.raises(
            RuntimeError,
            match=r"fit_s_learner failed: Length mismatch: len\(X\)=10, len\(T\)=9, len\(Y\)=10",
        ):
            uplift.fit_s_learner(
                X,
                T_short,
                Y,
                n_estimators=10,
                max_depth=2,
                random_state=42,
            )

    def test_nan_in_features_raises_error(self):
        """
        Validation Goal:
            - 特征列里必须不包含 NaN, 否则报错
        """
        import src.uplift as uplift

        X, T, Y, ps = _make_synthetic_uplift_data(n=100, random_state=42)
        X_nan = X.copy()
        X_nan.iloc[0, 0] = np.nan

        with pytest.raises(RuntimeError, match=r"fit_x_learner failed: X contains NaN values"):
            uplift.fit_x_learner(
                X_nan,
                T,
                Y,
                ps,
                n_estimators=10,
                max_depth=2,
                random_state=42,
            )

class TestImmutability:
    """
    Validation Goal: 测 "函数纯度/引用透明度"
        "fit_*_learner()" 作为建模函数, 必须把输入当作只读, 不允许修改 X/T/Y/ps

    Workflow:
        1) 该类下有 3 个 test 函数, 分别对应测试 3 个 learner:
            - test_s_learner_does_not_mutate_input
            - test_t_learner_does_not_mutate_input
            - test_x_learner_does_not_mutate_input
        2) 每个 test 都是同样的验证结构
            - 用 _make_synthetic_uplift_data 创建一个合成数据集 (含 X/T/Y/ps)
            - deep copy 备份: X_before/T_before/Y_before/(ps_before)
            - 用 monkeypatch 把内部训练函数替换成 dummy
            - 调用对应的 uplift.fit_*_learner(...)
            - 用 pd.testing.assert_*_equal / np.testing.assert_array_equal 断言输入是否未被修改

    Attention:
        1) 该测试目的不是测模型效果, 而是测 "工程契约": 输入不可变
        2) monkeypatch 是为了把 ML 不确定性剥离:
            - 真实 ML 会引入随机性
            - 真实训练会慢, 具有 flaky 风险, 还会让单纯的 "输入不变" 测试变成 integration 测试
            - 测试目的是 "有没有副作用 (更改输入)", 不是评判模型好坏
    """
    def test_s_learner_does_not_mutate_input(self, monkeypatch: pytest.MonkeyPatch):
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=300, random_state=42)

        X_before = X.copy(deep=True)
        T_before = T.copy(deep=True)
        Y_before = Y.copy(deep=True)

        class _DummyClassifier:
            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                n = int(len(X_in))
                p = np.full(n, 0.123, dtype=float)      # p always 0.123 (CONST)
                return np.column_stack([1.0 - p, p])

        clf_calls = {"n": 0}
        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            clf_calls["n"] += 1
            return _DummyClassifier()

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        _ = uplift.fit_s_learner(X, T, Y, n_estimators=10, max_depth=2, random_state=42)

        # Only train one model, check that it was called once.
        assert clf_calls["n"] == 1

        pd.testing.assert_frame_equal(X, X_before, check_dtype=True)
        pd.testing.assert_series_equal(T, T_before, check_dtype=True)
        pd.testing.assert_series_equal(Y, Y_before, check_dtype=True)
        assert "__treatment_feature__" not in X.columns

    def test_t_learner_does_not_mutate_input(self, monkeypatch: pytest.MonkeyPatch):
        import src.uplift as uplift

        X, T, Y, _ps = _make_synthetic_uplift_data(n=300, random_state=42)

        X_before = X.copy(deep=True)
        T_before = T.copy(deep=True)
        Y_before = Y.copy(deep=True)

        class _DummyClassifier:
            def __init__(self, p: float):
                self._p = float(p)

            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                n = int(len(X_in))
                p = np.full(n, self._p, dtype=float)
                return np.column_stack([1.0 - p, p])

        clf_calls = {"n": 0}
        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            clf_calls["n"] += 1
            # model_1 then model_0
            if clf_calls["n"] == 1:
                return _DummyClassifier(0.21)
            if clf_calls["n"] == 2:
                return _DummyClassifier(0.19)
            raise AssertionError("Unexpected number of classifier fits")

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        _ = uplift.fit_t_learner(X, T, Y, n_estimators=10, max_depth=2, random_state=42)

        # Train two models, check that it was called twice.
        assert clf_calls["n"] == 2

        pd.testing.assert_frame_equal(X, X_before, check_dtype=True)
        pd.testing.assert_series_equal(T, T_before, check_dtype=True)
        pd.testing.assert_series_equal(Y, Y_before, check_dtype=True)

    def test_x_learner_does_not_mutate_input(self, monkeypatch: pytest.MonkeyPatch):
        import src.uplift as uplift

        X, T, Y, ps = _make_synthetic_uplift_data(n=300, random_state=42)
        ps = ps.copy()

        # If X-learner ever clips PS in-place, this will catch it.
        ps[0] = 0.0
        ps[1] = 1.0

        X_before = X.copy(deep=True)
        T_before = T.copy(deep=True)
        Y_before = Y.copy(deep=True)
        ps_before = ps.copy()

        # Stage 1: dummy classifier
        class _DummyClassifier:
            def __init__(self, p: float):
                self._p = float(p)

            def predict_proba(self, X_in: pd.DataFrame) -> np.ndarray:
                n = int(len(X_in))
                p = np.full(n, self._p, dtype=float)
                return np.column_stack([1.0 - p, p])

        clf_calls = {"n": 0}
        def _fake_fit_classifier_with_spw(
            X_in: pd.DataFrame,
            y_in: pd.Series,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
            scale_pos_weight: float,
        ):
            clf_calls["n"] += 1
            # outcome model_1 then model_0
            if clf_calls["n"] == 1:
                return _DummyClassifier(0.22)
            if clf_calls["n"] == 2:
                return _DummyClassifier(0.18)
            raise AssertionError("Unexpected number of classifier fits")

        monkeypatch.setattr(uplift, "_fit_classifier_with_spw", _fake_fit_classifier_with_spw)

        # Stage 2: dummy regressor
        class _DummyRegressor:
            def predict(self, X_in: pd.DataFrame) -> np.ndarray:
                return np.zeros(int(len(X_in)), dtype=float)

        reg_calls = {"n": 0}
        def _fake_fit_regressor(
            X_in: pd.DataFrame,
            y_in: np.ndarray,
            *,
            n_estimators: int,
            max_depth: int,
            random_state: int,
        ):
            reg_calls["n"] += 1
            if reg_calls["n"] > 2:
                raise AssertionError("Unexpected number of regressor fits")
            return _DummyRegressor()

        monkeypatch.setattr(uplift, "_fit_regressor", _fake_fit_regressor)

        _ = uplift.fit_x_learner(X, T, Y, ps, n_estimators=10, max_depth=2, random_state=42)

        assert clf_calls["n"] == 2
        assert reg_calls["n"] == 2

        pd.testing.assert_frame_equal(X, X_before, check_dtype=True)
        pd.testing.assert_series_equal(T, T_before, check_dtype=True)
        pd.testing.assert_series_equal(Y, Y_before, check_dtype=True)
        np.testing.assert_array_equal(ps, ps_before)



