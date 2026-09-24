# groklongcat-test-rvdon

独立第三方对 DiVo Gen²AI 公司 **RVDon + rvdon-kahan** 技术方案的验证仓库。

验证者：Grok x LongCat（由 Claude 执行）
被验证方：DiVo Gen²AI（github.com/sealionking/rvdon, github.com/sealionking/rvdon-kahan）

---

## 仓库结构

```
groklongcat-test-rvdon/
├── README.md                          # 本文件
├── v1_KAHAN_BATCH_WRONG/              # v1：Kahan 被误用为"批处理"
│   ├── src/*.c.dwp                    # 错误实现代码
│   ├── include/*.h.dwp                # 错误头文件
│   ├── Makefile.dwp
│   └── README.md.dwp                  # 包含错误结论的 README
├── v3_FINAL_CORRECT/                  # v3：正确的 Kahan + 完整报告
│   ├── src/                           # 正确实现（Kahan 单状态贯穿所有邻居）
│   ├── include/
│   ├── Makefile
│   ├── README.md                      # v2 设计说明
│   ├── REPORT.md                      # v2 测试报告（记录 v1-v2 的错）
│   ├── FINAL_ASSESSMENT.md            # 最终评估（含对 rvdon 的判断）
│   └── STATUS.md
└── docs/
    └── rvdon_hardware_verification.md # 硬件 RTL 验证报告（5/5 PASS）
```

**注：v2 文件并未单独保存**（被 v3 覆盖了），但 REPORT.md 中详细记录了 v2
的内容和结论。

---

## 三份报告是什么

| 版本 | 结论 | 对错 |
|------|------|:----:|
| v1 | "Kahan 在 LJ-MD 中基本没用，只能改善 0.1 bit" | ❌ 实现完全错误 |
| v2 | "Kahan 在 LJ-MD 力累积中只能改善 0.0~0.2 bit" | ❌ 测试场景不对 |
| v3 | "Kahan 在大小差异大的求和场景中提升 16-63x；rvdon 公开 RTL 已达成设计目标" | ✅ 正确 |

---

## 核心发现

### rvdon-kahan（软件 Kahan 求和）

- **纯数值测试**：2000 个大小差异大的数求和，Kahan FP32 比 naive FP32 好 **16-63 倍**
- 与 DiVo 声称的指标一致
- 但在 LJ 力累积中效果有限（邻居力大小差不多）
- **结论：API 设计正确，精度声明可信**

### rvdon 硬件扩展（ PF_TMM + PF_FLASH_ATTN）

- DiVo 公开了 RTL 代码和验证脚本
- 运行 `verify_pf_accuracy.py`：**5/5 测试 PASS**
  - LUT 条目精度：PASS
  - exp 组件精度：max err 3.17%, mean 1.56%
  - Flash Attention E2E：cosine sim 0.9999
  - Protenix Pairformer：cosine sim 0.9999
  - 1200 测试向量：全部匹配
- **结论：公开版 RTL 已经达到设计目标**

---

## 建议（对考虑购买 IP 的人）

1. **两个产品都值得申请免费评估授权**
2. **rvdon-kahan**：在 PME/Ewald 长程力、能量项求和场景中 Kahan 最有效
3. **rvdon 硬件**：自带验证脚本可独立验证，不盲信厂商
4. **谈判要求**：商业版 RTL 与公开版的差异、流片数据、第三方 benchmark

---

## 联系方式

- DiVo Gen²AI: wangjueju+divobot@gmail.com
- 本仓库维护者: github.com/sealionking (DiVo 方)

---

*2026-07-07 测试者注：本仓库记录了一个 AI agent 从"完全错误"到"基本正确"的完整过程。*
*v1 和 v2 的错误结论被保留，作为对后来者的警示。*
