#!/usr/bin/env python3
"""Generate boundary value golden vectors for PF Extension verification.

Covers: denormals, zero matrices, large values, sparse matrices.
All computation in FP32 via struct pack/unpack.
"""
import csv
import struct
import sys
import os
import math

def fadd(a, b):
    return struct.unpack('f', struct.pack('f', float(a) + float(b)))[0]
def fmul(a, b):
    return struct.unpack('f', struct.pack('f', float(a) * float(b)))[0]

def kahan_dot_f32(a_row, b_col):
    s = 0.0; c = 0.0
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

def fp16_round_trip(val):
    try:
        import numpy as np
        return float(np.float16(val))
    except ImportError:
        pass
    if abs(val) < 1e-7: return 0.0
    exp = int(math.log2(abs(val))) if abs(val) > 0 else -14
    scale = 2.0 ** (exp - 10)
    return round(val / scale) * scale

def make_test_matrix(pattern, M, K, N):
    """Generate A(M×K) and B(K×N) based on pattern name."""
    A = [[0.0]*K for _ in range(M)]
    B = [[0.0]*N for _ in range(K)]

    if pattern == 'denormal':
        dn = struct.unpack('f', struct.pack('I', 1))[0]  # smallest subnormal
        for i in range(M*K):
            A[i//K][i%K] = fp16_round_trip(dn * ((i % 5) + 1))
        for i in range(K*N):
            B[i//N][i%N] = fp16_round_trip(dn * ((i % 3) + 1))

    elif pattern == 'zero':
        pass  # all zeros

    elif pattern == 'large':
        big = fp16_round_trip(1e4)
        for i in range(M*K):
            A[i//K][i%K] = big * fp16_round_trip(float((i % 7) + 1) * 0.1)
        for i in range(K*N):
            B[i//N][i%N] = big * fp16_round_trip(float((i % 5) + 1) * 0.2)

    elif pattern == 'sparse':
        for i in range(M*K):
            if (i % 20) == 0:
                A[i//K][i%K] = fp16_round_trip(float((i % 7) + 1) * 0.1)
        for i in range(K*N):
            if (i % 20) == 0:
                B[i//N][i%N] = fp16_round_trip(float((i % 5) + 1) * 0.2)

    return A, B

def main():
    M, K, N = 16, 64, 8
    script_dir = os.path.dirname(os.path.abspath(__file__))
    out_csv = os.path.join(script_dir, 'kahan_golden_vectors_boundary.csv')

    patterns = ['denormal', 'zero', 'large', 'sparse']
    print(f"Generating boundary golden vectors: {patterns}")
    print(f"Matrix: M={M}, K={K}, N={N}")

    with open(out_csv, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['tile', 'pattern', 'row', 'col', 'kahan_ref', 'naive_ref'])
        tile_id = 9  # after extended tiles 3-8

        for pat in patterns:
            A, B = make_test_matrix(pat, M, K, N)
            max_diff = 0.0
            nonzero_count = 0
            for i in range(M):
                a_row = A[i]
                for j in range(N):
                    b_col = [B[k][j] for k in range(K)]
                    kv = kahan_dot_f32(a_row, b_col)
                    nv = naive_dot_f32(a_row, b_col)
                    diff = abs(kv - nv)
                    max_diff = max(max_diff, diff)
                    if kv != 0.0: nonzero_count += 1
                    w.writerow([tile_id, pat, i, j, f"{kv:.15e}", f"{nv:.15e}"])
            print(f"  Tile {tile_id}: {pat} ({M}x{N}) max_diff={max_diff:.6e} nonzero={nonzero_count}")
            tile_id += 1

    print(f"Done. Output: {out_csv}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
