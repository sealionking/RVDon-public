#!/usr/bin/env python3
"""
compare_results.py — 对比 C 实现 vs 金标准

判据：
  V1: Kahan vs math.fsum 相对误差 < 1e-6; Kahan vs naive f32 精度提升 >= 100x
  V2: Kahan 力/能量 vs FP64 参考相对误差 < 1e-5; Newton's 3rd law 净力 < 1e-5
  V3: Kahan vs FP64 Buckingham 相对误差 < 1e-5
"""

import csv
import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def read_csv_dict(path):
    """读取 CSV，返回行列表（每行是 dict）"""
    with open(path, "r") as f:
        return list(csv.DictReader(f))


def read_meta_csv(path):
    """读取带 # 注释行的 CSV"""
    result = {}
    with open(path, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].startswith("#"):
                key = row[0].lstrip("# ").strip()
                vals = [float(v) for v in row[1:]]
                result[key] = vals[0] if len(vals) == 1 else vals
    return result


def rel_err(a, b):
    """相对误差"""
    if abs(b) < 1e-300:
        return abs(a) if abs(a) < 1e-300 else float('inf')
    return abs(a - b) / abs(b)


def check_v1():
    """V1: 标量压测"""
    print("=" * 60)
    print("V1: 标量压测 (100,000 条)")
    print("=" * 60)

    golden = read_csv_dict(os.path.join(TESTS_DIR, "golden_v1.csv"))
    c_result = read_csv_dict(os.path.join(TESTS_DIR, "c_result_v1.csv"))

    fsum_val = float(golden[0]["sum"])
    np_val = float(golden[1]["sum"])
    naive_f32_val = float(golden[2]["sum"])
    naive_f64_val = float(golden[3]["sum"])

    kahan_val = float(c_result[0]["sum"])
    c_naive_val = float(c_result[1]["sum"])

    # 判据 1: Kahan vs math.fsum 相对误差
    err_kahan_fsum = rel_err(kahan_val, fsum_val)
    pass1 = err_kahan_fsum < 1e-6
    print(f"  Kahan f32 sum      = {kahan_val:.15e}")
    print(f"  math.fsum (golden) = {fsum_val:.15e}")
    print(f"  相对误差            = {err_kahan_fsum:.6e}")
    print(f"  判据 < 1e-6:        {'PASS' if pass1 else 'FAIL'}")

    # 判据 2: Kahan vs naive f32 精度提升
    err_kahan = rel_err(kahan_val, fsum_val)
    err_naive = rel_err(c_naive_val, fsum_val)
    improvement = err_naive / err_kahan if err_kahan > 0 else float('inf')
    pass2 = improvement >= 100
    print(f"\n  Kahan 误差 = {err_kahan:.6e}")
    print(f"  Naive 误差 = {err_naive:.6e}")
    print(f"  精度提升   = {improvement:.1f}x")
    print(f"  判据 >= 100x:      {'PASS' if pass2 else 'FAIL'}")

    return pass1 and pass2


def check_v2():
    """V2: LJ 系统"""
    print("\n" + "=" * 60)
    print("V2: LJ 系统 (128 原子)")
    print("=" * 60)

    golden_rows = read_csv_dict(os.path.join(TESTS_DIR, "golden_v2.csv"))
    golden_meta = read_meta_csv(os.path.join(TESTS_DIR, "golden_v2.csv"))
    c_rows = read_csv_dict(os.path.join(TESTS_DIR, "c_result_v2.csv"))
    c_meta = read_meta_csv(os.path.join(TESTS_DIR, "c_result_v2.csv"))

    # 过滤掉注释行
    c_data = [r for r in c_rows if not r.get("atom_id", "").startswith("#")]
    golden_data = [r for r in golden_rows if not r.get("atom_id", "").startswith("#")]

    n = len(golden_data)
    max_force_err = 0.0
    rms_force_err = 0.0

    for i in range(n):
        gx = float(golden_data[i]["fx_fp64"])
        gy = float(golden_data[i]["fy_fp64"])
        gz = float(golden_data[i]["fz_fp64"])
        kx = float(c_data[i]["fx_kahan"])
        ky = float(c_data[i]["fy_kahan"])
        kz = float(c_data[i]["fz_kahan"])

        gmag = (gx*gx + gy*gy + gz*gz)**0.5
        if gmag > 0:
            err = ((kx-gx)**2 + (ky-gy)**2 + (kz-gz)**2)**0.5 / gmag
        else:
            err = ((kx-gx)**2 + (ky-gy)**2 + (kz-gz)**2)**0.5
        max_force_err = max(max_force_err, err)
        rms_force_err += err**2

    rms_force_err = (rms_force_err / n)**0.5

    # 势能对比
    pe_kahan = c_meta.get("total_pe_kahan", 0.0)
    pe_fp64 = golden_meta.get("total_pe_fp64", 0.0)
    pe_err = rel_err(pe_kahan, pe_fp64)

    # Newton's 3rd law
    net_force = c_meta.get("net_force_kahan", [0, 0, 0])
    if isinstance(net_force, (int, float)):
        net_force = [net_force]
    net_mag = (net_force[0]**2 + net_force[1]**2 + net_force[2]**2)**0.5

    # 总力大小参考
    total_force_mag = 0.0
    for i in range(n):
        gx = float(golden_data[i]["fx_fp64"])
        gy = float(golden_data[i]["fy_fp64"])
        gz = float(golden_data[i]["fz_fp64"])
        total_force_mag += (gx*gx + gy*gy + gz*gz)**0.5
    rel_net = net_mag / total_force_mag if total_force_mag > 0 else net_mag

    pass1 = max_force_err < 1e-5
    pass2 = pe_err < 1e-5
    pass3 = rel_net < 1e-5

    print(f"  最大力相对误差 = {max_force_err:.6e}  判据 < 1e-5: {'PASS' if pass1 else 'FAIL'}")
    print(f"  RMS 力相对误差  = {rms_force_err:.6e}")
    print(f"  势能相对误差   = {pe_err:.6e}  判据 < 1e-5: {'PASS' if pass2 else 'FAIL'}")
    print(f"  净力 |F_net|   = ({net_force[0]:.6e}, {net_force[1]:.6e}, {net_force[2]:.6e})")
    print(f"  相对净力       = {rel_net:.6e}  判据 < 1e-5: {'PASS' if pass3 else 'FAIL'}")

    return pass1 and pass2 and pass3


def check_v3():
    """V3: Buckingham"""
    print("\n" + "=" * 60)
    print("V3: Buckingham 力 (12 组)")
    print("=" * 60)

    golden_rows = read_csv_dict(os.path.join(TESTS_DIR, "golden_v3.csv"))
    c_rows = read_csv_dict(os.path.join(TESTS_DIR, "c_result_v3.csv"))

    n = len(golden_rows)
    max_pe_err = 0.0
    max_force_rel_err = 0.0
    max_force_abs_err = 0.0

    for i in range(n):
        g_pe = float(golden_rows[i]["pe_fp64"])
        g_fx = float(golden_rows[i]["fx_fp64"])
        g_fy = float(golden_rows[i]["fy_fp64"])
        g_fz = float(golden_rows[i]["fz_fp64"])

        k_pe = float(c_rows[i]["pe_kahan"])
        k_fx = float(c_rows[i]["fx_kahan"])
        k_fy = float(c_rows[i]["fy_kahan"])
        k_fz = float(c_rows[i]["fz_kahan"])

        # 势能：相对误差
        pe_e = rel_err(k_pe, g_pe) if abs(g_pe) > 1e-10 else abs(k_pe - g_pe)

        # 力：相对误差 + 绝对误差分别记录
        gmag = (g_fx**2 + g_fy**2 + g_fz**2)**0.5
        abs_f_err = ((k_fx-g_fx)**2 + (k_fy-g_fy)**2 + (k_fz-g_fz)**2)**0.5
        max_force_abs_err = max(max_force_abs_err, abs_f_err)

        if gmag > 1e-6:
            f_e = abs_f_err / gmag
        else:
            # 力很小时相对误差无意义，用绝对误差判断
            # 阈值取最大力量级的 1e-5 倍（由后续判定处理）
            f_e = 0.0

        max_pe_err = max(max_pe_err, pe_e)
        max_force_rel_err = max(max_force_rel_err, f_e)

    # 判定：相对误差 OR 绝对误差任一通过即可
    max_force_err = max(max_force_rel_err, max_force_abs_err)

    pass1 = max_pe_err < 1e-5
    pass2 = max_force_err < 1e-5

    print(f"  最大势能相对误差 = {max_pe_err:.6e}  判据 < 1e-5: {'PASS' if pass1 else 'FAIL'}")
    print(f"  最大力相对误差   = {max_force_rel_err:.6e}")
    print(f"  最大力绝对误差   = {max_force_abs_err:.6e}")
    print(f"  力判据(rel|abs)  = {max_force_err:.6e}  判据 < 1e-5: {'PASS' if pass2 else 'FAIL'}")

    return pass1 and pass2


def main():
    all_pass = True

    all_pass &= check_v1()
    all_pass &= check_v2()
    all_pass &= check_v3()

    print("\n" + "=" * 60)
    if all_pass:
        print("总体结论: ALL PASS")
    else:
        print("总体结论: SOME FAILED")
    print("=" * 60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
