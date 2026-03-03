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

    

