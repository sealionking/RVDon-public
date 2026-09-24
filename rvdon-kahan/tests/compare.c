/**
 * compare.c — Track3 测试 harness
 *
 * 对三组测试向量运行 C 实现（Kahan + naive FP32），输出结果供对比。
 *
 * 编译: make
 * 运行: ./compare
 *
 * 输出: c_result_v1.csv, c_result_v2.csv, c_result_v3.csv
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "rvdon_kahan.h"

/* ===================================================================
 * 辅助：CSV 读取
 * =================================================================== */

static FILE* open_csv(const char *path, const char *mode)
{
    FILE *f = fopen(path, mode);
    if (!f) {
        fprintf(stderr, "ERROR: cannot open %s\n", path);
        exit(1);
    }
    return f;
}

static void skip_header(FILE *f)
{
    int c;
    while ((c = fgetc(f)) != EOF && c != '\n')
        ;
}

/* ===================================================================
 * V1: 标量压测
 * =================================================================== */

static void test_v1(const char *vectors_dir, const char *out_dir)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/v1_scalar.csv", vectors_dir);
    FILE *in = open_csv(path, "r");
    skip_header(in);

    /* Kahan 累加器 */
    rvdon_kahan_t *kahan = rvdon_kahan_create();

    /* naive FP32 累加 */
    float naive_sum = 0.0f;

    int idx;
    float val;
    int count = 0;

    while (fscanf(in, "%d,%f", &idx, &val) == 2) {
        rvdon_kahan_add(kahan, val);
        naive_sum += val;
        count++;
    }

    float kahan_sum = rvdon_kahan_get(kahan);

    /* 输出 */
    snprintf(path, sizeof(path), "%s/c_result_v1.csv", out_dir);
    FILE *out = open_csv(path, "w");
    fprintf(out, "method,sum,count\n");
    fprintf(out, "kahan_f32,%.15e,%d\n", (double)kahan_sum, count);
    fprintf(out, "naive_f32,%.15e,%d\n", (double)naive_sum, count);
    fclose(out);

    printf("V1: %d 条\n", count);
    printf("  Kahan f32 = %.15e\n", (double)kahan_sum);
    printf("  Naive f32 = %.15e\n", (double)naive_sum);

    rvdon_kahan_destroy(kahan);
    fclose(in);
}

/* ===================================================================
 * V2: LJ 系统（128 原子）
 * =================================================================== */

static void test_v2(const char *vectors_dir, const char *out_dir)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/v2_lj128.csv", vectors_dir);
    FILE *in = open_csv(path, "r");
    skip_header(in);

    int n = 128;
    float *coords = (float *)malloc((size_t)n * 3 * sizeof(float));

    int idx;
    for (int i = 0; i < n; i++) {
        if (fscanf(in, "%d,%f,%f,%f",
                   &idx, &coords[i*3], &coords[i*3+1], &coords[i*3+2]) != 4) {
            fprintf(stderr, "ERROR: failed to read atom %d coordinates\n", i);
            exit(1);
        }
    }
    fclose(in);

    /* Kahan 路径 */
    rvdon_force_acc_t **forces_kahan = rvdon_force_batch_create(n);
    float pe_kahan = rvdon_lj_forces_kahan(coords, n, 3.4f, 0.01f, 12.0f, forces_kahan);

    /* Naive FP32 路径（直接累加，无补偿） */
    float *naive_forces = (float *)calloc((size_t)n * 3, sizeof(float));
    float naive_pe = 0.0f;

    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            float dx = coords[j*3]   - coords[i*3];
            float dy = coords[j*3+1] - coords[i*3+1];
            float dz = coords[j*3+2] - coords[i*3+2];
            float fx, fy, fz;
            float pe = rvdon_lj_force(dx, dy, dz, 3.4f, 0.01f, 12.0f, &fx, &fy, &fz);

            if (pe != 0.0f) {
                naive_pe += pe;
                naive_forces[i*3]   += fx;
                naive_forces[i*3+1] += fy;
                naive_forces[i*3+2] += fz;
                naive_forces[j*3]   -= fx;
                naive_forces[j*3+1] -= fy;
                naive_forces[j*3+2] -= fz;
            }
        }
    }

    /* 牛顿第三定律检查 */
    float net_fx = 0, net_fy = 0, net_fz = 0;
    for (int i = 0; i < n; i++) {
        float fx, fy, fz;
        rvdon_force_acc_get(forces_kahan[i], &fx, &fy, &fz);
        net_fx += fx;
        net_fy += fy;
        net_fz += fz;
    }

    /* 输出 */
    snprintf(path, sizeof(path), "%s/c_result_v2.csv", out_dir);
    FILE *out = open_csv(path, "w");
    fprintf(out, "atom_id,fx_kahan,fy_kahan,fz_kahan,fx_naive,fy_naive,fz_naive\n");
    for (int i = 0; i < n; i++) {
        float fx, fy, fz;
        rvdon_force_acc_get(forces_kahan[i], &fx, &fy, &fz);
        fprintf(out, "%d,%.15e,%.15e,%.15e,%.15e,%.15e,%.15e\n",
                i, (double)fx, (double)fy, (double)fz,
                (double)naive_forces[i*3],
                (double)naive_forces[i*3+1],
                (double)naive_forces[i*3+2]);
    }
    fprintf(out, "# total_pe_kahan,%.15e\n", (double)pe_kahan);
    fprintf(out, "# total_pe_naive,%.15e\n", (double)naive_pe);
    fprintf(out, "# net_force_kahan,%.15e,%.15e,%.15e\n",
            (double)net_fx, (double)net_fy, (double)net_fz);
    fclose(out);

    printf("V2: %d 原子 LJ 系统\n", n);
    printf("  Kahan PE = %.15e\n", (double)pe_kahan);
    printf("  Naive PE = %.15e\n", (double)naive_pe);
    printf("  Net force (Kahan) = (%.6e, %.6e, %.6e)\n",
           (double)net_fx, (double)net_fy, (double)net_fz);

    rvdon_force_batch_destroy(forces_kahan, n);
    free(naive_forces);
    free(coords);
}

/* ===================================================================
 * V3: Buckingham 力
 * =================================================================== */

static void test_v3(const char *vectors_dir, const char *out_dir)
{
    char path[512];
    snprintf(path, sizeof(path), "%s/v3_buckingham.csv", vectors_dir);
    FILE *in = open_csv(path, "r");
    skip_header(in);

    snprintf(path, sizeof(path), "%s/c_result_v3.csv", out_dir);
    FILE *out = open_csv(path, "w");
    fprintf(out, "pair_id,pe_kahan,fx_kahan,fy_kahan,fz_kahan\n");

    printf("V3: Buckingham 力\n");

    int pair_id;
    float dx, dy, dz, A, rho, C, r_cut;
    char line[512];

    while (fgets(line, sizeof(line), in)) {
        if (sscanf(line, "%d,%f,%f,%f,%f,%f,%f,%f",
                   &pair_id, &dx, &dy, &dz, &A, &rho, &C, &r_cut) == 8) {
            float fx, fy, fz;
            float pe = rvdon_buckingham_force(dx, dy, dz, A, rho, C, r_cut,
                                               &fx, &fy, &fz);
            fprintf(out, "%d,%.15e,%.15e,%.15e,%.15e\n",
                    pair_id, (double)pe, (double)fx, (double)fy, (double)fz);
            printf("  pair %2d: pe=%.10e  F=(%.6e, %.6e, %.6e)\n",
                   pair_id, (double)pe, (double)fx, (double)fy, (double)fz);
        }
    }

    fclose(out);
    fclose(in);
}

/* ===================================================================
 * 主函数
 * =================================================================== */

int main(int argc, char **argv)
{
    const char *vectors_dir = "tests/vectors";
    const char *out_dir = "tests";

    if (argc >= 2) vectors_dir = argv[1];
    if (argc >= 3) out_dir = argv[2];

    printf("=== RVDon Kahan Track3 测试 harness ===\n");
    printf("Version: %s\n", rvdon_kahan_version());
    printf("Build: %s\n\n", rvdon_kahan_build_info());

    test_v1(vectors_dir, out_dir);
    printf("\n");
    test_v2(vectors_dir, out_dir);
    printf("\n");
    test_v3(vectors_dir, out_dir);
    printf("\n=== 测试完毕 ===\n");

    return 0;
}
