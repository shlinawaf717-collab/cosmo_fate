# 交接文档（2026-07-21，v1.2 科学纠错版）

> 2026-07-22 状态：完成的 v1.x 基线固定于 commit `70a47ec` 和 tag
> `paper-v1x-final-20260722`。后续 PRD 强化研究不修改该历史，执行前以
> `plan/PRD_EXTENSION_PROTOCOL.md` 和
> `plan/prd_extension_protocol.json` 为准；新结果只进入
> `runs/prd_extension/`。

本仓库是 `cosmo_fate` 的可复现研究工作区。冻结预注册由本地 Git commit
`98abc20` 和 tag `prereg-v1` 定义，记录时间为 2026-07-03 10:26；首个终局结果
commit `76ed25d` 记录于 11:29，且前者是后者的祖先。公共仓库随后建立，因此论文
称其为“本地版本控制预注册”，不冒充第三方平台注册。完整溯源见
`plan/PREREGISTRATION_PROVENANCE.md`。其精确范围是对既有公开数据所做终局翻译
审计的本地预注册，不声称早于数据接触。A-001--A-003 是生效的预注册计划修订，
A-004--A-007 是明确标注的事后审计、纠错或实现溯源记录，不是新增预注册修订。

## 一、当前结论边界

| 项目 | 当前状态 |
|---|---|
| Gate 1 | 通过；压缩 CMB 管线与官方 DESI DR2 链在声明精度内一致 |
| Gate 2 | 100 个有噪声 mock + mock000 完成；方向统计量与 `U(0,1)` 相容 |
| D0 CPL | MCMC `P(RIP)=0.18%`；nested 原始权重三种子均值 `0.179%`、种子间 SD `0.039` 个百分点 |
| 数据轴 | D0--D4 全部亚百分比；原始权重尾概率 `0.0008%--0.376%`，正式跨度 `2.665 dex` |
| 统计量轴 | `ln B(CPL/LCDM)=-1.617`，种子间 SD `0.224`；证据偏向 LCDM |
| 先验轴 | P2/P3 从定义上排除 RIP；注册跨度为无穷 |
| 参数化轴 | 四个收敛拟合 CPL/JBP/BA/BIN4；GP 只保留构造性反例 |
| 约束视界 | 注册的 `a_h` 未达到；`a=1` 仅为直接观测支持边界 |
| A-004 | matched-prior 重要性重加权全局 No-Go；不报告 matched 概率 |
| A-005 | 有限极限严格按 `w_inf=-1` 分界；BA/BIN4 RIP=1.34%/49.96%，DS=0 |
| A-006 | BIN4 早期暗能量硬门通过；full Planck 在当前背景接口上为 No-Go |
| A-007 | 逐语法 P1 早期条件的事后实现溯源；零分析与数值变动 |

论文的硬边界：结果使用 Planck 距离先验而非完整 CMB 谱似然；100→500 mocks、
off-boundary 功效战役、完整 Planck/ACT 与增长数据均属于后续加强，不是 v1.2
已经完成的证据。

## 二、复现与测试

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/cobaya-install sn.pantheonplus sn.pantheonplusshoes sn.union3 sn.desdovekie \
  bao.desi_dr2 --packages-path data/cobaya_packages

.venv/bin/python -m pytest -q pipeline/test_fate.py pipeline/test_append_mocks.py \
  pipeline/test_nested_interface.py pipeline/test_aggregate_nested_d0.py \
  pipeline/test_inwindow_fit_audit.py \
  pipeline/test_matched_prior_audit.py pipeline/test_fragility_audit.py \
  pipeline/test_early_de_gate.py
.venv/bin/python pipeline/constraint_horizon_audit.py
.venv/bin/python pipeline/prior_fate_audit.py --n 2000000
.venv/bin/python pipeline/inwindow_fit_audit.py
.venv/bin/python pipeline/model_average_audit.py
.venv/bin/python pipeline/matched_prior_audit.py --n 20000
.venv/bin/python pipeline/early_de_audit.py
.venv/bin/python pipeline/full_planck_feasibility_audit.py
.venv/bin/python pipeline/fragility_audit.py
.venv/bin/python pipeline/gen_paper_numbers.py
.venv/bin/python pipeline/audit_nested_archives.py
```

环境和数据版本以 `requirements.lock` 与 `data/MANIFEST.md` 为准。

## 三、mock 安全规则

`pipeline/make_mocks.py` 只允许初始化空目录；非空目录一律拒绝，不能覆盖包含
`chain.*`、checkpoint 或日志的现有 mock 目录。追加使用：

```bash
.venv/bin/python pipeline/append_mocks.py --append 10 --dry-run
.venv/bin/python pipeline/append_mocks.py --append 10
```

旧清单首次追加前必须通过精确 `m000` 重建检查；实际追加后才写入输入指纹及其
迁移来源。当前论文仍以完成的 100 个有噪声 mock 为准。

## 四、论文与发布

主文稿：`paper/main.tex`。数字由 `pipeline/gen_paper_numbers.py` 生成，图由
`pipeline/make_paper_figs.py` 生成。PDF 输出放在
`output/pdf/Zhang_cosmic_fate_audit_major_revision.pdf`。

v1.0 是 2026-07-13 的原始 submission archive。v1.1 纳入大修解释、A-004 No-Go、
mock 安全工具、nested 接口与扩展 CI；v1.1.1 仅把正文中的 v1.0 版本 DOI 改为稳定的
Zenodo 概念 DOI `10.5281/zenodo.21332433`，无科学内容变更。v1.2 修正 A-003
物理分类、A-004 BIN4 网格秩、nested 原始权重与多种子处理，补齐正式脆弱性指标、
修正图 4 的 nested/MCMC 数据口径，并加入 A-006 范围门。发布时必须确认 GitHub
release、Zenodo 新版本、PDF 和源码来自同一提交。
v1.2.1 仅把生成审计浮点数统一到跨 BLAS/NumPy 平台可复现的声明精度；
科学数字、正文和 PDF 均与 v1.2 相同。
当前修订分支位于 v1.2.1 之后：限定本地二次数据预注册范围，补 A-007、A-003
作废标识、正式文献元数据和 chain-minimum AIC 措辞；发布版本号由合并后另定。

## 五、后续加强（不计入 v1.2 已完成工作）

1. 追加并运行 400 个 mock，把 null 战役扩展到 500。
2. 设计 off-boundary 真值轴，测量方向/深度统计量的功效。
3. 为 BIN4 实现并验证 Boltzmann 扰动，再安装官方 Planck likelihood 做完整谱检验。
4. 将共同生成式函数先验或正规化 GP 超先验作为独立后续研究。
