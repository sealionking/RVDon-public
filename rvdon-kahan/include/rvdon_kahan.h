/**
 * rvdon_kahan.h — RVDon Kahan Public API
 *
 * Kahan compensated summation for FP32-precision force accumulation.
 * Achieves near-FP64 accuracy on FP32 hardware with zero hardware changes.
 *
 * Copyright (c) 2026 DiVo Gen²AI
 *
 * Licensed under the MIT License. See LICENSE file for details.
 *
 * ⚠️ Do NOT compile with -ffast-math. Kahan compensated summation relies on
 * IEEE 754 arithmetic semantics. -ffast-math permits reordering of
 * floating-point operations, which destroys the compensation and degrades
 * accuracy to naive FP32 level.
 */

#ifndef RVDON_KAHAN_H
#define RVDON_KAHAN_H

#ifdef __cplusplus
extern "C" {
#endif

/* ===================================================================
 * Opaque Types
 * =================================================================== */

typedef struct rvdon_kahan_s rvdon_kahan_t;
typedef struct rvdon_force_acc_s rvdon_force_acc_t;

/* ===================================================================
 * Scalar Kahan Accumulator
 * =================================================================== */

rvdon_kahan_t* rvdon_kahan_create(void);
void rvdon_kahan_destroy(rvdon_kahan_t *acc);
void rvdon_kahan_add(rvdon_kahan_t *acc, float x);
float rvdon_kahan_get(const rvdon_kahan_t *acc);
void rvdon_kahan_reset(rvdon_kahan_t *acc);

/* ===================================================================
 * 3D Force Vector Accumulator
 * =================================================================== */

rvdon_force_acc_t* rvdon_force_acc_create(void);
void rvdon_force_acc_destroy(rvdon_force_acc_t *acc);
void rvdon_force_accum(rvdon_force_acc_t *acc, float fx, float fy, float fz);
void rvdon_force_acc_get(const rvdon_force_acc_t *acc,
                          float *fx, float *fy, float *fz);
void rvdon_force_acc_reset(rvdon_force_acc_t *acc);

/* ===================================================================
 * Batch Operations (N atoms)
 * =================================================================== */

rvdon_force_acc_t** rvdon_force_batch_create(int N);
void rvdon_force_batch_destroy(rvdon_force_acc_t **acc, int N);
void rvdon_force_accum_pair(rvdon_force_acc_t **forces, int i, int j,
                             float fx, float fy, float fz);

/* ===================================================================
 * MD Force Functions
 * =================================================================== */

/**
 * Lennard-Jones force between two atoms.
 * V(r) = 4ε[(σ/r)¹² - (σ/r)⁶]
 * F_i = -24ε/r²·(2(σ/r)¹² - (σ/r)⁶)·(dx,dy,dz)
 */
float rvdon_lj_force(float dx, float dy, float dz,
                      float sigma, float epsilon, float r_cut,
                      float *fx, float *fy, float *fz);

/**
 * All pairwise LJ forces with Kahan-compensated accumulation.
 * Uses triangle symmetry (j > i) for 50% computation savings.
 */
float rvdon_lj_forces_kahan(const float *coords, int N,
                              float sigma, float epsilon, float r_cut,
                              rvdon_force_acc_t **forces);

/**
 * Buckingham force between two atoms.
 * V(r) = A·exp(-r/ρ) - C/r⁶
 */
float rvdon_buckingham_force(float dx, float dy, float dz,
                              float A, float rho, float C, float r_cut,
                              float *fx, float *fy, float *fz);

/* ===================================================================
 * Version & Build Info
 * =================================================================== */

const char* rvdon_kahan_version(void);
const char* rvdon_kahan_build_info(void);

#ifdef __cplusplus
}
#endif

#endif /* RVDON_KAHAN_H */
