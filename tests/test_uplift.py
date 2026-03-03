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

