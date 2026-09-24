# RVDon-public

Open-source components from the RVDon project (RISC-V Domain-specific Open Node).

RVDon is a self-developed chip IP based on the open-source Vortex RISC-V GPGPU,
extended with PF Extension (Pairformer hardware acceleration) for AlphaFold3 /
Protenix-style biomolecular computation. This repository consolidates all
open-sourceable components into a single managed repository.

Previously split across three separate repos (rvdon, rvdon-kahan,
groklongcat-test-rvdon) — now unified here for simpler maintenance.

## Components

### rvdon-spec — Architecture & Documentation (Apache 2.0)

PF Extension ISA specification, architecture documents, and design notes.

- `rvdon-spec/ARCHITECTURE.md` — PF Extension ISA spec (PF_TMM, PF_TMM_INC, PF_FLASH_ATTN)
- `rvdon-spec/docs/` — ISA spec, synthesis evaluation, precision whitepaper, opensource plan
- `rvdon-spec/CONTRIBUTING.md` — Contribution guide

### pf-extension — Open-source RTL & Intrinsics (Apache 2.0)

Selected RTL modules and software intrinsics from the PF Extension.

- `pf-extension/rtl/VX_tcu_fa.sv` — FA Online Softmax pipeline (3-stage, 16-entry LUT exp)
- `pf-extension/include/vx_pf.h` — PF Extension intrinsics (rvdon::pf namespace)
- `pf-extension/axi-bridge/VX_mem_axi_bridge.sv` — Vortex to AXI4 universal bridge

### mc-wrappers — Memory Controller Wrappers (Apache 2.0)

SystemVerilog wrappers for integrating external DDR/AXI memory controllers.

| Wrapper | Target Controller | Use Case |
|---------|-------------------|----------|
| passthrough | Direct passthrough | Testing, no external MC |
| cva6_axi | CVA6 AXI | RISC-V SoC integration |
| baiyang_ddr4 | Baiyang (YuQuan) DDR4 | SoC DDR4 |
| ddr3ctrl | DDR3 controller | Legacy DDR3 |
| litedram | LiteDRAM | FPGA DDR3/DDR4 |

### rvdon-kahan — Kahan Compensated Summation Library (MIT)

FP64-equivalent force accumulation for MD on FP32 hardware. Includes
cross-validation bridge for independently verifying PF Extension correctness.

- Library: `rvdon-kahan/src/rvdon_kahan.c`
- API: `rvdon-kahan/include/rvdon_kahan.h`
- Tests: 3 vector sets (scalar, LJ-128, Buckingham)
- Cross-validation: golden vectors + external engineer guide

### tests — PF Extension Test Suite (Apache 2.0)

Regression test for PF_TMM, PF_TMM_INC, FA_MMA, FA_SOFTMAX, FA_UPDATE, FA_E2E.

- `tests/pf_tcu/` — Host-side test (main.cpp, kernel.cpp, common.h, Makefile)

### verification — Verification Scripts & Test Vectors (Apache 2.0)

- `verification/scripts/` — verify_pf_accuracy.py, generate_test_vectors.py
- `verification/test-vectors/` — exp LUT, flash attention, Protenix Pairformer vectors
- `verification/results/` — verification results summary
- `verification/checklist/` — standardized verification checklist
- `verification/red-team/` — independent red-team verification report
- `verification/yuquan/` — YuQuan MC wrapper independent verification
- `verification/bug-fixes/` — bug10 technical note + verification script

### third-party-verification — Grok × LongCat Independent Verification

Third-party verification by Grok x LongCat (executed by Claude). Documents
the complete journey from incorrect (v1) to correct (v3) verification.

- `FINAL_ASSESSMENT.md` — Final assessment (5/5 PASS, cosine 0.9999)
- `REPORT.md` — Detailed test report
- `rvdon_hardware_verification.md` — Hardware RTL verification (5/5 PASS)

## Repository Structure

```
RVDon-public/
├── LICENSE                              # Apache 2.0 (top-level)
├── README.md
├── .gitignore
├── rvdon-spec/                          # Architecture & docs
│   ├── ARCHITECTURE.md
│   ├── CONTRIBUTING.md
│   └── docs/
├── pf-extension/                        # Open-source RTL & intrinsics
│   ├── rtl/VX_tcu_fa.sv
│   ├── include/vx_pf.h
│   └── axi-bridge/VX_mem_axi_bridge.sv
├── mc-wrappers/                         # Memory controller wrappers
│   ├── rtl/
│   ├── testbench/
│   └── docs/
├── rvdon-kahan/                         # Kahan library (MIT)
│   ├── LICENSE                           # MIT
│   ├── include/
│   ├── src/
│   ├── examples/
│   ├── tests/
│   └── cross-validation/
├── tests/                               # PF Extension test suite
│   └── pf_tcu/
├── verification/                        # Verification scripts & vectors
│   ├── scripts/
│   ├── test-vectors/
│   ├── results/
│   ├── checklist/
│   ├── red-team/
│   ├── yuquan/
│   └── bug-fixes/
└── third-party-verification/            # Grok × LongCat verification
    ├── FINAL_ASSESSMENT.md
    ├── REPORT.md
    └── rvdon_hardware_verification.md
```

## Licenses

| Component | License |
|-----------|---------|
| rvdon-kahan | MIT |
| All other components | Apache 2.0 |
| Top-level | Apache 2.0 |

## Related Projects

- [Vortex GPGPU](https://github.com/vortexgpgpu/vortex) — Apache 2.0, RISC-V GPGPU base
- [YuQuan (白杨)](https://github.com/OpenXiangShan/YuQuan) — MulanPSL-2.0, DDR4 controller IP
- [LiteDRAM](https://github.com/enjoy-digital/litedram) — BSD-2-Clause, DDR controller
- [ddr3ctrl](https://github.com/ultraembedded/ddr3ctrl) — MIT, DDR3 controller

## Archived Repositories

The following GitHub repositories are archived and superseded by this repo:

- `sealionking/rvdon` → contents merged into rvdon-spec/, pf-extension/, mc-wrappers/, tests/, verification/
- `sealionking/rvdon-kahan` → contents merged into rvdon-kahan/
- `sealionking/groklongcat-test-rvdon` → key reports merged into third-party-verification/

---

Copyright (c) 2024-2026 DiVo Gen²AI — 王掬琅（Peter Wang）· 王潇奕（Shawn Wang）
