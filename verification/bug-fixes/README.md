# RVDon BUG-10 独立黑盒验证 Kit

**版本**: v1.0 — 2026-07-19
**验证方**: 独立第三方（红队）
**发布方**: DiVo Gen²AI

---

## 一、验证声明

DiVo 声称修复了 RVDon PF Extension 的一个 BUG（编号 BUG-10），该 BUG 导致多 CTA 场景下三角遮罩坐标计算错误。

### 1.1 BUG 描述

**修复前**：当多个 CTA 在列方向排列（N > xtileN）时，第二个及之后的 CTA 的 `pf_col_base` 值为 0，导致三角遮罩在全局坐标系中位置错误——所有 CTA 的掩码行为与第一个 CTA 完全相同，而非按列偏移正确定位。

**修复后**：通过 `block_idx_x`/`block_idx_y` 信号从 CTA dispatch 全链路传播到 TCU 核心，每个 CTA 的 `pf_col_base = block_idx_x × xtileN`，`pf_row_base = block_idx_y × ISSUE_WIDTH × xtileM + warp_rank × xtileM`。

### 1.2 DiVo 的验证结果

| 测试场景 | Grid | 结果 |
|----------|------|------|
| M=16, N=8  (单CTA基线) | 1×1 | PASSED |
| M=16, N=16 (双CTA列方向) | 2×1 | PASSED |
| M=32, N=16 (4 CTA) | 2×2 | PASSED |
| M=80, N=16 (10 CTA) | 2×5 | PASSED |

### 1.3 你需要验证什么

**核心声明**：修复后的硬件在多 CTA 列方向场景下，PF_TMM 三角遮罩按全局坐标正确施加，而非所有 CTA 共享第一个 CTA 的掩码。

---

## 二、验证工具

本 kit 提供**编译好的黑盒仿真二进制**（librtlsim.so），你可以：

1. 用任何 Vortex 兼容的测试程序调用它
2. 输入不同 M/N 值，观察 PF_TMM 输出
3. 自行编写参考实现对比

**你不拥有**：RTL 源代码、SimX 行为模型源码、FA_SOFTMAX LUT 参数。

---

## 三、验证步骤

### Step 1: 环境搭建

```bash
# 本 kit 自带 librtlsim.so（已编译，ISSUE_WIDTH=4, NRC=8）
export LD_LIBRARY_PATH=$(pwd)/bin:$LD_LIBRARY_PATH
export VORTEX_DRIVER=rtlsim

# 需要你自行编译测试程序（或用我们提供的预编译二进制）
# 编译依赖: Vortex 公开 API (vortex.h)
```

### Step 2: 基线验证（单 CTA）

```bash
# M=16 N=8 → Grid=1×1（单 CTA，pf_col_base=0，不受 BUG-10 影响）
./run_test.sh 16 8
# 预期: PASSED
```

### Step 3: BUG-10 关键验证（多 CTA 列方向）

```bash
# M=16 N=16 → Grid=2×1（2个 CTA 列方向）
# CTA 0: block_idx_x=0, pf_col_base=0
# CTA 1: block_idx_x=1, pf_col_base=8
./run_test.sh 16 16
# 如果 BUG 未修复: CTA 1 的 pf_col_base=0（与 CTA 0 相同），PF_TMM 输出全0或错误
# 如果 BUG 已修复: CTA 1 的 pf_col_base=8，PF_TMM 输出正确
```

### Step 4: 大矩阵验证

```bash
./run_test.sh 32 16   # Grid=2×2
./run_test.sh 80 16   # Grid=2×5
```

---

## 四、独立参考实现

你可以用以下公式自行实现 PF_TMM 参考计算，与硬件输出对比：

### 4.1 坐标计算

```
xtileM = 4     // 2 × TCU_TC_M = 2 × 2 = 4
xtileN = 8     // (NRC × NT) / xtileM = (8 × 4) / 4 = 8
cta_M  = ISSUE_WIDTH × xtileM = 4 × 4 = 16
per_warp_N = xtileN = 8

// 对于 Grid[gridX][gridY] 中的 CTA:
block_idx_x = gridX  // 列方向索引
block_idx_y = gridY  // 行方向索引

// 每个 warp 的全局坐标偏移:
pf_row_base = block_idx_y × ISSUE_WIDTH × xtileM + warp_rank × xtileM
pf_col_base = block_idx_x × xtileN

// 逐元素全局坐标:
global_i = pf_row_base + step_m × TCU_TC_M + i   (i ∈ [0, TCU_TC_M))
global_j = pf_col_base + step_n × TCU_TC_N + j   (j ∈ [0, TCU_TC_N))
```

### 4.2 三角掩码

```
// PF_TMM Outgoing: 保留上三角（含对角线）
mask_out = (global_i <= global_j)

// PF_TMM Incoming: 保留下三角（含对角线）
mask_inc = (global_j <= global_i)

// PF_FLASH_ATTN FA_MMA: 因果掩码
causal_mask = (global_j <= global_i)
```

### 4.3 Python 参考实现

```python
import numpy as np

def pf_tmm_outgoing_ref(A, B, M, N, K,
                         issue_width=4, xtileM=4, xtileN=8,
                         tcM=2, tcN=2, tcK=4):
    """PF_TMM Outgoing 参考实现（含全局坐标）"""
    C = np.zeros((M, N), dtype=np.float32)
    cta_M = issue_width * xtileM
    per_warp_N = xtileN

    grid_x = N // per_warp_N
    grid_y = M // cta_M

    for gy in range(grid_y):
        for gx in range(grid_x):
            for warp_rank in range(issue_width):
                pf_row_base = gy * issue_width * xtileM + warp_rank * xtileM
                pf_col_base = gx * xtileN

                # 遍历该 warp 的 xtileM × xtileN 块
                for step_m in range(xtileM // tcM):
                    for step_n in range(xtileN // tcN):
                        for i in range(tcM):
                            for j in range(tcN):
                                global_i = pf_row_base + step_m * tcM + i
                                global_j = pf_col_base + step_n * tcN + j

                                # Outgoing: 保留 global_i <= global_j
                                if global_i > global_j:
                                    continue

                                # 计算 C[global_i][global_j]
                                for k in range(K):
                                    C[global_i][global_j] += A[global_i][k] * B[k][global_j]
    return C
```

### 4.4 BUG-10 修复前后对比

```python
# 修复前（BUG）: pf_col_base = 0（所有 CTA）
# 修复后:       pf_col_base = block_idx_x * xtileN

# 以 M=16 N=16 Grid=2×1 为例:
# CTA 0 (block_idx_x=0): pf_col_base = 0  → 列范围 [0, 7]
# CTA 1 (block_idx_x=1): pf_col_base = 8  → 列范围 [8, 15]

# BUG 场景: CTA 1 的 pf_col_base=0 → 列范围 [0, 7]（与 CTA 0 重叠）
# 结果: CTA 1 输出的 C[i][8..15] 全为 0（因为 j 永远 < 8，不满足 global_j >= 8）
```

---

## 五、验证清单（对应 standardized-verification-checklist-v1.1.md）

### 硬件功能正确性

- [ ] PF_TMM Outgoing: M=16 N=8 单 CTA — 错误数/总测试数
- [ ] PF_TMM Outgoing: M=16 N=16 双 CTA — 错误数/总测试数
- [ ] PF_TMM Incoming: 同上两组
- [ ] PF_FLASH_ATTN FA_MMA: M=16 N=16 双 CTA 因果掩码 — 错误数/总测试数
- [ ] SimX 与 RTL 仿真一致性 — 是否 0 错误

### 坐标计算专项

- [ ] block_idx_x/y 是否正确传播到 TCU（可用 PF_DBG trace 输出验证）
- [ ] pf_col_base 值是否正确（CTA 0 → 0, CTA 1 → 8）
- [ ] pf_row_base 值是否正确（CTA 0 warp 0 → 0, warp 1 → 4）
- [ ] 三角掩码是否在全局坐标下正确施加（非 warp-local）

### 大矩阵鲁棒性

- [ ] M=32 N=16 (Grid=2×2) — 是否 PASSED
- [ ] M=80 N=16 (Grid=2×5) — 是否 PASSED

---

## 六、IP 边界说明

### 你拥有（本 kit 提供）

| 材料 | 说明 |
|------|------|
| `bin/librtlsim.so` | Verilator 编译的 RTL 仿真黑盒二进制 |
| `bin/libvortex-rtlsim.so` | Vortex rtlsim 运行时 |
| `include/vortex.h` | Vortex 公开 API |
| `include/vortex2.h` | Vortex TCU 扩展 API |
| 坐标计算公式 + 参数值 | 第 4 节的完整数学描述 |
| Python 参考实现 | 第 4.3 节 |
| 测试脚本 | `tests/run_test.sh` |

### 你不拥有（DiVo IP）

| 材料 | 为什么不给 |
|------|-----------|
| RTL 源代码 (VX_tcu_core.sv, VX_tcu_pkg.sv 等) | 核心 IP |
| SimX 行为模型源码 (tcu_unit.cpp) | 核心 IP |
| FA_SOFTMAX LUT 精细参数 (32条目) | 商业授权内容 |
| FEDP pipeline 实现 | 核心 IP |
| 12个 pipeline 修改文件的源码 | 核心 IP |

### 逆向可行性评估

`librtlsim.so` 是 Verilator 将 RTL 翻译成 C++ 再编译的产物。代码经过：
- Verilator 的 AST → C++ 转换（大量生成代码，变量名被重写为 `v__PVT__...`）
- `-O2` 编译优化（内联、常量折叠、死代码消除）
- 链接时优化（LTO）

恢复出有意义的 RTL 结构的难度相当于从编译后的二进制恢复 C++ 源码——理论上可能，实际上不可行。

---

## 七、目录结构

```
rvdon-test-bug10/
├── README.md              ← 本文件
├── bin/
│   ├── librtlsim.so       ← 黑盒仿真二进制（ISSUE_WIDTH=4, NRC=8）
│   └── libvortex-rtlsim.so
├── include/
│   ├── vortex.h           ← 公开 API
│   └── vortex2.h          ← TCU 扩展 API
├── tests/
│   ├── run_test.sh        ← 一键测试脚本
│   └── verify_bug10.py    ← Python 独立验证脚本
├── vectors/
│   └── expected_results.csv  ← 预期输出参考
└── docs/
    ├── bug10-technical-note.md  ← BUG 技术说明（不含源码）
    └── verification-report-template.md  ← 验证报告模板
```

---

## 八、如何提交验证报告

请按 `docs/verification-report-template.md` 格式提交，必须包含：

1. **测试环境**：OS、编译器、Vortex 版本
2. **原始数据**：每个测试场景的完整输出（非截图，必须可复制文本）
3. **独立参考实现**：你自写的验证代码（Python/C++/任何语言）
4. **结论**：BUG-10 修复是否有效？YES/NO + 证据
5. **发现**：任何未预期的行为或异常

发送至: wangjueju+divobot@gmail.com
