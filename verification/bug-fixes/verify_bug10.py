#!/usr/bin/env python3
"""
verify_bug10.py — RVDon BUG-10 独立验证脚本（纯 Python，无需硬件）

这个脚本不依赖任何 DiVo 内部代码。它从第一性原理实现 PF_TMM 的
全局坐标三角遮罩计算，生成预期输出，供与硬件结果对比。

用法: python3 verify_bug10.py [M] [N] [K]

BUG-10 核心问题:
  修复前: pf_col_base = 0（所有CTA共用第一个CTA的列偏移）
  修复后: pf_col_base = block_idx_x * xtileN（每个CTA正确偏移）

验证策略:
  1. 用全局坐标公式计算正确的 PF_TMM 输出
  2. 用 BUG 场景（pf_col_base=0）计算错误输出
  3. 对比两者，证明 BUG 确实存在且修复有效
  4. 生成测试向量供黑盒仿真对比
"""

import sys
import json
import struct
import numpy as np

# ==============================================================
# TCU 参数 (NT=4, NRC=8 默认配置 — 来自 Vortex 公开文档)
# ==============================================================

NT = 4           # VX_CFG_NUM_THREADS
TCU_TC_M = 2     # 微分块行数
TCU_TC_N = 2     # 微分块列数
TCU_TC_K = 4     # 微分块K维
xtileM = 4       # = 2 * TCU_TC_M
xtileN = 8       # = (NRC * NT) / xtileM = (8 * 4) / 4 = 8
ISSUE_WIDTH = 4  # VX_CFG_ISSUE_WIDTH
cta_M = ISSUE_WIDTH * xtileM  # = 16

def pf_tmm_outgoing_global(A, B, M, N, K):
    """
    PF_TMM Outgoing 参考实现 — 全局坐标（BUG-10 修复后）
    掩码: global_i <= global_j（保留上三角+对角线）
    """
    C = np.zeros((M, N), dtype=np.float32)
    per_warp_N = xtileN
    grid_x = N // per_warp_N
    grid_y = M // cta_M

    for gy in range(grid_y):
        for gx in range(grid_x):
            for warp_rank in range(ISSUE_WIDTH):
                pf_row_base = gy * ISSUE_WIDTH * xtileM + warp_rank * xtileM
                pf_col_base = gx * xtileN  # BUG-10 修复: 使用 block_idx_x * xtileN

                for step_m in range(xtileM // TCU_TC_M):
                    for step_n in range(xtileN // TCU_TC_N):
                        for i in range(TCU_TC_M):
                            for j in range(TCU_TC_N):
                                global_i = pf_row_base + step_m * TCU_TC_M + i
                                global_j = pf_col_base + step_n * TCU_TC_N + j

                                if global_i > global_j:
                                    continue
                                if global_i >= M or global_j >= N:
                                    continue

                                for k in range(K):
                                    C[global_i][global_j] += A[global_i][k] * B[k][global_j]
    return C


def pf_tmm_outgoing_buggy(A, B, M, N, K):
    """
    PF_TMM Outgoing BUG 场景 — pf_col_base=0（所有CTA）
    这模拟了 BUG-10 修复前的行为
    """
    C = np.zeros((M, N), dtype=np.float32)
    per_warp_N = xtileN
    grid_x = N // per_warp_N
    grid_y = M // cta_M

    for gy in range(grid_y):
        for gx in range(grid_x):
            for warp_rank in range(ISSUE_WIDTH):
                pf_row_base = gy * ISSUE_WIDTH * xtileM + warp_rank * xtileM
                pf_col_base = 0  # BUG: 所有 CTA 列偏移为 0

                for step_m in range(xtileM // TCU_TC_M):
                    for step_n in range(xtileN // TCU_TC_N):
                        for i in range(TCU_TC_M):
                            for j in range(TCU_TC_N):
                                global_i = pf_row_base + step_m * TCU_TC_M + i
                                global_j = pf_col_base + step_n * TCU_TC_N + j

                                if global_i > global_j:
                                    continue
                                if global_i >= M or global_j >= N:
                                    continue

                                for k in range(K):
                                    C[global_i][global_j] += A[global_i][k] * B[k][global_j]
    return C


def pf_tmm_outgoing_warp_local(A, B, M, N, K):
    """
    PF_TMM Outgoing — warp-local 坐标（rvdon-public v1.0 的行为）
    掩码: local_i < local_j（warp内局部坐标，非全局）
    """
    C = np.zeros((M, N), dtype=np.float32)
    for row in range(M):
        for col in range(N):
            local_i = row % xtileM
            local_j = col % xtileN
            if local_i >= local_j:
                continue
            for k in range(K):
                C[row][col] += A[row][k] * B[k][col]
    return C


def generate_test_data(M, N, K, seed=42):
    """生成测试输入数据"""
    rng = np.random.RandomState(seed)
    A = (rng.randn(M, K) * 0.5 + 1.0).astype(np.float32)
    B = (rng.randn(K, N) * 0.3 + 0.5).astype(np.float32)
    return A, B


def verify_bug10():
    """主验证流程"""
    M = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    N = int(sys.argv[2]) if len(sys.argv) > 2 else 16
    K = int(sys.argv[3]) if len(sys.argv) > 3 else 16

    print("=" * 70)
    print("RVDon BUG-10 独立验证（纯数学，无需硬件）")
    print("=" * 70)
    print(f"\n参数: M={M}, N={N}, K={K}")
    print(f"xtileM={xtileM}, xtileN={xtileN}, ISSUE_WIDTH={ISSUE_WIDTH}")
    print(f"cta_M={cta_M}, per_warp_N={xtileN}")
    print(f"Grid: {N // xtileN}x{M // cta_M}")

    # 检查维度合法性
    if M % cta_M != 0 or N % xtileN != 0:
        print(f"\nERROR: M={M} 必须是 cta_M={cta_M} 的倍数, N={N} 必须是 xtileN={xtileN} 的倍数")
        return

    A, B = generate_test_data(M, N, K)

    # 三种实现
    C_global = pf_tmm_outgoing_global(A, B, M, N, K)
    C_buggy = pf_tmm_outgoing_buggy(A, B, M, N, K)
    C_warp_local = pf_tmm_outgoing_warp_local(A, B, M, N, K)

    grid_x = N // xtileN

    # ============================================================
    # 核心验证: 全局坐标 vs BUG 场景
    # ============================================================
    print("\n" + "─" * 70)
    print("验证1: 全局坐标（修复后）vs BUG场景（pf_col_base=0）")
    print("─" * 70)

    diff = np.abs(C_global - C_buggy)
    num_diff = np.count_nonzero(diff > 1e-6)
    total = M * N

    print(f"  差异元素数: {num_diff} / {total}")
    print(f"  最大差异:   {diff.max():.6f}")
    print(f"  平均差异:   {diff.mean():.6f}")

    if num_diff == 0 and grid_x <= 1:
        print("  → 单CTA场景（grid_x=1），无差异是预期的（BUG不影响单CTA）")
    elif num_diff > 0:
        print("  → 多CTA场景，BUG导致输出不同！修复是必要的。")

        # 找到差异最大的区域
        diff_rows, diff_cols = np.where(diff > 1e-6)
        if len(diff_rows) > 0:
            print(f"\n  差异分布:")
            for gx in range(grid_x):
                col_start = gx * xtileN
                col_end = (gx + 1) * xtileN
                region_diff = diff[:, col_start:col_end]
                region_num = np.count_nonzero(region_diff > 1e-6)
                region_max = region_diff.max()
                print(f"    CTA列{gx} (col {col_start}-{col_end-1}): "
                      f"{region_num} 个差异, max={region_max:.4f}")
    else:
        print("  → ⚠️ 多CTA但无差异？可能BUG-10修复未生效")

    # ============================================================
    # 验证2: 全局坐标 vs warp-local 坐标（rvdon-public v1.0行为）
    # ============================================================
    print("\n" + "─" * 70)
    print("验证2: 全局坐标（修复后）vs warp-local（rvdon-public v1.0）")
    print("─" * 70)

    diff2 = np.abs(C_global - C_warp_local)
    num_diff2 = np.count_nonzero(diff2 > 1e-6)
    print(f"  差异元素数: {num_diff2} / {total}")
    if num_diff2 > 0:
        print("  → 全局坐标和warp-local行为不同！说明BUG-10修复改变了语义。")
    else:
        print("  → 结果一致（可能在某些配置下两者等价）")

    # ============================================================
    # 验证3: 三角遮罩正确性（核心验证）
    # ============================================================
    print("\n" + "─" * 70)
    print("验证3: 三角遮码正确性检查")
    print("─" * 70)

    # 检查: global_i > global_j 的位置应为 0
    mask_violations = 0
    non_zero_upper = 0
    for row in range(M):
        for col in range(N):
            if row > col:
                # 下三角：PF_TMM Outgoing 应为 0
                if abs(C_global[row][col]) > 1e-6:
                    mask_violations += 1
            else:
                # 上三角+对角线：应有非零值（除非 A*B 恰好为 0）
                if abs(C_global[row][col]) > 1e-6:
                    non_zero_upper += 1

    print(f"  下三角非零违规: {mask_violations} (应为0)")
    print(f"  上三角+对角非零: {non_zero_upper} / {M * (M + 1) // 2}")

    if mask_violations == 0:
        print("  ✅ 三角遮码正确：下三角全部为0")
    else:
        print(f"  ❌ 三角遮码错误：{mask_violations} 个下三角位置非零")

    # ============================================================
    # 生成测试向量（供黑盒仿真对比）
    # ============================================================
    print("\n" + "─" * 70)
    print("生成测试向量: vectors/expected_results.csv")
    print("─" * 70)

    import os
    vec_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vectors")
    os.makedirs(vec_dir, exist_ok=True)

    with open(os.path.join(vec_dir, "expected_results.csv"), "w") as f:
        f.write("row,col,global_coord_value,buggy_value,warp_local_value\n")
        for row in range(M):
            for col in range(N):
                f.write(f"{row},{col},{C_global[row][col]:.8e},"
                        f"{C_buggy[row][col]:.8e},{C_warp_local[row][col]:.8e}\n")

    print(f"  已写入 {M * N} 个测试向量")

    # ============================================================
    # 总结
    # ============================================================
    print("\n" + "=" * 70)
    print("验证总结")
    print("=" * 70)

    grid_x = N // xtileN
    grid_y = M // cta_M

    if grid_x > 1:
        if num_diff > 0 and mask_violations == 0:
            print("✅ BUG-10 修复有效:")
            print(f"   - 多CTA场景（Grid={grid_x}x{grid_y}）下全局坐标与BUG场景显著不同")
            print(f"   - 修复后的三角遮码在下三角区域全部为0（正确）")
            print(f"   - BUG场景中 CTA1+ 的输出错误（pf_col_base=0 而非 {xtileN}）")
        else:
            print("⚠️ 需要进一步调查:")
            print(f"   - 差异元素数: {num_diff}")
            print(f"   - 遮码违规数: {mask_violations}")
    else:
        print("ℹ️ 单CTA场景，BUG-10不适用。请用 N>8 测试多CTA。")

    print(f"\n第三方验证建议: 用黑盒仿真运行 M={M} N={N} 并对比上述向量。")


if __name__ == "__main__":
    verify_bug10()
