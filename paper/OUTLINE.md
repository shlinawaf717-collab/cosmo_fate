# 论文骨架 v1（2026-07-06）

目标期刊：PRD（主）/ JCAP（备）；PRL 短文版本视核心图反响另议。
语言：英文。风格：方法论论文，克制主张，每个概率带条件标签。

## 标题候选

1. *Is cosmic fate an inference or an assumption? A preregistered fragility audit of the heat-death conclusion with DESI DR2, Pantheon+, and Planck*
2. *The verdict on cosmic fate is prior-dominated: a preregistered analysis of dynamical dark energy*
3. *How fragile is the heat death?*（短标题，PRL 版）

## 摘要骨架（数字全部已锁定，F_param 待补一句）

- 问题：DESI 时代终局宣称激增；热寂结论是数据强制还是假设赠送？
- 方法：预注册（tag prereg-v1 + 2 次留痕修订）；D0 = DESI DR2 BAO + Planck-2018
  距离先验 + Pantheon+SH0ES；CPL 基线 + 终局分类器（§5 判据）；100 组 ΛCDM mock 空校准。
- 结果四连：
  (1) D0+CPL+P1：P(DECAY)=99.8%，P(RIP)=0.18%（nested 复核 0.165±0.038%）；P(DS)=0——语法伪影。
  (2) 空校准：方向判决在零假设下 ~U(0,1)（判对率 50/100，KS p=0.25；零噪声 mock 52/48）；
      真实数据深度 p<0.030（0/100），与 Wilks p=0.024 双路收敛。
  (3) 脆弱性矩阵：方向（thawing 象限）在全部 leave-one-out 下存活；幅度摆 3 倍
      （wₐ −0.55↔−1.72）；SN 样本换轨显著性摆 2.25↔3.27σ；ln B=−1.76 反挺 ΛCDM
      （统计量轴方向翻转）；quintessence 先验令 P(RIP)≡0（墙代价 +8.9χ²）。
  (4) [F_param 待补：跨语法终局表 + DS 概率在 JBP 下的复活与否]
- 结论句：P(热寂兼容)>99.3% 对一切已测假设变换稳健；终局概率表的内部结构由假设主导；
  终局方向判决在零假设下由噪声主导。评估框架与全部管线公开。

## 章节结构

### 1. Introduction
- DESI DR2 证据现状与显著性摇摆（2.25–4.2σ 谱系）；终局论文小潮流
- 认识论问题的提出（Krauss & Turner 1999 谱系 → 定量化）
- 贡献清单（5 条）；预注册声明 + AI 使用披露

### 2. Preregistered design
- 冻结计划、三道 Gate、修订机制；A-001/A-002 全文披露（附录 B）
- 与分析自由度批评（garden of forking paths）的关系

### 3. Data, likelihoods, and validation
- 三数据集档案（正文表 T1；约定一致性教训 → 附录）
- Gate 1：官方链级验证（图 F1：叠加等高线，≤0.33σ）
- F_CMB 定价：2.25σ vs 2.8σ，三样本稳定折扣

### 4. Fate taxonomy and classifier
- §5 判据（表 T2）；热力学映射；**DECAY≠逃脱热寂**（分类学修正点）
- 分类器单元测试与 OTHER 审计预算；边界标记机制

### 5. Baseline posterior and fate probabilities (D0+CPL+P1)
- 后验（图 F2：w₀-wₐ 等高线叠终局分区着色）
- 表 T3：终局概率 + 全部验证标签（nested、批均值误差、边界占比）
- ln B = −1.76 ± 0.31：Lindley 现象现场（F_statistic 轴引子）

### 6. Null calibration（核心节）
- 概率积分变换论证 → 预言 U(0,1)；100 mock 实测；**图 F3（招牌）：均匀直方图
  + 真实数据红线 + 零噪声 mock 标记**
- 校准后的真实数据陈述：方向无信息 / 深度 p<0.030
- 赛前预测 6/6 的披露（诚信证据）

### 7. The fragility matrix（论文主体）
- 7.1 F_data：D1–D4 表（T5）+ D5 阶梯 + SH0ES 泄漏
- 7.2 F_prior：P1/P2/P3 表；"由先验排除"；+8.9χ² 墙代价；P3≈P2 冗余发现
- 7.3 F_statistic：Δχ² vs ln B 方向翻转；先验体积依赖讨论
- 7.4 F_param：[待补——CPL/BA/JBP/BIN4(/GP) 终局表；图 F5 柱状对比]
- 7.5 约束视界 a_h：[待补——BIN4 KL(a) 曲线图 F6；终局判定位置 vs 视界]
- 7.6 汇总表 T4（八轴、旋钮、读数、稳健/脆弱判定）——全文核心表

### 8. Discussion
- 三层叙事定型：方向层无信息 / 深度层有信号 / 翻译层假设主导
- 刀锋不可判定性：终局 = 观测量的不连续泛函；若 Λ 精确成立则原则不可判定
- 智能体视角注记：DECAY vs DS 的 Dyson/Krauss–Starkman 区别（DECAY=计算无上限）
- 与 2025–26 终局论文的关系：他们报 P(终局)，我们报 ∂P/∂假设
- 局限：压缩 CMB（A-001 定价）、纯几何、CPL 族、单作者+AI（披露与验证链）

### 9. Conclusions（半页，四条）

### 附录
A. 冻结计划全文引用 | B. 修订记录全文 | C. 分类器数值细节与已知边界
D. mock 机制与零噪声验证 | E. 可复现性（仓库、MANIFEST、种子、命令）

## 图表清单

| # | 内容 | 状态 |
|---|---|---|
| F1 | Gate1 vs 官方链叠加 | ✅ 已有 |
| F2 | D0 w₀-wₐ 等高线 + 终局分区着色 | ✅ runs/phase2/d0_fate_partition.png |
| F3 | 空校准直方图（招牌图） | ✅ 已有 |
| F4 | leave-one-out 森林图（wₐ 与 P(RIP) 随组合移动） | ✅ runs/phase3/fdata/f4_loo_forest.png（pipeline/make_paper_figs.py） |
| F5 | F_param 跨语法终局柱状 | ✅ runs/phase3/fparam/f5_grammar_fates.png（同上） |
| F6 | a_h 的 KL(a) 曲线 | ✅ runs/phase3/fparam/f6_constraint_horizon.png（同上；旧 ah_kl_profile.png 有缺陷已被取代） |
| T1–T5 | 数据档案/判据/D0终局/八轴汇总/leave-one-out | 数据齐 |

## 引用清单骨架（refs.bib 同步建）

数据：Brout+22, Scolnic+22(Pantheon+), DESI DR2 (2503.14738), Chen+18(1808.05724), Schöneberg 24(BBN)
方法：CPL(Chevallier-Polarski 01; Linder 03), BA, JBP, Lewis+(CAMB), Torrado&Lewis(cobaya),
     Lewis(getdist), Speagle(dynesty), Wilks 38
论战：Efstathiou 24/25, DES-Dovekie(2511.07517), 2508.10514, 2502.04212, 2504.15222
终局谱系：Krauss&Turner 99, Dyson 79, Krauss&Starkman 00, Caldwell+03, Kallosh&Linde,
     Andrei-Ijjas-Steinhardt 22, 2025-26 终局论文组
