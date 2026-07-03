# 数据清单

Phase 1 下载数据时逐条登记；写入论文的每个数据文件必须在此有记录。

## 已登记（2026-07-03，Phase 1）

| 文件 | 来源 | 版本/发布日期 | SHA256 | 备注 |
|---|---|---|---|---|
| `cobaya_packages/data/bao_data/desi_bao_dr2/desi_gaussian_bao_ALL_GCcomb_mean.txt` | CobayaSampler/bao_data（DESI DR2 官方压缩测量，arXiv:2503.14738） | bao_data v2.6 | `9ac154ab…640585` | 7 个红移 bin、13 个测量值（D_V/r_d, D_M/r_d, D_H/r_d），已逐条与 DR2 论文核对 |
| `cobaya_packages/data/bao_data/desi_bao_dr2/desi_gaussian_bao_ALL_GCcomb_cov.txt` | 同上 | bao_data v2.6 | `252a1432…886509` | 13×13 协方差 |
| `cobaya_packages/data/sn_data/PantheonPlus/Pantheon+SH0ES.dat` | CobayaSampler/sn_data（Brout et al. 2022, arXiv:2202.04077） | sn_data（cobaya 3.6.2 安装） | `1cb0fc37…198cf8` | 1701 条光变曲线距离模数；D0 用 SH0ES 变体，D1 用 z>0.01 截断 + M_B 边缘化 |
| `cobaya_packages/data/sn_data/PantheonPlus/Pantheon+SH0ES_STAT+SYS.cov` | 同上 | 同上 | `abf806d9…5df0fdc` | 完整 stat+sys 协方差 |

## D5 轴 SN 备选样本（2026-07-03 登记）

| 文件 | 来源 | SHA256（前 10 位） | 备注 |
|---|---|---|---|
| `sn_data/Union3/lcparam_full.txt` | Rubin et al.（Union3/UNITY，2087 SNe，SALT3） | `a840fe71c6…` | 分 bin 距离模数 |
| `sn_data/Union3/mag_covmat.txt` | 同上 | `64c79abd24…` | |
| `sn_data/DES-Dovekie/DES-Dovekie_HD.csv` | DES-Dovekie 重校准（1623 DES + 197 低 z） | `c614821f21…` | |
| `sn_data/DES-Dovekie/covtot_inv_000.npz` | 同上 | `ffd3124b32…` | 逆协方差 |

均经 cobaya 3.6.2 官方安装器获取（`sn.union3`, `sn.desdovekie`）。

## CMB 压缩距离先验（数值直接登记）

出处：**Chen, Huang & Wang 2018, arXiv:1808.05724《Distance Priors from Planck Final Release》Table I，ΛCDM 行，Planck 2018 TT,TE,EE+lowE**。
该文 §II C 用 wCDM 与 CPL 模型验证了此先验与完整 Planck 拟合一致（我们计划 §3 的适用性声明引用此节）。

均值与 1σ（取 (R, ℓ_A, Ω_b h²) 三参数子集，ℓ_A 误差对称化取 0.090）：

```
R      = 1.7502  ± 0.0046
ℓ_A    = 301.471 ± 0.090
Ω_b h² = 0.02236 ± 0.00015
```

相关矩阵（顺序 R, ℓ_A, Ω_b h²）：

```
 1.00   0.46  -0.66
 0.46   1.00  -0.33
-0.66  -0.33   1.00
```

理论侧按该文 (1)–(6) 式计算 R、ℓ_A：z_* 用其 (8)–(10) 式的拟合公式，
r_s 数值积分（3/(4Ω_γh²)=31500(T/2.7)⁻⁴，T=2.7255 K），
Ω_r 按 z_eq=2.5×10⁴ Ω_m h²(T/2.7)⁻⁴。实现于 `pipeline/cmb_distprior.py`。

**约定一致性教训（Phase 1 记录）**：先验抽取端与理论预测端必须用同一套 z_*/r_s 公式。
曾试用 CAMB 精确复合史的 z_* 与 r_*，在 Planck 2018 ΛCDM 均值点上 ℓ_A 系统偏高 0.27（≈3σ）——
纯约定差异，不是物理。切换为论文自带拟合公式后同一点 χ²=1.66（3 个数据点），通过。

## 软件环境（Phase 1 定型）

| 组件 | 版本 |
|---|---|
| Python | 3.13.13 (arm64 venv `.venv`) |
| cobaya | 3.6.2 |
| camb | 1.6.6 |
| dynesty | 3.0.0 |
| getdist | 1.7.7 |
| numpy / scipy | 2.5.0 / 1.16.2（scipy 钉在 1.16.2：1.18 的插值返回形状变化使 camb 1.6.6 的 BBN YHe setter 报错） |

SN/BAO 似然使用 cobaya 内置实现（`sn.pantheonplus`, `sn.pantheonplusshoes`, `bao.desi_dr2`）；D5 备选 `sn.union3`, `sn.desy5` 同已随包可用。
