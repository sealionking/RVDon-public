# PF 指令编码黄金参考（V1 字节级验证基准）

生成：2026-09-17，/opt/riscv/llvm-vortex（clang 20.1.8, fork b2ecfe0）
方法：`.insn r CUSTOM0, funct3, funct7=2, xFMD, xFMS, xFLAGS`（vx_pf.h 现行编码）

| 指令 | funct3 | fmd | fms | flags | 编码（LE hex word） |
|:-----|:---:|:---:|:---:|:---:|:---|
| PF_TMM | 3 | 1 | 2 | 0 | `0401308b` |
| PF_TMM_INC | 4 | 1 | 2 | 0 | `0401408b` |
| PF_FA_MMA | 5 | 1 | 2 | 0 | `0401508b` |
| PF_FA_SOFTMAX | 5 | 1 | 2 | 2 (sub_op=1<<1) | `0421508b` |
| PF_FA_UPDATE | 5 | 1 | 2 | 4 (sub_op=2<<1) | `0441508b` |

V1 验收：llvm-rvdon fork 的 llvm-mc 汇编 `pf_tmm` 等助记符必须产出
与上表逐字节一致的编码；llvm-objdump 必须能把这些字节反汇编回助记符
（当前上游 objdump 显示 `<unknown>`，证明 PF 对上游工具链不可见）。

源文件：pf_enc_golden_20260917.s（同目录）
关联：git-bug 4812080，docs/pf-llvm-codegen-design_20260917.md §六 V1
