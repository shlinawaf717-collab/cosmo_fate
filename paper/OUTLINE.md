# 论文结构与交付状态（v1.1 大修候选，2026-07-21）

目标稿件：方法论型宇宙学论文。正文对所有概率保留数据、语法、先验和统计量条件，
不把有限红移信号直接写成模型无关的宇宙终局。

## 正文章节

1. **Introduction**：提出“终局是推断还是假设”的可审计问题。
2. **Preregistered design**：冻结计划、A-001--A-003 与事后 A-004 的身份边界。
3. **Data and validation**：DESI DR2、Pantheon+/SH0ES、Planck 距离先验及 Gate 1。
4. **Fate taxonomy**：冻结分类器、A-003 渐近分支与已知边缘案例。
5. **Baseline**：D0+CPL+P1 后验、nested 尾部复核及证据。
6. **Null calibration**：100 个 LCDM mocks、`U(0,1)` 方向层和真实数据深度层。
7. **Fragility matrix**：数据、先验、统计量、参数化与约束视界。
8. **Discussion/Conclusions**：方向、深度、翻译三层结论及局限。
9. **Appendices**：冻结计划、修订记录、分类器、mock、预测时序与复现。

## 图表状态

| 交付物 | 内容 | 状态 |
|---|---|---|
| F1 | Gate 1 与官方链对照 | 完成 |
| F2 | D0 后验与终局分区 | 完成 |
| F3 | Gate 2 null 直方图 | 完成 |
| F4 | leave-one-out 森林图 | 完成 |
| F5 | 四语法先验/后验终局组成 + GP 构造 | 完成 |
| F6 | BIN4 KL 与约束视界 | 完成 |
| T1--T5 | 数据、判据、基线、脆弱性矩阵、数据消融 | 完成 |

## 大修新增审计

- `prior_fate_audit.json`：四语法原生先验诱导的终局组成。
- `inwindow_fit_audit.json`：四个收敛语法的窗口内链最小值/AIC 审计。
- `model_average_audit.json`：LCDM/CPL 探索性模型平均。
- `matched_prior_audit.json`：A-004 支持维数审计；全局 No-Go，matched 值为空。
- `ah.json`：注册约束视界未达到；未来 KL 是语法运输而非直接观测。

## 明确排除于 v1.1 定量结论之外

- 非收敛、超先验未正规化的层级 GP 后验；仅保留均值回归构造。
- 500-mock 扩展、off-boundary 功效曲线、完整 CMB 谱似然、ACT/增长数据。
- 任何由协方差正则化制造的 matched-prior 权重或概率。
