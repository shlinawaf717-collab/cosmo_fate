# cosmo_fate — 动态暗能量下宇宙终局结论的脆弱性

预注册研究工作区。核心问题：在 SN + BAO + CMB 距离数据下，"宇宙热寂"结论对动态暗能量假设有多脆弱。

- `plan/ANALYSIS_PLAN.md` — 预注册分析计划（先验表、终局判据、数据组合、脆弱性度量、过关条件）。冻结后只能通过 `plan/AMENDMENTS.md` 修订。
- `pipeline/` — 似然、采样、终局分类器代码（Phase 1 起）
- `data/` — 数据文件与 `MANIFEST.md`（版本、来源、校验和）
- `runs/` — MCMC/nested sampling 输出，按 `<组合>_<模型>_<先验>` 命名
- `paper/` — 文稿

阶段路线：0 预注册（本阶段）→ 1 管线验证（Gate 1：复现 DESI DR2 已发表 w₀wₐCDM 结果）→ 2 全后验 + 终局分类 → 3 脆弱性量化（F_prior / F_param / F_data、mock 校准、约束视界）→ 4 写作。

## 复现（Reproduce）

```bash
# 环境（scipy 必须钉 1.16.2，原因见 data/MANIFEST.md）
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
.venv/bin/cobaya-install sn.pantheonplus sn.pantheonplusshoes sn.union3 sn.desdovekie \
    bao.desi_dr2 --packages-path data/cobaya_packages
# 数据校验：对照 data/MANIFEST.md 的 SHA256 逐条 shasum -a 256

.venv/bin/python pipeline/test_fate.py            # 分类器单元测试 8/8
.venv/bin/python pipeline/constraint_horizon_audit.py  # 重算注册 KL；a_h 未达到
.venv/bin/python pipeline/prior_fate_audit.py     # 各语法诱导的先验终局构成
.venv/bin/python pipeline/inwindow_fit_audit.py   # 四个已收敛语法的窗口内拟合审计
.venv/bin/python pipeline/model_average_audit.py  # 探索性 LCDM/CPL 模型平均
.venv/bin/python pipeline/make_mocks.py 100 42    # 仅初始化空 mock 目录；非空即拒绝，绝不覆盖链结果
.venv/bin/python pipeline/append_mocks.py --append 10 --dry-run  # 先校验清单、m000 和输入指纹；去掉 --dry-run 才追加
.venv/bin/python pipeline/run_gate2.py 1 100 --jobs=4   # 空校准 100 组（断点续跑 runs/gate2/results.jsonl）
.venv/bin/python pipeline/make_paper_figs.py      # 论文图 F1–F6
```

MCMC/nested 运行配置均以 `*.input.yaml` 存于 `runs/` 各目录（cobaya 直接可跑）；
论文正文 `paper/main.tex` 用 `tectonic main.tex` 编译。

链文件策略：入库的 `runs/**/*_N.1.txt` 为存档用薄链（论文数字的直接依据，
`pipeline/example_read_chain.py` 演示读取并复现表 I）；未入库的合并链/mock 数据
均可由入库配置与 seed 确定性再生。代码与文档以 MIT 许可发布（见 LICENSE）；
精确环境见 `requirements.lock`。

## 解释边界（大修版）

- 注册的约束视界 `a_h` 是后验到先验 KL 首次低于 0.1 nat 的位置；它在
  BIN4 审计中**未达到**。`a=1` 只是直接观测支持的边界，不能替代 `a_h`。
- CPL/JBP/BA/BIN4 的坐标先验、维数和早期物质主导约束不同；论文同时报告
  各语法诱导的先验终局构成，不再称为“相同先验”。
- GP 层级链没有达到冻结的 `R-1<0.01` 门槛，因此仅保留为均值回归未来如何
  预先固定终局的构造性反例，不进入四个拟合语法的定量比较。
- nested 文件中的二项标准误只描述固定随机重采样的数值诊断，不是
  nested-sampling 运行间不确定度。
