# RVDon PF Extension — External Cross-Validation Guide

> **Audience**: External engineers who wish to independently verify the numerical
> correctness of the RVDon PF Extension hardware without accessing proprietary RTL.
>
> **Prerequisites**: Familiarity with IEEE 754 floating-point arithmetic, Kahan
> compensated summation, and basic matrix multiplication.
>
> **No NDA required**: This guide and the accompanying data files contain no
> proprietary hardware information. The RTL is not distributed.

---

## 1. What You Are Verifying

The RVDon PF Extension adds three instructions to a RISC-V GPGPU:

| Instruction | Mask Type | Semantics |
|:---|:---|:---|
| PF_TMM | Outgoing triangle | Keep upper triangle (row < col); zero lower triangle + diagonal |
| PF_TMM_INC | Incoming triangle | Zero K-dimension elements where step_k >= min(row, col) |
| FA_MMA | Causal | Keep lower triangle + diagonal (row >= col); zero upper triangle |

Each instruction performs a masked matrix multiply: C = masked(A × B) where the
mask zeros certain A-row elements before the FEDP (floating-point dot product).
The hardware uses FP16 inputs (decoded to FP32) and accumulates in FP32.

You will verify that the hardware produces correct results by comparing its
output against your own independent Kahan-compensated reference implementation.

---

## 2. Provided Data Files

Two CSV files are distributed alongside this guide:

### 2.1 `kahan_input_matrices.csv`

Format:
```
matrix,row,col,value
A,0,0,9.997558593750000e-02
A,0,1,1.999511718750000e-01
...
B,0,0,1.999511718750000e-01
...
```

- Matrix A: 16 rows × 16 columns (row-major), FP16-decoded FP32 values
- Matrix B: 16 rows × 8 columns (row-major), FP16-decoded FP32 values
- All values are the exact FP32 representation after FP16 round-trip

### 2.2 `kahan_golden_vectors.csv`

Format:
```
tile,row,col,kahan_ref,naive_ref,rtl_output
0,0,0,3.619868040084839e+00,3.619868040084839e+00,3.619868040084839e+00
0,0,1,3.499951124191284e+00,3.499950885772705e+00,3.499951124191284e+00
...
```

Three tiles, each 16×8 = 128 elements (384 total):

| Tile | Operation | Mask |
|:---:|:---|:---|
| 0 | WGMMA (baseline, no mask) | None — full matmul |
| 1 | PF_TMM (outgoing triangle) | row >= col → zero |
| 2 | FA_MMA (causal mask) | row < col → zero |

Columns:
- `kahan_ref`: Reference computed with Kahan compensated summation (FP32)
- `naive_ref`: Reference computed with naive FP32 accumulation
- `rtl_output`: Actual hardware output from RTL simulation

---

## 3. What You Need to Implement

Write your own program (any language) that:

1. **Loads** `kahan_input_matrices.csv` to obtain matrices A and B
2. **Implements** Kahan compensated summation (Kahan, 1965):
   ```
   function kahan_add(acc, x):
       y = x - acc.comp
       t = acc.sum + y
       acc.comp = (t - acc.sum) - y
       acc.sum = t
   ```
3. **Computes** three matrix multiplies:
   - Tile 0: C[i][j] = Kahan_sum(A[i][:] × B[:][j]) — no mask
   - Tile 1: Same as tile 0, but zero the result where row >= col
   - Tile 2: Same as tile 0, but zero the result where row < col
4. **Compares** your results against the CSV columns

Alternatively, you may use the open-source **rvdon-kahan** library (DiVo Gen²AI,
MIT-compatible license) which implements the Kahan compensated accumulator API
documented in `rvdon_kahan.h`. The library provides:
- `rvdon_kahan_create()` / `rvdon_kahan_add()` / `rvdon_kahan_get()` — scalar accumulator
- `rvdon_force_acc_create()` / `rvdon_force_accum()` — 3D force accumulator

If you choose to use rvdon-kahan, link it as a static library and call the
scalar accumulator API for each dot product element.

---

## 4. Verification Criteria

### 4.1 Mask Correctness

For each tile, verify that the zero pattern matches the mask definition:

- **Tile 0 (WGMMA)**: No elements should be zero (unless the true result is zero)
- **Tile 1 (PF_TMM)**: All elements where row >= col must be exactly zero
- **Tile 2 (FA_MMA)**: All elements where row < col must be exactly zero

Check both `kahan_ref` and `rtl_output` columns.

### 4.2 Your Kahan vs CSV Kahan Reference

Your independently computed Kahan-compensated GEMM should match the
`kahan_ref` column within FP32 precision:

```
|your_result - kahan_ref| <= max(|kahan_ref| * 1e-6, 1e-6)
```

If you use FP64 (double) for your computation, expect differences up to
~2.4e-7 relative to the reference value, because the CSV kahan_ref was
computed in FP32 (C++ `float`). This is expected and not an error.

### 4.3 RTL Output vs Kahan Reference

The `rtl_output` column (actual hardware output) should match `kahan_ref`
within the hardware tolerance:

```
|rtl_output - kahan_ref| <= max(|kahan_ref| * 0.005, 1e-3)
```

The 0.5% relative tolerance accounts for FP16 input quantization and FP32
FEDP pipeline accumulation order differences.

### 4.4 Naive vs Kahan Divergence

The `naive_ref` column (naive FP32 accumulation) should differ from
`kahan_ref` by at most ~5e-7 absolute. This is the expected FP32
accumulation error that Kahan compensation corrects. If the divergence
is much larger, the input data or computation order may be wrong.

---

## 5. Suggested Workflow

1. Parse both CSV files
2. Reconstruct A (16×16) and B (16×8) matrices
3. Implement Kahan compensated GEMM with the three mask patterns
4. Load the golden vectors
5. Run the four checks from Section 4
6. Report: total elements checked, pass count, fail count, max differences

---

## 6. Expected Results

For reference, our internal verification yielded:

| Check | Tile 0 (WGMMA) | Tile 1 (PF_TMM) | Tile 2 (FA_MMA) |
|:---|:---:|:---:|:---:|
| Mask correctness | 0 errors | 0 errors | 0 errors |
| RTL vs Kahan | 0 errors (max 4.77e-7) | 0 errors | 0 errors |
| Independent Kahan vs CSV | 0 errors (max 2.38e-7) | 0 errors | 0 errors |
| Naive vs Kahan max diff | 4.77e-7 | 4.77e-7 | 4.77e-7 |

Total: 384/384 elements passed all checks.

---

## 7. Intellectual Property Statement

- **Distributed**: Input matrices, golden vectors, this guide, and the
  rvdon-kahan library (open-source, separately licensed)
- **Not distributed**: RVDon PF Extension RTL code, FEDP pipeline
  implementation, TCU microarchitecture, landing queue structure

The input matrices use a simple deterministic pattern (i % 7 + 1) × 0.1 for A
and (i % 5 + 1) × 0.2 for B, then FP16-quantized. This is not proprietary data.

The Kahan compensated summation algorithm is public domain (Kahan, 1965).
The mask definitions (triangle/causal) are standard mathematical concepts.

---

## 8. References

1. Kahan, W. (1965). "Further remarks on reducing truncation errors."
   *Communications of the ACM*, 8(1), 40.
2. IEEE 754-2019: IEEE Standard for Floating-Point Arithmetic.
3. Vaswani, A. et al. (2017). "Attention Is All You Need." *NeurIPS*.
   (Causal mask in attention mechanism)
4. rvdon-kahan public API: `rvdon_kahan.h` (distributed separately)
