# 数据清单

Phase 1 下载数据时逐条登记；写入论文的每个数据文件必须在此有记录。

## 已登记（2026-07-03，Phase 1）

| 文件 | 来源 | 版本/发布日期 | SHA256 | 备注 |
|---|---|---|---|---|
| `cobaya_packages/data/bao_data/desi_bao_dr2/desi_gaussian_bao_ALL_GCcomb_mean.txt` | CobayaSampler/bao_data（DESI DR2 官方压缩测量，arXiv:2503.14738） | bao_data v2.6 | `9ac154ab583ce759c0f7eef3c978c7c70a6ead2d18774caceadf1a350a640585` | 7 个红移 bin、13 个测量值（D_V/r_d, D_M/r_d, D_H/r_d），已逐条与 DR2 论文核对 |
| `cobaya_packages/data/bao_data/desi_bao_dr2/desi_gaussian_bao_ALL_GCcomb_cov.txt` | 同上 | bao_data v2.6 | `252a143274c8a07c78694c119617d36594f6d7965d00319ca611c6ffb886e509` | 13×13 协方差 |
| `cobaya_packages/data/sn_data/PantheonPlus/Pantheon+SH0ES.dat` | CobayaSampler/sn_data（Brout et al. 2022, arXiv:2202.04077） | sn_data（cobaya 3.6.2 安装） | `1cb0fc379ef066afdc2ffd1857681cc478024570d8a3eba284fb645775198cf8` | 1701 条光变曲线距离模数；D0 用 SH0ES 变体，D1 用 z>0.01 截断 + M_B 边缘化 |
| `cobaya_packages/data/sn_data/PantheonPlus/Pantheon+SH0ES_STAT+SYS.cov` | 同上 | 同上 | `abf806d966485e64afdb359c87bffc0ecc00d05eff0a31ced66f247385df0fdc` | 完整 stat+sys 协方差 |

## D5 轴 SN 备选样本（2026-07-03 登记）

| 文件 | 来源 | SHA256 | 备注 |
|---|---|---|---|
| `sn_data/Union3/lcparam_full.txt` | Rubin et al.（Union3/UNITY，2087 SNe，SALT3） | `a840fe71c606bda11b869dbfcacc21c0199a5dc393f3790d10a7b58de97deae7` | 分 bin 距离模数 |
| `sn_data/Union3/mag_covmat.txt` | 同上 | `64c79abd24bf5154bc1e38ad0c031e31dd6247cdcc5ca930829698169809a146` | |
| `sn_data/DES-Dovekie/DES-Dovekie_HD.csv` | DES-Dovekie 重校准（1623 DES + 197 低 z） | `c614821f2108f97279b753d1376b4200006ab0e95ab218d081db733fe7afd372` | |
| `sn_data/DES-Dovekie/covtot_inv_000.npz` | 同上 | `ffd3124b32148b1372bd95fda9299269f0352a9f8eee02d416c610e38495463b` | 逆协方差 |

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
| numpy / scipy | 2.5.0 / 1.16.2（scipy 钉在 1.16.2：scipy 1.18 回归缺陷（scipy#25471,BivariateSpline 标量输入返回 (1,) 数组）;camb 已在 master 提交 workaround(137e0f5,见 CAMB#202),下版发布后可解钉） |

SN/BAO 似然使用 cobaya 内置实现（`sn.pantheonplus`, `sn.pantheonplusshoes`, `bao.desi_dr2`）；D5 备选 `sn.union3`, `sn.desy5` 同已随包可用。

## DESI DR2 官方宇宙学链（2026-07-06 登记）

来源:`https://data.desi.lbl.gov/public/papers/y3/bao-cosmo-params/cobaya/base_w_wa/desi-bao-all_pantheonplus_planck2018-lowl-TT-clik_planck2018-lowl-EE-clik_planck-NPIPE-highl-CamSpec-TTTEEE_planck-act-dr6-lensing/`
（公开,免账号;官方 SHA256 清单同目录 `dr2_vac_dr2_bao-cosmo-params_v1.0.sha256sum`）。
本地:`runs/gate1/official/chain.{1-4}.txt` + margestats + updated.yaml。
逐链 SHA256：

| 文件 | SHA256 |
|---|---|
| `chain.1.txt` | `db81d299d59051ae5e1e8f67952320e08a1644a4a1f8d19267705aee32798877` |
| `chain.2.txt` | `442390266f6a3bfe88e9c7cd8e29d1e7cff47fc8582f3a3af80a6b40b9f83939` |
| `chain.3.txt` | `1c92edf523df34784633f6852f7564f3d953203ae939d5d2e8cd4c3fd6f580ae` |
| `chain.4.txt` | `b17dc02689c3a30dd34a96d91ac35180006f17d10b82331396ef55ce999594af` |

用途:Gate 1 链级验证。

### DESI DR2 官方 posterior-maximization 基准（2026-08-13，F0 解盲后登记）

WP4 F0 完成冻结的外部停止审计、并由作者明确授权解盲后，补存同一数据组合
的 DESI 官方 `iminuit` posterior-maximization 产物。两份文件均从官方公开
目录逐字节下载并以远端流 SHA256 复核；它们只用于 §7 的 CPL 相对
ΛCDM `Delta chi2` 复现门，不参与采样、停止或 fate 分类。

| 模型 | 本地文件 | SHA256 | likelihood `chi2` |
|---|---|---|---:|
| flat CPL (`base_w_wa`) | `runs/gate1/official_bestfits/base_w_wa/bestfit.minimum.txt` | `2eb4d1a0679b85ea759e558bba75c82348e09d58b04cdf84b9d252f227ece6c6` | 12394.829 |
| flat ΛCDM (`base`) | `runs/gate1/official_bestfits/base/bestfit.minimum.txt` | `4ac3b96a23ec55de34b64de667ba8efb4243b351485c289b5d58bbef1655a58b` | 12404.756 |

来源根目录：
`https://data.desi.lbl.gov/public/papers/y3/bao-cosmo-params/iminuit/`；
各模型下的数据组合目录均为
`desi-bao-all_pantheonplus_planck2018-lowl-TT-clik_planck2018-lowl-EE-clik_planck-NPIPE-highl-CamSpec-TTTEEE_planck-act-dr6-lensing/`。
官方基准定义为各模型 posterior maximum 处的 likelihood chi-square 差，
`Delta chi2 = chi2_CPL - chi2_LCDM = -9.927`；负值偏向 CPL。

## WP4 full-CMB F0（2026-07-27，采样前登记）

目标组合与 `plan/PRD_EXTENSION_PROTOCOL.md` §7 一致：DESI DR2 all BAO、
Pantheon+（不含 SH0ES）、Planck 2018 low-l TT/EE `clik`、Planck NPIPE
high-l CamSpec TTTEEE、Planck+ACT DR6 lensing。此节登记时尚未运行 F0
采样，也未计算任何 fate 端点。

本节及其所列静态配置、清单和预检产物均在 F0 driver 启动前于本机生成；
Git 静态检查点则是在 F0 已开始运行后补交，因此 Git 提交时间不作为独立的
采样前时间戳。冻结内容由 `f0/run_plan.json` 中的逐文件哈希核验。

### 官方参考配置和目标链

- 官方配置：`runs/gate1/official/chain.updated.yaml`，SHA256
  `ce490ac81bd61fa3ca65738666dde4a1f3d07c64983fdc0d2646cdab1a9a14b9`。
  该文件完整保留官方 likelihood 组件、CAMB 精度、采样设置、17 个自由参数
  及全部 nuisance prior。
- 官方运行版本：Cobaya 3.5、CAMB 1.5.4、ACT likelihood v1.2。
- 本机复现环境：Cobaya 3.6.2、CAMB 1.6.6、clipy-like 0.15、
  act-dr6-lenslike 1.2.1。低多极 `clik` 数据仍为 Planck R3.00 官方
  `.clik` payload；Cobaya 3.6.2 通过纯 Python clipy 0.15 读取。
- 公开组件名规范化：官方内部
  `desi_y3_cosmo_bindings...desi_bao_all` 映射为公开
  `bao.desi_dr2.desi_bao_all`；官方并存版本别名
  `act_dr6_lenslike_v1_2.ACTDR6LensLike` 映射为公开且锁定版本的
  `act_dr6_lenslike.ACTDR6LensLike`。这些是路径/包名规范化，不改变
  数据组合；数值等价性由 F0 的冻结阈值判断，不预先假定。

官方 nuisance prior（逐项来自上述已哈希配置）：

| 参数 | prior / 固定值 |
|---|---|
| `A_planck` | Normal(1, 0.0025) |
| `amp_143`, `amp_217`, `amp_143x217` | Uniform(0, 50) |
| `n_143`, `n_217`, `n_143x217` | Uniform(0, 5) |
| `calTE`, `calEE` | Normal(1, 0.01) |
| `use_fg_residual_model`, `amp_100` | 0 |
| `cal0`, `cal2`, `n_100` | 1 |

### 输入文件逐文件哈希

逐文件路径、字节数和 SHA256 登记于
`runs/prd_extension/wp4_full_cmb/input_manifest.json`；该 JSON 的 SHA256
为 `ab3694ed03dcaa7a1c5190d95f679d041d8a4f189d1fe7fe47d6ab5760c75614`。
共 1305 个唯一文件、3,577,141,302 bytes；按
`path + NUL + bytes + NUL + sha256 + LF` 排序计算的总树哈希为
`3414342f1963062afa0da43ddc26802af7c0851888feb8667ebc5c431539b531`。

| 输入组 | 来源/版本 | 文件数 | 树 SHA256 |
|---|---|---:|---|
| DESI DR2 BAO | CobayaSampler/bao_data v2.6 | 2 | `b2f535cc46f11c3dbd621030df7100fcbcb096c1a398e3a9c1c02bba335227dc` |
| Pantheon+ | CobayaSampler/sn_data v1.8 | 3 | `2eaca17f999fca1fddf37ca59efe756c19c0a277e68183922ad40d41133655d2` |
| Planck 2018 low-l TT/EE | PLA baseline R3.00，product 151902 | 294 | `bbb4b3faa858cfccca0d2a30d08722db53d036a685f6c286b54b3576112f72c4` |
| Planck supplementary | CobayaSampler/planck_supp_data_and_covmats v2.1 | 960 | `9d41e0d054b4908eb36e86c39848713ee57efd5311eec02071036d22f2d6ec03` |
| Planck NPIPE CamSpec | CobayaSampler/planck_native_data v1，`CamSpec_NPIPE.zip` | 15 | `e8d9ba7ee24361201ae4d409bbc416cbe2ddaf1d33360af3b0594814c721349e` |
| ACT DR6 lensing | NASA LAMBDA `ACT_dr6_likelihood_v1.2.tgz` | 31 | `20490efd1a2e60b5d3b08710bda06616a4daa82b64a917271e4107d1ff42c414` |

安装来源：

- Planck R3.00：`https://pla.esac.esa.int/pla-sl/data-action?COSMOLOGY.COSMOLOGY_OID=151902`
- NPIPE CamSpec：`https://github.com/CobayaSampler/planck_native_data/releases/tag/v1`
- ACT DR6 v1.2：`https://lambda.gsfc.nasa.gov/data/suborbital/ACT/ACT_dr6/likelihood/data/ACT_dr6_likelihood_v1.2.tgz`
