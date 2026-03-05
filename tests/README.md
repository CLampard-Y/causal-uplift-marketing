# Tests

Fast, deterministic `pytest` unit tests for core uplift utilities (mainly `src/uplift.py`).

这里的测试专注于“工程合同 + 高风险不变量”：用合成数据 + `monkeypatch` 把训练过程替换成确定性组件，从而在重构时快速发现排序方向、权重公式、输入校验、以及副作用等回归。

Non-goals: these unit tests do not prove causal identification or business lift.

注意：这些单元测试不负责证明“因果识别成立/业务效果达标”，只负责把实现层的关键不变量与工程合同变成可回归门禁。

## Run

Run from repo root.

注意：`pytest` 是开发依赖；若环境未安装，请先执行：
`python -m pip install pytest`

```bash
# Run all unit tests
python -m pytest -q

# Run uplift tests only
python -m pytest -q tests/test_uplift.py

# Run a single test class (pattern)
python -m pytest -q tests/test_uplift.py -k "TestXLearnerBasicFunctionality"

# Common interview-focused entry points
python -m pytest -q tests/test_uplift.py -k "TestSLearnerBasicFunctionality"
python -m pytest -q tests/test_uplift.py -k "TestTLearnerBasicFunctionality"
python -m pytest -q tests/test_uplift.py -k "TestXLearnerBasicFunctionality"
python -m pytest -q tests/test_uplift.py -k "TestXLearnerPSWeighting"
python -m pytest -q tests/test_uplift.py -k "TestQiniBasicFunctionality"
python -m pytest -q tests/test_uplift.py -k "TestInputValidation"
python -m pytest -q tests/test_uplift.py -k "TestImmutability"
```

## Coverage Map

`tests/test_uplift.py` (data-free, deterministic)

| Test class / helper | What is asserted (only what the tests actually check) | 中文要点 |
|---|---|---|
| `_make_synthetic_uplift_data` | deterministic synthetic `X/T/Y/ps`; ensures both treated/control exist and each group has a positive outcome | 合成数据工厂；保证 treated/control 都存在且各自有正例，避免除零与空子集 |
| `TestSLearnerBasicFunctionality` | `fit_s_learner` returns `np.ndarray`; shape matches `X`/`X_pred`; all-finite; magnitude sanity bound; passes `scale_pos_weight = n_neg/n_pos`; injects `__treatment_feature__` into model input | S-learner 工程合同：输出稳定 + 类别不平衡权重（SPW）传参正确；treatment 作为特征注入模型输入 |
| `TestTLearnerBasicFunctionality` | `fit_t_learner` returns float `np.ndarray`; shape matches `X`/`X_pred`; all-finite; fits two group models on the correct row subsets; per-group `scale_pos_weight`; `cate = p_treated - p_control` under constant dummy models | 两模型两子集：treated/control 真分开拟合；SPW 分组计算；差分方向固定为 `p_treated - p_control` |
| `TestXLearnerBasicFunctionality` | `fit_x_learner` returns float `np.ndarray`; shape matches `X` and also matches `X_pred` when called with `X_pred` + same-length `ps_pred`; all-finite; output matches the final combination formula using `np.clip(ps, 0.01, 0.99)`; pseudo-outcome direction for cross-estimation (`D1 = Y1 - mu0`, `D0 = mu1 - Y0`) | X-learner 连线不变量：`X_pred` 对齐分支可跑通；PS 截断参与融合；交叉伪残差方向（D1/D0）不写反 |
| `TestXLearnerPSWeighting` | final combination formula `cate = (1-ps) * tau_1 + ps * tau_0`; extreme `ps` (0.01/0.99) correlation sanity checks; symmetry check for uniform `ps=0.5` | 只测融合代数：权重公式不允许写错；极端 PS 排序 sanity；`ps=0.5` 必须完全对称 |
| `TestQiniBasicFunctionality` | `compute_qini` returns required keys; `qini_x/qini_y/random_y` lengths (`n_bins=20 -> 21`); boundary points (`x` starts at 0 and ends at 1; curves start at 0); random `cate` has near-zero mean `qini_coefficient` (Monte Carlo); oracle ranking beats random and reversed ranking; endpoint convergence `qini_y[-1] == random_y[-1]` | Qini 几何/语义合同：输出结构与边界点正确；随机排序接近 0；oracle 排序优于随机/反向；端点与随机基线收敛 |
| `TestInputValidation` | learners/metrics wrap validation errors as `RuntimeError` with stable, matchable messages; `None` inputs; empty `X`; non-binary `T`; length mismatch; `NaN` in `X` | 输入校验门禁：统一 `RuntimeError` 前缀便于上层捕获；覆盖 None/空数据/非二元 treatment/长度不齐/NaN |
| `TestImmutability` | `fit_s_learner/fit_t_learner/fit_x_learner` do not mutate `X/T/Y/ps` in-place; S-learner does not leave `__treatment_feature__` in `X` | 无副作用合同：不原地修改输入；S-learner 不残留临时列；防 in-place PS clip 这种隐蔽脏写 |

## Shared Contracts

These are the recurring "API safety rails" you will see across classes.

为了减少重复描述，这里把各类测试里反复出现的断言集中列出；每个 `Test*` 小节只补充“额外的、该类特有的断言”。

- Return type: learners 返回 `np.ndarray` (而不是 `pd.Series`或 `list`)
- Output shape: 当提供时 `X_pred` , 输出长度要和 `len(X_pred)` 对齐; 否则就和 `len(X)` 对齐
- Numeric stability: 返回的 CATE 数组必须有界(`np.isfinite(...).all()`)

## TestSLearnerBasicFunctionality

Validates `fit_s_learner` contracts via a dummy classifier.

这组测试的重点是 S-learner 的“把 treatment 当特征”这一工程实现是否被破坏，以及类别不平衡权重是否按约定传入内部训练 helper。

- Magnitude sanity: `max(abs(cate)) < 0.50`
- Class imbalance handling: asserts `scale_pos_weight == n_neg / n_pos` is passed into `src.uplift._fit_classifier_with_spw`
- Treatment feature injection: dummy `predict_proba` asserts `__treatment_feature__` exists in the model input

## TestTLearnerBasicFunctionality

Validates `fit_t_learner` contracts and "two models, two subsets" wiring.

这组测试保护 T-learner 的 treated/control 两套模型必须真的在各自子样本上训练，并且差分方向不被改坏（`p_treated - p_control`）。

- Float dtype: asserts returned CATE is floating (`np.issubdtype(cate.dtype, np.floating)`)
- Independent group fitting: records which row indices are passed into each `_fit_classifier_with_spw` call
- Per-group `scale_pos_weight`: asserts SPW is computed separately for treated vs control subsets
- CATE definition: constant dummy probabilities imply constant `cate` with exact `allclose`

## TestXLearnerBasicFunctionality

Validates `fit_x_learner` contracts plus X-learner-specific invariants.

这组测试的核心是 X-learner 的连线正确性：走通 `X_pred` 分支并保证输出对齐、PS 截断在融合公式里生效、以及 cross-estimation 伪残差的符号方向。

- Float dtype: asserts returned CATE is floating
- `X_pred` path: when called with `X_pred` (and a same-length `ps_pred`), output shape matches `len(X_pred)`
- PS clipping in final weighting: uses out-of-range `ps` and asserts the output matches the formula with `np.clip(ps, 0.01, 0.99)`
- Cross-estimation pseudo-outcomes: asserts the tau-stage regressor receives `D1 = Y1 - mu0` and `D0 = mu1 - Y0`

## TestXLearnerPSWeighting

Validates the final PS-weighted combination formula (without relying on stochastic training).

这组测试把训练过程 mock 掉，只验证“融合层的代数公式”以及几个极端值/对称性的 sanity check，避免权重写反、漏乘、或向量对齐错误。

- Formula correctness (strict): `cate == (1-ps) * tau_1 + ps * tau_0` with `allclose(..., atol=1e-12)`
- Extreme PS sanity: `ps=0.01` implies strong rank alignment with `tau_1` (correlation > 0.95); `ps=0.99` aligns with `tau_0`
- Symmetry sanity: uniform `ps=0.5` implies exact average `0.5*tau_1 + 0.5*tau_0`

## TestQiniBasicFunctionality

Validates `compute_qini` output contracts and geometric/semantic invariants.

这组测试不追逐某个固定数值结果，而是测试一组“实现必须满足”的性质：输出结构、边界点、随机排序应接近随机基线、完美排序应优于随机并且端点收敛。

- Output schema: required keys exist; list lengths match `n_bins=20 -> 21`; list values are finite
- Boundary invariants: `qini_x[0]==0`, `qini_y[0]==0`, `random_y[0]==0`, and `qini_x[-1]==1`
- Random ranking baseline: Monte Carlo (`n=5000`, repeats=200) yields `abs(mean(qini_coefficient)) < 0.2`
- Oracle ranking: `qini_coefficient > 0` and beats reversed ranking; a mid-bin point is above random; endpoint converges to random

## TestInputValidation

Validates fail-fast input checks and the public error contract.

这组测试把“输入不合法”的行为固定为可匹配的异常消息：不仅要抛 `RuntimeError`，还要保证 message 前缀稳定（例如 `fit_x_learner failed:` / `compute_qini failed:`），方便上层统一捕获与定位。

- `fit_x_learner`: `X is None` and `X contains NaN values`
- `fit_s_learner`: empty `X`; length mismatch among `X/T/Y`
- `fit_t_learner`: non-binary treatment values
- `compute_qini`: `T is None` and `Y is None`

## TestImmutability

Ensures learners treat inputs as read-only.

这组测试专门防“隐式副作用”：断言 `fit_*_learner` 不会修改传入的 `X/T/Y/ps`（包括 dtype/值），并且 S-learner 不会把临时列残留在原始 `X` 上。

- `fit_s_learner`: `X/T/Y` unchanged; `__treatment_feature__` not left behind
- `fit_t_learner`: `X/T/Y` unchanged
- `fit_x_learner`: `X/T/Y/ps` unchanged; guards against in-place PS clipping

## Conventions

- Synthetic only (no local dataset dependency)
- Deterministic (fixed random seeds + monkeypatch)
- Prefer invariants/contracts over "model quality" metrics to avoid flaky tests

## Flakiness

flaky test 指 "同一份代码，多跑几次，有时过有时不过"。常见来源是随机性、阈值型统计断言（例如相关系数阈值）、以及环境差异。
这套测试通过固定随机种子、使用 `monkeypatch`、以及在需要时用 Monte Carlo 平均来降噪，来尽量降低 flaky 风险。
