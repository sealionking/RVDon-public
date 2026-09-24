/**
 * rvdon_kahan.c — Kahan Compensated Summation Library
 *
 * Implementation of the Kahan (1965) compensated summation algorithm for
 * molecular dynamics force accumulation on FP32 hardware.
 *
 * Copyright (c) 2026 DiVo Gen²AI
 *
 * Licensed under the MIT License. See LICENSE file for details.
 */

#ifdef __FAST_MATH__
#error "Compensated summation is unsafe with -ffast-math"
#endif

#include <stdlib.h>
#include <math.h>

#include "rvdon_kahan.h"

/* ===================================================================
 * Internal Structures
 * =================================================================== */

struct rvdon_kahan_s {
    float sum;
    float comp;
};

struct rvdon_force_acc_s {
    struct rvdon_kahan_s ax;
    struct rvdon_kahan_s ay;
    struct rvdon_kahan_s az;
};

#define RVDON_VERSION "1.0.0"
#define RVDON_BUILD_INFO "Kahan compensated; C99; IEEE 754"

/* ===================================================================
 * Scalar Kahan Accumulator
 * =================================================================== */

rvdon_kahan_t* rvdon_kahan_create(void)
{
    rvdon_kahan_t *acc = (rvdon_kahan_t *)malloc(sizeof(rvdon_kahan_t));
    if (acc) {
        acc->sum  = 0.0f;
        acc->comp = 0.0f;
    }
    return acc;
}

void rvdon_kahan_destroy(rvdon_kahan_t *acc)
{
    free(acc);
}

void rvdon_kahan_add(rvdon_kahan_t *acc, float x)
{
    if (!acc) return;
    float y = x - acc->comp;
    float t = acc->sum + y;
    acc->comp = (t - acc->sum) - y;
    acc->sum  = t;
}

float rvdon_kahan_get(const rvdon_kahan_t *acc)
{
    if (!acc) return 0.0f;
    return acc->sum;
}

void rvdon_kahan_reset(rvdon_kahan_t *acc)
{
    if (!acc) return;
    acc->sum  = 0.0f;
    acc->comp = 0.0f;
}

/* ===================================================================
 * 3D Force Vector Accumulator
 * =================================================================== */

rvdon_force_acc_t* rvdon_force_acc_create(void)
{
    rvdon_force_acc_t *acc = (rvdon_force_acc_t *)malloc(sizeof(rvdon_force_acc_t));
    if (acc) {
        acc->ax.sum = 0.0f;  acc->ax.comp = 0.0f;
        acc->ay.sum = 0.0f;  acc->ay.comp = 0.0f;
        acc->az.sum = 0.0f;  acc->az.comp = 0.0f;
    }
    return acc;
}

void rvdon_force_acc_destroy(rvdon_force_acc_t *acc)
{
    free(acc);
}

void rvdon_force_accum(rvdon_force_acc_t *acc, float fx, float fy, float fz)
{
    if (!acc) return;
    float y, t;

    y = fx - acc->ax.comp;
    t = acc->ax.sum + y;
    acc->ax.comp = (t - acc->ax.sum) - y;
    acc->ax.sum  = t;

    y = fy - acc->ay.comp;
    t = acc->ay.sum + y;
    acc->ay.comp = (t - acc->ay.sum) - y;
    acc->ay.sum  = t;

    y = fz - acc->az.comp;
    t = acc->az.sum + y;
    acc->az.comp = (t - acc->az.sum) - y;
    acc->az.sum  = t;
}

void rvdon_force_acc_get(const rvdon_force_acc_t *acc,
                          float *fx, float *fy, float *fz)
{
    if (!acc) {
        if (fx) *fx = 0.0f;
        if (fy) *fy = 0.0f;
        if (fz) *fz = 0.0f;
        return;
    }
    if (fx) *fx = acc->ax.sum;
    if (fy) *fy = acc->ay.sum;
    if (fz) *fz = acc->az.sum;
}

void rvdon_force_acc_reset(rvdon_force_acc_t *acc)
{
    if (!acc) return;
    acc->ax.sum = 0.0f;  acc->ax.comp = 0.0f;
    acc->ay.sum = 0.0f;  acc->ay.comp = 0.0f;
    acc->az.sum = 0.0f;  acc->az.comp = 0.0f;
}

/* ===================================================================
 * Batch Operations
 * =================================================================== */

rvdon_force_acc_t** rvdon_force_batch_create(int N)
{
    if (N <= 0) return NULL;

    rvdon_force_acc_t **batch =
        (rvdon_force_acc_t **)malloc((size_t)N * sizeof(rvdon_force_acc_t *));
    if (!batch) return NULL;

    for (int i = 0; i < N; i++) {
        batch[i] = rvdon_force_acc_create();
        if (!batch[i]) {
            for (int j = 0; j < i; j++)
                rvdon_force_acc_destroy(batch[j]);
            free(batch);
            return NULL;
        }
    }
    return batch;
}

void rvdon_force_batch_destroy(rvdon_force_acc_t **acc, int N)
{
    if (!acc) return;
    for (int i = 0; i < N; i++)
        rvdon_force_acc_destroy(acc[i]);
    free(acc);
}

void rvdon_force_accum_pair(rvdon_force_acc_t **forces, int i, int j,
                             float fx, float fy, float fz)
{
    rvdon_force_accum(forces[i],  fx,  fy,  fz);
    rvdon_force_accum(forces[j], -fx, -fy, -fz);
}

/* ===================================================================
 * MD Force Functions
 * =================================================================== */

float rvdon_lj_force(float dx, float dy, float dz,
                      float sigma, float epsilon, float r_cut,
                      float *fx, float *fy, float *fz)
{
    float r2 = dx*dx + dy*dy + dz*dz;
    float r  = sqrtf(r2);

    if (r > r_cut || r == 0.0f) {
        if (fx) *fx = 0.0f;
        if (fy) *fy = 0.0f;
        if (fz) *fz = 0.0f;
        return 0.0f;
    }

    float s  = sigma / r;
    float s2 = s * s;
    float s6 = s2 * s2 * s2;
    float s12 = s6 * s6;

    float pe = 4.0f * epsilon * (s12 - s6);

    float coef = 24.0f * epsilon / r2;
    float fmag = coef * (2.0f * s12 - s6);

    if (fx) *fx = -fmag * dx;
    if (fy) *fy = -fmag * dy;
    if (fz) *fz = -fmag * dz;

    return pe;
}

float rvdon_lj_forces_kahan(const float *coords, int N,
                              float sigma, float epsilon, float r_cut,
                              rvdon_force_acc_t **forces)
{
    if (!coords || N <= 0 || !forces) return 0.0f;

    rvdon_kahan_t *pe_acc = rvdon_kahan_create();
    if (!pe_acc) return 0.0f;

    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            float dx = coords[j*3+0] - coords[i*3+0];
            float dy = coords[j*3+1] - coords[i*3+1];
            float dz = coords[j*3+2] - coords[i*3+2];

            float fx, fy, fz;
            float pe = rvdon_lj_force(dx, dy, dz, sigma, epsilon, r_cut,
                                       &fx, &fy, &fz);

            float r2 = dx*dx + dy*dy + dz*dz;
            float r  = sqrtf(r2);
            if (r > 0.0f && r <= r_cut) {
                rvdon_kahan_add(pe_acc, pe);
                rvdon_force_accum_pair(forces, i, j, fx, fy, fz);
            }
        }
    }

    float total_pe = rvdon_kahan_get(pe_acc);
    rvdon_kahan_destroy(pe_acc);
    return total_pe;
}

float rvdon_buckingham_force(float dx, float dy, float dz,
                              float A, float rho, float C, float r_cut,
                              float *fx, float *fy, float *fz)
{
    float r2 = dx*dx + dy*dy + dz*dz;
    float r  = sqrtf(r2);

    if (r > r_cut || r == 0.0f) {
        if (fx) *fx = 0.0f;
        if (fy) *fy = 0.0f;
        if (fz) *fz = 0.0f;
        return 0.0f;
    }

    float expr = expf(-r / rho);
    float r6 = r2 * r2 * r2;
    float pe = A * expr - C / r6;

    float inv_r = 1.0f / r;
    float r7 = r6 * r;
    float dVdr = -A / rho * expr + 6.0f * C / r7;

    if (fx) *fx = dVdr * inv_r * dx;
    if (fy) *fy = dVdr * inv_r * dy;
    if (fz) *fz = dVdr * inv_r * dz;

    return pe;
}

/* ===================================================================
 * Version & Build Info
 * =================================================================== */

const char* rvdon_kahan_version(void)
{
    return RVDON_VERSION;
}

const char* rvdon_kahan_build_info(void)
{
    return RVDON_BUILD_INFO;
}
