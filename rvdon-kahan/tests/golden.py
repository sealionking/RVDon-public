#!/usr/bin/env python3
"""
golden.py — 金标准计算（独立于 C 实现）

三个金标准：
  1. math.fsum — 精确舍入求和（V1 标量压测）
  2. numpy pairwise — 独立算法族（V2 LJ 系统能量/力）
  3. FP64 参考 — 双精度直接计算（V2/V3）

输出：golden_<vector>.csv，供 compare 阶段对比
"""

import math
import csv
import os
import struct
import numpy as np

VECTORS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vectors")
OUT_DIR = os.path.dirname(os.path.abspath(__file__))


def read_csv(path):
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def golden_v1():
    """V1 金标准：math.fsum（精确舍入）"""
    rows = read_csv(os.path.join(VECTORS_DIR, "v1_scalar.csv"))
    values_f32 = [float(r["value"]) for r in rows]

    # math.fsum: 精确舍入求和（使用 float64 中间表示）
    fsum_result = math.fsum(values_f32)

    # numpy pairwise 求和（float64）
    np_result = np.sum(np.array(values_f32, dtype=np.float64))

    # naive float32 求和（直接顺序累加）
    naive_f32 = np.float32(0.0)
    for v in values_f32:
        naive_f32 += np.float32(v)

    # naive float64 求和
    naive_f64 = np.float64(0.0)
    for v in values_f32:
        naive_f64 += np.float64(v)

    path = os.path.join(OUT_DIR, "golden_v1.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["method", "sum"])
        w.writerow(["math.fsum", f"{fsum_result:.15e}"])
        w.writerow(["numpy_pairwise", f"{np_result:.15e}"])
        w.writerow(["naive_f32", f"{naive_f32:.15e}"])
        w.writerow(["naive_f64", f"{naive_f64:.15e}"])

    print(f"V1 金标准:")
    print(f"  math.fsum      = {fsum_result:.15e}")
    print(f"  numpy pairwise = {np_result:.15e}")
    print(f"  naive f32      = {naive_f32:.15e}")
    print(f"  naive f64      = {naive_f64:.15e}")
    print(f"  -> {path}")
    return path


def lj_force_fp64(dx, dy, dz, sigma, epsilon, r_cut):
    """FP64 LJ 力计算（独立参考实现）"""
    r = math.sqrt(dx*dx + dy*dy + dz*dz)
    if r > r_cut or r == 0.0:
        return 0.0, 0.0, 0.0, 0.0

    s = sigma / r
    s2 = s * s
    s6 = s2 * s2 * s2
    s12 = s6 * s6

    pe = 4.0 * epsilon * (s12 - s6)

    # F_i = (dV/dr)/r * r_vec
    # dV/dr = (24*eps/r) * (s6 - 2*s12)
    # F_i = -(24*eps/r^2) * (2*s12 - s6) * r_vec
    coef = 24.0 * epsilon / (r * r)
    fmag = coef * (2.0 * s12 - s6)
    fx = -fmag * dx
    fy = -fmag * dy
    fz = -fmag * dz

    return pe, fx, fy, fz


def golden_v2():
    """V2 金标准：FP64 LJ 系统全量对力"""
    rows = read_csv(os.path.join(VECTORS_DIR, "v2_lj128.csv"))
    n = len(rows)
    coords = np.array([[float(r["x"]), float(r["y"]), float(r["z"])] for r in rows], dtype=np.float64)

    sigma = 3.4
    epsilon = 0.01
    r_cut = 12.0

    # FP64 逐对计算
    forces_fp64 = np.zeros((n, 3), dtype=np.float64)
    total_pe_fp64 = 0.0

    # numpy pairwise（用于势能用 numpy.sum 验证）
    pe_list = []

    for i in range(n):
        for j in range(i+1, n):
            dx = coords[j, 0] - coords[i, 0]
            dy = coords[j, 1] - coords[i, 1]
            dz = coords[j, 2] - coords[i, 2]

            pe, fx, fy, fz = lj_force_fp64(dx, dy, dz, sigma, epsilon, r_cut)

            if pe != 0.0:
                total_pe_fp64 += pe  # naive f64 sum
                pe_list.append(pe)
                forces_fp64[i, 0] += fx
                forces_fp64[i, 1] += fy
                forces_fp64[i, 2] += fz
                forces_fp64[j, 0] -= fx
                forces_fp64[j, 1] -= fy
                forces_fp64[j, 2] -= fz

    # numpy pairwise sum of energies
    pe_np = np.sum(np.array(pe_list, dtype=np.float64))

    # Newton's third law check: net force ≈ 0
    net_force = np.sum(forces_fp64, axis=0)

    path = os.path.join(OUT_DIR, "golden_v2.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["atom_id", "fx_fp64", "fy_fp64", "fz_fp64"])
        for i in range(n):
            w.writerow([i,
                        f"{forces_fp64[i,0]:.15e}",
                        f"{forces_fp64[i,1]:.15e}",
                        f"{forces_fp64[i,2]:.15e}"])
        # 元数据行（供 compare_results.py 读取）
        f.write(f"# total_pe_fp64,{total_pe_fp64:.15e}\n")
        f.write(f"# total_pe_numpy,{pe_np:.15e}\n")
        f.write(f"# net_force_fp64,{net_force[0]:.15e},{net_force[1]:.15e},{net_force[2]:.15e}\n")

    print(f"V2 金标准 (FP64):")
    print(f"  总势能 (naive f64) = {total_pe_fp64:.15e}")
    print(f"  总势能 (numpy sum) = {pe_np:.15e}")
    print(f"  净力 |F_net|       = ({net_force[0]:.6e}, {net_force[1]:.6e}, {net_force[2]:.6e})")
    print(f"  -> {path}")
    return path


def buckingham_force_fp64(dx, dy, dz, A, rho, C, r_cut):
    """FP64 Buckingham 力计算（独立参考实现）"""
    r = math.sqrt(dx*dx + dy*dy + dz*dz)
    if r > r_cut or r == 0.0:
        return 0.0, 0.0, 0.0, 0.0

    expr = math.exp(-r / rho)
    r6 = r**6
    pe = A * expr - C / r6

    # dV/dr = -A/rho * exp(-r/rho) + 6C/r^7
    dVdr = -A / rho * expr + 6.0 * C / (r**7)
    inv_r = 1.0 / r
    fx = dVdr * inv_r * dx
    fy = dVdr * inv_r * dy
    fz = dVdr * inv_r * dz

    return pe, fx, fy, fz


def golden_v3():
    """V3 金标准：FP64 Buckingham 力"""
    rows = read_csv(os.path.join(VECTORS_DIR, "v3_buckingham.csv"))

    path = os.path.join(OUT_DIR, "golden_v3.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pair_id", "pe_fp64", "fx_fp64", "fy_fp64", "fz_fp64"])
        print(f"V3 金标准 (FP64 Buckingham):")
        for row in rows:
            i = int(row["pair_id"])
            dx, dy, dz = float(row["dx"]), float(row["dy"]), float(row["dz"])
            A, rho, C = float(row["A"]), float(row["rho"]), float(row["C"])
            r_cut = float(row["r_cut"])

            pe, fx, fy, fz = buckingham_force_fp64(dx, dy, dz, A, rho, C, r_cut)
            w.writerow([i, f"{pe:.15e}", f"{fx:.15e}", f"{fy:.15e}", f"{fz:.15e}"])
            print(f"  pair {i:2d}: pe={pe:.10e}  F=({fx:.6e}, {fy:.6e}, {fz:.6e})")

    print(f"  -> {path}")
    return path


if __name__ == "__main__":
    golden_v1()
    golden_v2()
    golden_v3()
    print("金标准计算完毕。")
