# 项目状态

## 当前版本：v2（修复版）

编译通过 ✅  
单次静态测试通过 ✅  
完整 MD 长时运行通过 ✅  

## 已知限制

1. **PF_TMM 真实指令未测试**：因为 rvdon 仓库未安装，rvx_vec 模式用的是 scalar tree-sum 模拟
2. **rvdon-kahan 真实 API 未测试**：用标准 Kahan 算法代替
3. **能量漂移瓶颈不在累积**：在 PBC 距离计算、Verlet 辛结构、初始条件稳定性

## 文件清单

```
rvdontest/
├── Makefile                  # 编译入口
├── README.md                 # v2 设计说明
├── REPORT.md                 # v2 测试报告（含对 rvdon 的评估）
├── STATUS.md                 # 本文件
├── include/
│   ├── lj_system.h           # 四种力模式 API
│   ├── integrator.h          # Verlet 模式分派
│   └── benchmark.h           # 统一测试接口
├── src/
│   ├── lj_system.c           # 四种力模式实现
│   ├── integrator.c          # Verlet（fmodf PBC）
│   └── benchmark.c           # CLI 入口
└── results/                  # 运行产物（gitignore）
```
