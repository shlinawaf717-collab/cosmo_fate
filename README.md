# cosmo_fate — 动态暗能量下宇宙终局结论的脆弱性

本地版本控制的二次数据分析预注册研究工作区。核心问题：在 SN + BAO + CMB 距离数据下，"宇宙热寂"结论对动态暗能量假设有多脆弱。数据与验证策略已知，但终局翻译审计计划在首次目标终局计算前冻结；公共仓库随后建立，故不称为经第三方平台注册的预注册。时间线、逐语法 P1 实现溯源、提交祖先关系与校验和见 `plan/PREREGISTRATION_PROVENANCE.md`。

- `plan/ANALYSIS_PLAN.md` — 预注册分析计划（先验表、终局判据、数据组合、脆弱性度量、过关条件）。冻结后只能通过 `plan/AMENDMENTS.md` 修订。
- `plan/PREREGISTRATION_PROVENANCE.md` — 预注册冻结、首次结果、Git 祖先关系和公共仓库建立时间的溯源审计
- `pipeline/` — 似然、采样、终局分类器代码（Phase 1 起）
- `data/` — 数据文件与 `MANIFEST.md`（版本、来源、校验和）
- `runs/` — MCMC/nested sampling 输出，按 `<组合>_<模型>_<先验>` 命名
- `paper/` — 文稿

## 研究版本边界

完成的 v1.x 论文由 commit `70a47ec` 与 annotated tag
`paper-v1x-final-20260722` 固定；其论文、结果和原始本地预注册身份不由后续研究
追溯性改写。PRD 强化研究使用独立协议
`plan/PRD_EXTENSION_PROTOCOL.md`、机器清单
`plan/prd_extension_protocol.json` 和追加式修订账本
`plan/PRD_EXTENSION_AMENDMENTS.md`。所有新结果必须写入
`runs/prd_extension/`，不得覆盖 v1.x 的 `runs/gate2/`、`runs/phase2/` 或
`runs/phase3/`。

当前强化版封口检查点（2026-08-25）：WP2 已完成 500 个 noisy mock，正式端点为
`K=2/500`、plus-one `p=0.005988`；WP3 已完成 600 个 noisy case 与 6 个
Asimov case，外点方向功效门通过，但正面结论仅限两个注册外点备择。WP7 的
50-dataset SBC、五个真实数据设置和后处理审计均已 PASS；WP8 的观测不变未来延拓
及部分识别审计已 PASS。WP4 F1 MCMC 已导入并通过候选收敛/ESS门，但稀疏 RIP
尾部因未执行注册的 nested 验证而不进入论文；WP4 nested 记为计算可行性 No-Go。
WP5 在端点盲态、未收敛时按 PRD-A018 停止，所有部分链保留但排除于科学结果。
封口决定见 `plan/WP4_WP5_CLOSURE_DECISION.md`。

阶段路线：0 预注册（本阶段）→ 1 管线验证（Gate 1：复现 DESI DR2 已发表 w₀wₐCDM 结果）→ 2 全后验 + 终局分类 → 3 脆弱性量化（F_prior / F_param / F_data、mock 校准、约束视界）→ 4 写作。

## 复现（Reproduce）

```bash
# 环境（scipy 必须钉 1.16.2，原因见 data/MANIFEST.md）
python3 -m venv .venv && .venv/bin/pip install -r requirements.lock
.venv/bin/cobaya-install sn.pantheonplus sn.pantheonplusshoes sn.union3 sn.desdovekie \
    bao.desi_dr2 --packages-path data/cobaya_packages
# 数据校验：对照 data/MANIFEST.md 的 SHA256 逐条 shasum -a 256

.venv/bin/python pipeline/test_fate.py            # 分类器单元测试（含 A-005 严格边界）
.venv/bin/python pipeline/constraint_horizon_audit.py  # 重算注册 KL；a_h 未达到
.venv/bin/python pipeline/prior_fate_audit.py     # 各语法诱导的先验终局构成
.venv/bin/python pipeline/inwindow_fit_audit.py   # 四个已收敛语法的窗口内拟合审计
.venv/bin/python pipeline/model_average_audit.py  # 探索性 LCDM/CPL 模型平均
.venv/bin/python pipeline/matched_prior_audit.py  # A-004 结构审计；全局 No-Go，不生成 matched 概率
.venv/bin/python pipeline/early_de_audit.py       # A-006 BIN4 早期暗能量硬门审计
.venv/bin/python pipeline/full_planck_feasibility_audit.py  # full-Planck 接口 No-Go/重启条件
.venv/bin/python pipeline/fragility_audit.py      # 正式履行 F_prior/F_param/F_data
.venv/bin/python pipeline/gen_paper_numbers.py    # JSON 单一来源生成正文宏
.venv/bin/python pipeline/make_mocks.py 100 42    # 仅初始化空 mock 目录；非空即拒绝，绝不覆盖链结果
.venv/bin/python pipeline/append_mocks.py --append 10 --dry-run  # 先校验清单、m000 和输入指纹；去掉 --dry-run 才追加
.venv/bin/python pipeline/migrate_null500.py --dry-run  # WP2 原子迁移预检
.venv/bin/python pipeline/migrate_null500.py --audit    # 迁移或远程传输后的逐文件复核
.venv/bin/python pipeline/run_gate2.py 101 500 --jobs=4 --dry-run  # WP2 预检；仅允许 runs/prd_extension/null500/
.venv/bin/python pipeline/report_null500_endpoints.py  # 从 501 行账本生成 WP2 六项正式端点
.venv/bin/python pipeline/report_wp3_power.py          # 生成 WP3 表、图和限定解释
.venv/bin/python pipeline/wp7_wp8_preflight.py         # WP7/WP8 解析与数值预检
.venv/bin/python pipeline/make_paper_figs.py      # 论文图 F1–F6
```

MCMC/nested 运行配置均以 `*.input.yaml` 存于 `runs/` 各目录（cobaya 直接可跑）；
论文正文 `paper/main.tex` 用 `tectonic main.tex` 编译。

链文件策略：入库的 `runs/**/*_N.1.txt` 为存档用薄链（论文数字的直接依据，
`pipeline/example_read_chain.py` 演示读取并复现表 I）；未入库的合并链/mock 数据
均可由入库配置与 seed 确定性再生。代码与文档以 MIT 许可发布（见 LICENSE）；
精确环境见 `requirements.lock`。

`pipeline/migrate_null500.py` 将 v1.x 的 `m000`--`m100`、结果账本和 fitted-truth
快照原子迁入 `runs/prd_extension/null500/`，普通文件逐字节保持不变；每个 mock
的 SN/BAO 协方差改为仓库相对链接。`migration_manifest.json` 与
`migration_inventory.json` 用于本地和远程传输后的重复审计。新增 mock 的生成器
同样只创建相对协方差链接。

## 解释边界（大修版）

- WP2 的 500-mock 结果为 `2/500`，95% Clopper--Pearson 区间
  `[0.000485,0.014374]`；它提高了有限模拟尾部精度，但使 v1.x
  “低于每一个 mock / 八倍更深”的修辞失效。
- WP3 只证明分类器在两个注册外点备择下方向功效充足。六个真值的 D0 profile
  `Delta chi2` 跨 `0--39.37`，不能解释成对称、等支持的效应量曲线；单调性门只是
  粗筛查。
- 注册的约束视界 `a_h` 是后验到先验 KL 首次低于 0.1 nat 的位置；它在
  BIN4 审计中**未达到**。`a=1` 只是直接观测支持的边界，不能替代 `a_h`。
- CPL/JBP/BA/BIN4 的坐标先验、维数和早期物质主导约束不同；论文同时报告
  各语法诱导的先验终局构成，不再称为“相同先验”。
- A-005 将有限极限的物理边界严格置于 `w_inf=-1`；`epsilon=0.01` 只标记
  边界邻近样本。重算后 BA/BIN4 的 `P(RIP)` 分别为 1.34%/49.96%，严格
  `P(DS)=0`。
- A-004 七点摘要中的 BIN4 映射为 `[w3,w2,w1,w1,w1,w1,w1]`，支持秩为 3；
  共同交集仍为一维，matched-prior 全局 No-Go 不变。
- A-006 要求 BIN4 满足 `rho_DE/rho_m(z=1059)<0.01`；归档后验全部通过。
  当前背景代码没有 CMB 谱/扰动接口，故 BIN4 只称“压缩 CMB 条件下”，不称
  full-Planck 结果。
- A-007 记录 P1 早期物质主导意图的逐语法实现及其归档时间边界；它不追溯性地
  把逐语法公式称为冻结文本中已显式预注册的细节，且不改变任何分析或数字。
- GP 层级链没有达到冻结的 `R-1<0.01` 门槛，因此仅保留为均值回归未来如何
  预先固定终局的构造性反例，不进入四个拟合语法的定量比较。
- nested headline 直接使用原始归一化 `logwt`；等权重重采样只作诊断。
  D0 使用独立种子报告运行间离散度，且不与单次 dynesty 内部 `logZerr` 混合。
  当前 D0 三种子均值为 `P(RIP)=0.179%`（种子间 SD `0.039` 个百分点），
  `ln B(CPL/LCDM)=-1.617`（种子间 SD `0.224`）。D0--D4 的原始权重尾部
  跨 `0.0008%--0.376%`，方向均为亚百分比，但数值跨度为 `2.665 dex`。
