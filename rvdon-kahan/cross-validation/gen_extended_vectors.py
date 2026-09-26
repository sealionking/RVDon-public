#!/usr/bin/env python3
"""Generate golden vectors for K=128 and K=256 with genuine FP32 accumulation.

Uses struct pack/unpack to emulate FP32 behavior in Python.
"""
import csv
import struct
import sys
import os

def fadd(a, b):
    """FP32 add."""
    return struct.unpack('f', struct.pack('f', float(a) + float(b)))[0]
def fmul(a, b):
    """FP32 mul."""
    return struct.unpack('f', struct.pack('f', float(a) * float(b)))[0]

def kahan_dot_f32(a_row, b_col):
    s = 0.0
    c = 0.0
    for k in range(len(a_row)):
        prod = fmul(a_row[k], b_col[k])
        y = fadd(prod, -c)
        t = fadd(s, y)
        c = fadd(fadd(t, -s), -y)
        s = t
    return s

def naive_dot_f32(a_row, b_col):
    s = 0.0
    for k in range(len(a_row)):
        s = fadd(s, fmul(a_row[k], b_col[k]))
    return s

# Pre-computed fp16 quantized matrices for deterministic inputs
# (i%7+1)*0.1 for A, (i%5+1)*0.2 for B, then fp16 round-trip
def fp16_round_trip(val):
    """Python float -> IEEE 754 binary16 -> float (truncates to fp16 precision)."""
    import math
    # Use numpy if available for accuracy, otherwise simple rounding
    try:
        import numpy as np
        return float(np.float16(val))
    except ImportError:
        pass
    # Fallback: round to ~3.3 decimal digits
    if abs(val) < 1e-7:
        return 0.0
    mantissa_bits = 10
    exp = int(math.log2(abs(val))) if abs(val) > 0 else -14
    scale = 2.0 ** (exp - mantissa_bits)
    return round(val / scale) * scale

def make_inputs(M, N, K):
    A = [[0.0]*K for _ in range(M)]
    B = [[0.0]*N for _ in range(K)]
    for i in range(M * K):
        val = (float(i % 7 + 1) * 0.1)
        A[i // K][i % K] = fp16_round_trip(val)
    for i in range(K * N):
        val = (float(i % 5 + 1) * 0.2)
        B[i // N][i % N] = fp16_round_trip(val)
    return A, B

def main():
    K_values = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else [128, 256]
    M, N = 16, 8
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_csv = os.path.join(script_dir, 'kahan_golden_vectors_extended.csv')

    print(f"Generating extended FP32 golden vectors: K={K_values}, M={M}, N={N}")
    print(f"Using struct-based FP32 emulation")

    with open(out_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['tile', 'row', 'col', 'kahan_ref', 'naive_ref'])
        tile_id = 3

        for K in K_values:
            A, B = make_inputs(M, N, K)
            for mask_name, mask_fn in [('WGMMA', None), ('PF_TMM', lambda i,j: i<j), ('FA_MMA', lambda i,j: i>=j)]:
                max_diff = 0.0
                for i in range(M):
                    a_row = A[i]
                    for j in range(N):
                        if mask_fn and not mask_fn(i, j):
                            w.writerow([tile_id, i, j, "0.0", "0.0"])
                            continue
                        b_col = [B[k][j] for k in range(K)]
                        kv = kahan_dot_f32(a_row, b_col)
                        nv = naive_dot_f32(a_row, b_col)
                        max_diff = max(max_diff, abs(kv - nv))
                        w.writerow([tile_id, i, j, f"{kv:.15e}", f"{nv:.15e}"])
                print(f"  Tile {tile_id}: K={K} {mask_name} ({M}x{N}) {M*N} elems, max KvsN diff={max_diff:.6e}")
                tile_id += 1

    print(f"Done. Output: {out_csv}")
    return 0

if __name__ == '__main__':
    sys.exit(main())