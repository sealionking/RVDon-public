/**
 * basic_usage.c — RVDon Kahan Quick Start Example
 *
 * Build: gcc -O2 -o basic_usage examples/basic_usage.c src/rvdon_kahan.c -lm -Iinclude
 * Run:   ./basic_usage
 *
 * Copyright (c) 2026 DiVo Gen²AI. Licensed under MIT.
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "rvdon_kahan.h"

int main(void) {
    printf("RVDon Kahan — Basic Usage Example\n");
    printf("Library version: %s\n", rvdon_kahan_version());
    printf("Build: %s\n\n", rvdon_kahan_build_info());

    int N = 4;
    float coords[] = {
         0.0f,  0.0f,  0.0f,
         5.26f, 0.0f,  0.0f,
         0.0f,  5.26f, 0.0f,
         0.0f,  0.0f,  5.26f,
    };
    float sigma   = 3.4f;
    float epsilon = 0.01f;
    float r_cut   = 12.0f;

    rvdon_force_acc_t **forces = rvdon_force_batch_create(N);

    float total_pe = 0.0f;
    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            float dx = coords[j*3+0] - coords[i*3+0];
            float dy = coords[j*3+1] - coords[i*3+1];
            float dz = coords[j*3+2] - coords[i*3+2];
            float fx, fy, fz;
            float pe = rvdon_lj_force(dx, dy, dz, sigma, epsilon, r_cut, &fx, &fy, &fz);
            rvdon_force_accum_pair(forces, i, j, fx, fy, fz);
            printf("  Pair (%d,%d): r=%.3f, PE=%.6e\n",
                   i, j, sqrtf(dx*dx + dy*dy + dz*dz), pe);
            total_pe += pe;
        }
    }

    printf("\nTotal potential energy: %.10e\n", total_pe);
    printf("\nForces (Kahan-compensated):\n");
    for (int i = 0; i < N; i++) {
        float fx, fy, fz;
        rvdon_force_acc_get(forces[i], &fx, &fy, &fz);
        printf("  Atom %d: F = (%.6e, %.6e, %.6e)  |F| = %.6e\n",
               i, fx, fy, fz, sqrtf(fx*fx + fy*fy + fz*fz));
    }

    rvdon_force_batch_destroy(forces, N);
    printf("\nRVDon Kahan — FP64-equivalent precision on FP32 hardware.\n");
    return 0;
}
