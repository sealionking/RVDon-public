# TRACK.md — 本目录的轨道身份

> 2026-09-15 标注

## 身份：Track-RT（红队轨）

本目录是 2026-07-07 红队仅凭公开材料（rvdon_kahan.h + 文档）独立重写的实现，
**不是教授闭源 drop 的衍生物**，与 `rvdon-kahan/vendor-prof/` 无血缘关系。

## 在 rvdon-kahan 四轨体系中的位置

| 轨 | 位置 | 角色 | 状态 |
|:---|:---|:---|:---|
| Track1 | `rvdon-kahan/vendor-prof/` | 教授闭源参考 | 只读存档，禁止进 release |
| Track2 | `rvdon-kahan/divo/` | DiVo clean-room 正轨 | Apache-2.0，活跃 |
| Track3 | `rvdon-kahan/track3-trae/` | 盲测独立验证轨 | 已验收（c7226ca closed） |
| **Track-RT** | **本目录** | 红队验证轨 | 长期对照 |

## 历史意义

本实现是**最早使用正确力方向符号约定的轨道**（`src/rvdon_lj.c` L53-60，
`f_over_r = -f_mag * r_inv`）。2026-09-15 三轨对拍发现 Track1/Track2 共享
符号错误时，本目录与 Track3 共同构成正确性证据。

## 使用规则

- 作为交叉验证的第四轨保留，**不再演进**（功能演进走 Track2）
- 其测试（test_kahan/test_lj/test_drift/test_buckingham）仍可用于回归
- 注意一个边界差异：cutoff 判定为 `r2 >= r_cut²`（不含等号），其他轨为 `r > r_cut`（含等号）——仅在 r 恰好等于 r_cut 时有差异
