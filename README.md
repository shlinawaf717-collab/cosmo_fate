# cosmo_fate — 动态暗能量下宇宙终局结论的脆弱性

预注册研究工作区。核心问题：在 SN + BAO + CMB 距离数据下，"宇宙热寂"结论对动态暗能量假设有多脆弱。

- `plan/ANALYSIS_PLAN.md` — 预注册分析计划（先验表、终局判据、数据组合、脆弱性度量、过关条件）。冻结后只能通过 `plan/AMENDMENTS.md` 修订。
- `pipeline/` — 似然、采样、终局分类器代码（Phase 1 起）
- `data/` — 数据文件与 `MANIFEST.md`（版本、来源、校验和）
- `runs/` — MCMC/nested sampling 输出，按 `<组合>_<模型>_<先验>` 命名
- `paper/` — 文稿

阶段路线：0 预注册（本阶段）→ 1 管线验证（Gate 1：复现 DESI DR2 已发表 w₀wₐCDM 结果）→ 2 全后验 + 终局分类 → 3 脆弱性量化（F_prior / F_param / F_data、mock 校准、约束视界）→ 4 写作。
