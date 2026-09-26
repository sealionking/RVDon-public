# RVDon Cross-Validation

Independent verification of RVDon PF Extension numerical correctness.

## Files

| File | Description |
|------|-------------|
| `external_cross_validation_guide.md` | Complete verification instructions for external engineers |
| `kahan_input_matrices.csv` | Input matrices A(16×16) and B(16×8), FP16-decoded FP32 |
| `kahan_golden_vectors.csv` | Smoke test: 3 tiles × 128 elements (K=16, WGMMA/PF_TMM/FA_MMA) |
| `kahan_golden_vectors_extended.csv` | Extended: 6 tiles (K=128/K=256, WGMMA/PF_TMM/FA_MMA) |
| `kahan_golden_vectors_boundary.csv` | Boundary: 4 tiles (denormal/zero/large/sparse) |
| `gen_extended_vectors.py` | Reproducible generation script for extended vectors |
| `gen_boundary_vectors.py` | Reproducible generation script for boundary vectors |
| `SHA256SUMS` | SHA256 signatures for all CSV files |

## Quick Start

```bash
# 1. Read the guide
cat external_cross_validation_guide.md

# 2. Verify file integrity
sha256sum -c SHA256SUMS

# 3. Write your own verification script (see guide §3)
#    Or use rvdon-kahan library: cd ../ && make test

# 4. Compare your results against golden vectors
```

## Test Coverage

| Data Set | K | Tiles | Elements | Kahan vs Naive |
|----------|:---:|:---:|:---:|:---:|
| Smoke test | 16 | 3 | 384 | ~2.4e-7 (1 ULP) |
| Extended | 128 | 3 | 384 | ~5.7e-6 (24x) |
| Extended | 256 | 3 | 384 | ~1.5e-5 (64x) |
| Boundary | 64 | 4 | 512 | varies by pattern |

## Third-Party Verification Reports

| Verifier | Date | Result | Report |
|----------|------|:---:|--------|
| Grok × LongCat | 2026-07-07 | 5/5 PASS | `../../third-party-verification/FINAL_ASSESSMENT.md` |
| DeepSeek (TraeCode) | 2026-09-26 | 6/6 PASS | `../../third-party-verification/deepseek-20260926/` |
