#!/usr/bin/env python3
"""
gen_vectors.py — 生成确定性测试向量（固定种子）

三组向量：
  V1: 标量压测（100,000 条，1000.0 ± 1e-3 微扰动）
  V2: LJ 系统（N=128 随机原子坐标，σ=3.4, ε=0.01, r_cut=12.0）
  V3: Buckingham（10+ 组距离/参数）

输出：CSV 文件到 vectors/ 目录
"""

import numpy as np
import csv
import os

SEED = 42
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT_DIR, exist_ok=True)


def gen_v1():
    """V1: 标量压测 — 100,000 条

    设计：交替大数 + 小数（Kahan 经典 stress test）。
    大数 1e8 + 小数 1.0 的交替序列会破坏 naive 累加（小数被吞掉），
    而 Kahan 补偿能正确恢复。这是展示补偿效果的标准构造。
    """
    rng = np.random.RandomState(SEED)
    n = 100_000
    # 交替：前 50000 条是 ~1e8 级别的大数，后 50000 条是 ~1.0 级别的小数
    # 随机打乱顺序，确保不是纯交替
    big_vals = (1e8 + rng.uniform(-1.0, 1.0, size=n//2)).astype(np.float32)
    small_vals = (1.0 + rng.uniform(-1e-3, 1e-3, size=n//2)).astype(np.float32)
    values = np.empty(n, dtype=np.float32)
    # 交叉填充：偶数位放大数，奇数位放小数
    values[0::2] = big_vals
    values[1::2] = small_vals
    # 随机打乱（保持固定种子）
    rng.shuffle(values)

    path = os.path.join(OUT_DIR, "v1_scalar.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["index", "value"])
        for i, v in enumerate(values):
            w.writerow([i, f"{v:.10e}"])
    print(f"V1: {n} 条标量 -> {path}")
    return path


def gen_v2():
    """V2: LJ 系统 — N=128 原子随机坐标"""
    rng = np.random.RandomState(SEED + 1)
    n = 128
    # 盒子边长 20 Å，随机坐标
    coords = rng.uniform(0.0, 20.0, size=(n, 3)).astype(np.float32)
    path = os.path.join(OUT_DIR, "v2_lj128.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["atom_id", "x", "y", "z"])
        for i in range(n):
            w.writerow([i, f"{coords[i,0]:.10e}", f"{coords[i,1]:.10e}", f"{coords[i,2]:.10e}"])
    print(f"V2: {n} 原子 LJ 系统 -> {path}")
    return path


def gen_v3():
    """V3: Buckingham — 12 组距离向量 + 参数"""
    rng = np.random.RandomState(SEED + 2)
    n = 12
    # 距离向量（确保 r 在合理范围内 2-15 Å）
    dx = rng.uniform(-10.0, 10.0, size=n).astype(np.float32)
    dy = rng.uniform(-10.0, 10.0, size=n).astype(np.float32)
    dz = rng.uniform(-10.0, 10.0, size=n).astype(np.float32)
    # Buckingham 参数组
    A_vals = rng.uniform(1000.0, 50000.0, size=n).astype(np.float32)
    rho_vals = rng.uniform(0.2, 0.5, size=n).astype(np.float32)
    C_vals = rng.uniform(1.0, 1000.0, size=n).astype(np.float32)
    r_cut = 15.0

    path = os.path.join(OUT_DIR, "v3_buckingham.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "dx", "dy", "dz", "A", "rho", "C", "r_cut"])
        for i in range(n):
            w.writerow([i,
                        f"{dx[i]:.10e}", f"{dy[i]:.10e}", f"{dz[i]:.10e}",
                        f"{A_vals[i]:.10e}", f"{rho_vals[i]:.10e}",
                        f"{C_vals[i]:.10e}", f"{r_cut:.1f}"])
    print(f"V3: {n} 组 Buckingham 参数 -> {path}")
    return path


if __name__ == "__main__":
    gen_v1()
    gen_v2()
    gen_v3()
    print("所有测试向量生成完毕。")
