# 交接文档（2026-07-21，v1.1 大修候选）

本仓库是 `cosmo_fate` 的可复现研究工作区。冻结预注册仍由 tag
`prereg-v1` 定义；A-001--A-003 是生效修订，A-004 是明确标注的事后结构审计，
不是第四项预注册修订。

## 一、当前结论边界

| 项目 | 当前状态 |
|---|---|
| Gate 1 | 通过；压缩 CMB 管线与官方 DESI DR2 链在声明精度内一致 |
| Gate 2 | 100 个有噪声 mock + mock000 完成；方向统计量与 `U(0,1)` 相容 |
| D0 CPL | `P(RIP)=0.18%`；nested 点估计 `0.165%`；证据偏向 LCDM |
| 数据/先验/统计量轴 | 已完成并进入正文 |
| 参数化轴 | 四个收敛拟合 CPL/JBP/BA/BIN4；GP 只保留构造性反例 |
| 约束视界 | 注册的 `a_h` 未达到；`a=1` 仅为直接观测支持边界 |
| A-004 | matched-prior 重要性重加权全局 No-Go；不报告 matched 概率 |

论文的硬边界：结果使用 Planck 距离先验而非完整 CMB 谱似然；100→500 mocks、
off-boundary 功效战役、完整 Planck/ACT 与增长数据均属于后续加强，不是 v1.1
已经完成的证据。

## 二、复现与测试

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/cobaya-install sn.pantheonplus sn.pantheonplusshoes sn.union3 sn.desdovekie \
  bao.desi_dr2 --packages-path data/cobaya_packages

.venv/bin/python -m pytest -q pipeline/test_fate.py pipeline/test_append_mocks.py \
  pipeline/test_nested_interface.py pipeline/test_matched_prior_audit.py
.venv/bin/python pipeline/constraint_horizon_audit.py
.venv/bin/python pipeline/prior_fate_audit.py --n 2000000
.venv/bin/python pipeline/inwindow_fit_audit.py
.venv/bin/python pipeline/model_average_audit.py
.venv/bin/python pipeline/matched_prior_audit.py --n 20000
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

v1.0 是 2026-07-13 的原始 submission archive。v1.1 目标是纳入大修解释、
A-004 No-Go、mock 安全工具、nested 接口与扩展 CI。发布时必须确认 GitHub release、
Zenodo 新版本、PDF 和源码来自同一提交。

## 五、后续加强（不计入 v1.1 已完成工作）

1. 追加并运行 400 个 mock，把 null 战役扩展到 500。
2. 设计 off-boundary 真值轴，测量方向/深度统计量的功效。
3. 用固定种子的共享 nested 接口重跑关键 D0 与跨语法结果，必要时做多种子复核。
4. 对 D0/CPL 和 BIN4 做有限范围完整 Planck(+lensing) 检验。
5. 将共同生成式函数先验或正规化 GP 超先验作为独立后续研究。
