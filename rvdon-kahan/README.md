# RVDon Kahan

**Kahan Compensated Summation for FP32 Hardware — MIT Licensed**

RVDon Kahan provides Kahan (1965) compensated summation for molecular dynamics
force accumulation, achieving near-FP64 accuracy on FP32 hardware with zero
hardware modifications.

## Why?

Protein MD simulations accumulate force contributions from hundreds of neighbor
atoms per timestep. Naive FP32 accumulation error grows as O(Nε) where
N = neighbor count and ε ≈ 1.2×10⁻⁷. For N = 200, this gives ~2.4×10⁻⁵ error
per accumulation — exceeding the 1e-6 energy conservation threshold.

Kahan compensated summation reduces this to O(ε) ≈ 1.2×10⁻⁷, which is **200×
better** than naive FP32 and well below the conservation threshold.

| Method | Per-Accumulation Error | Hardware Cost |
|--------|:---:|:---:|
| Naive FP32 (N=200) | ~2.4e-5 | Baseline |
| **RVDon Kahan (FP32)** | **~1.2e-7** | **0% (software only)** |
| FP64 Hardware | ~2.2e-16 | ~30% TCU area |

## Build

```bash
# Build the library
gcc -std=c99 -O2 -Wall -Wextra -c src/rvdon_kahan.c -o rvdon_kahan.o -Iinclude

# Build the example
gcc -std=c99 -O2 -o basic_usage examples/basic_usage.c src/rvdon_kahan.c -lm -Iinclude

# Run
./basic_usage
```

## Quick Start

```c
#include "rvdon_kahan.h"

int main() {
    int N = 1000;
    rvdon_force_acc_t **forces = rvdon_force_batch_create(N);

    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            float fx, fy, fz;
            float dx = coords[j*3+0] - coords[i*3+0];
            float dy = coords[j*3+1] - coords[i*3+1];
            float dz = coords[j*3+2] - coords[i*3+2];
            rvdon_lj_force(dx, dy, dz, sigma, epsilon, r_cut, &fx, &fy, &fz);
            rvdon_force_accum_pair(forces, i, j, fx, fy, fz);
        }
    }

    for (int i = 0; i < N; i++) {
        float fx, fy, fz;
        rvdon_force_acc_get(forces[i], &fx, &fy, &fz);
        /* use force vector */
    }

    rvdon_force_batch_destroy(forces, N);
    return 0;
}
```

## API

See [`include/rvdon_kahan.h`](include/rvdon_kahan.h) for the full API.

Key functions:
- `rvdon_kahan_create/add/get/reset` — scalar Kahan accumulator
- `rvdon_force_acc_create/accum/get` — 3D force accumulator
- `rvdon_lj_force` — Lennard-Jones pairwise force
- `rvdon_buckingham_force` — Buckingham pairwise force
- `rvdon_lj_forces_kahan` — all-pairs LJ forces with Kahan accumulation

## Testing

```bash
# Run self-contained tests (3 vector sets: scalar, LJ-128, Buckingham)
cd tests && make test

# Run valgrind memory leak check
cd tests && make valgrind

# Verify -ffast-math is rejected
cd tests && make test-fastmath
```

## PF Extension Cross-Validation

This library can be used to independently verify the RVDon PF Extension
hardware (triangle/causal masked matrix multiply) without accessing
proprietary RTL. See:

- [`cross-validation/external_cross_validation_guide.md`](cross-validation/external_cross_validation_guide.md)
  — Instructions for external engineers
- `cross-validation/kahan_input_matrices.csv` — input matrices A and B
- `cross-validation/kahan_golden_vectors.csv` — golden reference vectors

## Important: No -ffast-math

**Never compile this library with `-ffast-math` or equivalent flags.**
Kahan compensated summation relies on IEEE 754 strict evaluation order.
The library includes a compile-time check that will trigger a `#error`
if `-ffast-math` is detected.

## License

MIT License. See [`LICENSE`](LICENSE) for details.

Copyright (c) 2026 DiVo Gen²AI.

## Reference

Kahan, W. (1965). "Further remarks on reducing truncation errors."
*Communications of the ACM*, 8(1), 40.
