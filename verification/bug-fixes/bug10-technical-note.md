# BUG-10 技术说明

**编号**: BUG-10 (block_idx pipeline propagation)
**修复日期**: 2026-07-19
**影响范围**: PF_TMM, PF_TMM_INC, PF_FLASH_ATTN 的多 CTA 场景

---

## 1. 问题描述

Vortex GPU 的 TCU（Tensor Compute Unit）支持 PF Extension 的三角遮罩和因果掩码。掩码逻辑依赖全局坐标 `(global_i, global_j)` 来判断矩阵元素是否应被保留。

在 BUG-10 修复前，`global_i`/`global_j` 的计算只使用 warp 内的局部坐标：
- `pf_row_base = 0`, `pf_col_base = 0`

这意味着所有 CTA 的三角掩码行为完全相同——第二个 CTA 不会因为列偏移而调整掩码位置。

## 2. 修复方案

通过在 CTA dispatch 到 TCU core 的全链路 pipeline 中传播 `block_idx_x`/`block_idx_y` 信号，使每个 CTA 能够正确计算自己的全局坐标偏移：

```
pf_row_base = block_idx_y × ISSUE_WIDTH × xtileM + warp_rank × xtileM
pf_col_base = block_idx_x × xtileN
```

## 3. 参数值

| 参数 | 值 | 来源 |
|------|-----|------|
| NT | 4 | VX_CFG_NUM_THREADS |
| TCU_TC_M | 2 | 微分块行数 |
| TCU_TC_N | 2 | 微分块列数 |
| TCU_TC_K | 4 | 微分块K维 |
| xtileM | 4 | = 2 × TCU_TC_M |
| xtileN | 8 | = (NRC × NT) / xtileM = (8×4)/4 |
| ISSUE_WIDTH | 4 | VX_CFG_ISSUE_WIDTH |
| cta_M | 16 | = ISSUE_WIDTH × xtileM |
| per_warp_N | 8 | = xtileN |

**关键**: `xtileN = (NRC × NT) / xtileM = 8`，不是 `TCU_WG_TILE_N = (TCU_WG_NR × NT) / xtileM = 32`。

TCU_WG_NR=32 是 FPR 上限（所有 32 个浮点寄存器用作 C/D），但 PF 操作始终使用 NRC=8。

## 4. 坐标计算公式

对于 Grid[gridX][gridY] 中的 CTA：

```
block_idx_x = gridX    // 列方向
block_idx_y = gridY    // 行方向
warp_rank = wid % ISSUE_WIDTH

pf_row_base = block_idx_y * ISSUE_WIDTH * xtileM + warp_rank * xtileM
pf_col_base = block_idx_x * xtileN

global_i = pf_row_base + step_m * TCU_TC_M + i    (i ∈ [0, TCU_TC_M))
global_j = pf_col_base + step_n * TCU_TC_N + j    (j ∈ [0, TCU_TC_N))
```

## 5. 掩码规则

| 指令 | 掩码条件 | 说明 |
|------|---------|------|
| PF_TMM (Outgoing) | `global_i <= global_j` | 上三角+对角线 |
| PF_TMM_INC (Incoming) | `global_j <= global_i` | 下三角+对角线 |
| PF_FLASH_ATTN FA_MMA | `global_j <= global_i` | 因果掩码 |

## 6. BUG-10 具体影响

以 M=16 N=16 Grid=2×1 为例：

**修复后（正确）**：
- CTA 0 (block_idx_x=0): pf_col_base=0, 列范围 [0,7]
- CTA 1 (block_idx_x=1): pf_col_base=8, 列范围 [8,15]

**修复前（BUG）**：
- CTA 0: pf_col_base=0, 列范围 [0,7] ✓
- CTA 1: pf_col_base=0, 列范围 [0,7] ✗（应在 [8,15]）

CTA 1 的掩码错位导致：
1. 列 [0,7] 被重复计算（与 CTA 0 重叠）
2. 列 [8,15] 全部为 0（本应由 CTA 1 覆盖，但 global_j 永远 < 8）
3. 输出矩阵右半部分全零

## 7. Pipeline 传播路径

```
VX_cta_dispatch → VX_scheduler → VX_fetch → VX_decode
  → VX_ibuffer → VX_lane_dispatch → VX_opc_unit
  → VX_scoreboard → VX_dispatcher → VX_tcu_core
```

block_idx_x/y 作为执行头部（execution header）的新字段，沿此路径逐级传递。
