# 审稿预案与投稿前清单

来源：2026-07-08 全文逐字精读（Claude 会话）。本文件不属于冻结范围（plan/ANALYSIS_PLAN.md
与正文另行管理）；散文补丁的执行须走 editorial changelog。

## 一、散文补丁清单
**【状态：#1–#12 已于 2026-07-08 全部执行并通过编译验证——批次记录见
EDITORIAL_CHANGELOG.md（E-01…E-14，含 numbers.tex 宏机制）】**

| # | 位置 | 改动 | 性质 |
|---|---|---|---|
| 1 | 导言三结果段 | "dissipation versus rip" → "decay versus rip" | 术语统一（分类器/图 5/表 III 均用 decay） |
| 2 | 导言结论段 + Sec. VI 末 | "2–3σ" → "2–3.3σ" 或 "∼3σ" | 3.27σ 超出 "2–3σ"。**执行注记：σ 三分类**——2.25σ（压缩基线精确值，不动）；"2–3σ"（跨编纂集区间，改）；Discussion 末 "2σ"（anti-rip 深度 p≈0.024，正确，不动）。逐处判断，勿全局替换 |
| 3 | 导言路线图 | "(Sec. IV)" → "(Secs. IV–V)" 或补半句 | Sec. V（基线结果）在路线图中隐身 |
| 4 | 摘要 | 99.8% → 99.82% | 与 0.18% 精度对齐；99.82+0.18=100.00 使 P(ds)≡0 可见（精读者曾被 99.8 误导脑补 0.02% 幽灵类别） |
| 5 | 图 1 图注 | 加 "here and throughout, contour pairs show 68% and 95% credible regions" | 全文无处定义等高线置信等级（已 grep 验证） |
| 6 | main.tex:321（正文，\emph）+ main.tex:338（图 4 注） | "the full combination is the most moderate of all subsets" → "more moderate than any probe-removal subset (D2–D4)" | **逻辑错误，优先级最高**：D1(−SH0ES) wa=−0.55 比 D0 的 −0.62 更温和；正文该句同句内自相矛盾（括号引 −0.55 为区间端点） |
| 7 | main.tex:482 | 3.04 → 3.03 | ah.json 权威值 3.0347；图 6 正确（3.03），正文手抄双重舍入致错 |
| 8 | App. A 首段 | "(2026-07-02, ...)" → "(drafted 2026-07-02, tagged 2026-07-03, ...)" | 论文引起草日期为冻结日期；可验证冻结事件（tag prereg-v1 → commit 98abc20）为 2026-07-03 10:26 +0800。审计关键数字必须与外部锚严格一致 |
| 9 | Sec. VII C | 补报 ΔAIC/ΔBIC 一句 | **预注册履约缺口**：计划注册 "ΔAIC, ΔBIC, and ln B" 三件套，正文只报了 ln B（grep 证实 AIC/BIC 仅出现于 App. A 计划复述行 688）。数值由已报量平凡导出（Δk=2：ΔAIC = −7.44+4 = −3.44 弱挺 CPL；ΔBIC = −7.44+2ln N ≈ +7.4 挺 ΛCDM，N≈1673 依计数约定，以管线权威值为准）。补报反而强化 VII C：三种信息准则内部复现方向翻转（AIC 随 Δχ²，BIC 随证据）。性质：履行冻结承诺，非偏离——预注册纪律不能反过来为不交付注册量背书 |

**结构性配套（与补丁同批实施）**：numbers.tex 宏机制——脚本从 runs/ 的 JSON 产物生成
`\newcommand` 宏，正文引用宏而非手抄数字，消灭"两个舍入者"缺陷类。批次执行时一次解冻、
一次 editorial changelog 留档。

## 二、候选审稿人问题预案（五条）

**Q1. 真值位置轴只有 ΛCDM null，无 off-boundary 功效对照**
（"你证明了判决不会虚警，凭什么说它能检出？"）
答案骨架：深度统计量的功效由 Wilks 渐近路线独立支撑（p=0.024 与校准 p<0.030 咬合）；
null 战役的目的按预注册是校准而非功效；off-boundary mock 战役承认为 future work，
框架已开源可直接跑。

**Q2. GP 的窗口内等价未自证**
（摘要 "five grammars indistinguishable inside the data window"，Table III 无各语法 χ² 列）
答案骨架：各语法窗口内拟合量在仓库 runs/ 逐组合记录；[11] 提供独立文献支撑；
如需可在 response 中给出五语法 χ²_min 对照表（数据现成，不动冻结文本）。

**Q3. anti-rip 深度的语法条件性**
（"calibrated p<0.030 是 CPL 管线下的深度；BIN4 下真实数据落在 null 分布 ~41 百分位"）
答案骨架：深度统计量按预注册在基线语法（CPL）下定义与校准；跨语法稳健的是信号的
存在与中红移定位（w3=−1.53±0.20；GP 两核独立复现），其命运相关性不稳健——
这正是层次 (iii)（translation）的内容，Discussion 已把深度重述为 thawing-quadrant
preference。摘要措辞带 "Baseline (CPL)" 前缀，无不实。

**Q4. 为什么压缩 CMB 而非全似然**
答案骨架：审计规模（8 轴 × 5 语法 × 100 mock × 嵌套复核 = 数百次完整拟合）下全似然
不可行；信息亏损被测量、稳定（≈0.5σ，三编纂集复现）、定价并全文继承（A-001；
Table IV "priced, stable" 行）；Union3 3.27+0.5≈3.8 与官方全似然值互证。

**Q5. 语法家族是不是挑出来让分歧最大化的（"设定好的"）**
五层答案（由浅入深）：
1. 程序性：五语法在 prereg-v1（2026-07-03，GitHub tag 可验）冻结于任何命运计算之前，
   不可能依结果挑选；
2. 结构性：选择判据本身被冻结——ANALYSIS_PLAN §1 对照表逐行注记未来行为类别
   （发散/有界/冻结/均值回归），按命运相关的结构维度抽样；
3. 社会性：五个全是社区现役工具（CPL=DESI 标准；BA/JBP 文献标准；binned/GP 标准
   非参数方法），无一为本文定制；
4. 逻辑性（最硬）：结论是存在性命题 + 跨度声明为 lower bound——挑选偏倚只能**低估**
   脆弱性（漏掉极端语法），不能伪造"合法语法间存在灾难性分歧"这一存在性事实；
5. 反身性：语法预定判决正是论文的测量对象，且论文对自己执行了标签制度
   （"donated by mean function" / "decided before any photon arrived" / "excluded by prior" /
   图 5 轴注 "A-003 criteria"）——"你的语法预设了结论"的答案是"对，我们测的就是
   预设了多少：2.3 dex"。
一句话版本（预审信用）："The conclusion is existential and the span a lower bound;
selection could only understate it."

## 三、投稿前硬性检查项

- [x] **Acknowledgments 的 `[TODO: friendly reviewers]` 已删除**；当前致谢仅列软件、
      DESI 与 AI 使用披露，不虚构或暗示未发生的友好预审。
- [x] Zenodo v1.0 快照 + DOI 已完成；v1.1 大修版在最终 PDF 质检后发布为新版本。
- [x] 六预测会话片段入库（2026-07-08 完成：plan/predictions_session_excerpt.jsonl
      连续 48 行无删节，SHA-256 记录于 PREDICTIONS_SESSION_EXCERPT.md，
      含"证明什么/不证明什么"的如实声明；GATE2_REPORT.md 时点更正同步）
- [x] ~~App. A 译文条款~~ 已存在（"takes precedence in any discrepancy"，2026-07-08 验收）
- [x] ~~App. A P2 定义域~~ 已写明（a ∈ [a_CMB, a_max]，2026-07-08 验收）
- [x] ~~App. B/C other 触发比例~~ 已留档（App. B：BA 10.5%、BIN4 82.4%；ε=0.01 复用冻结 ds 阈值；"consequence zero" 论证完整。2026-07-08 验收）
- [x] **App. D 时间戳验证：不通过（→ 补丁 #10，投稿前必须）**。法证时间线（07-08 会话存档核查）：
      战役开跑 ~07-03 14:35+0800（git 33a85a9）→ 15:42 中期报告 17/100（判对率 53%、
      中位数 48.5%、真实数据第 0 百分位已可见）→ **16:08 六预测才注册**（会话记录）→
      16:19 mock000 出结果。Sec. II "before it ran" + "blind in the strict sense" 与
      App. D "before the campaign ran" **不成立**；App. B 的 "predicted during the mock
      campaign" 才是准确版本。真正预结果注册的仅预测 5（mock000）。仓库中无任何
      战役前预测工件（"50±10" 首次入库为 07-06 d657204）。
      **补丁 #10**：预测措辞对齐 App. B（"registered mid-campaign (~17/100),
      derived from the PIT argument, before completion; the mock000 prediction alone
      preceded its run"）；"blind in the strict sense" 限缩至 mock000 或删除。
      **三处**：main.tex:147（Sec. II）、:279（Sec. VI）、:851（App. D）。
      科学结果零变动；此为措辞诚实性修复,优先级最高。
- [x] **补丁 #11（已执行，批次 E-2026-07-08）**（App. E, main.tex:918）："Finite-mock reporting rules **(frozen before
      the campaign)**" 不成立——"k+1" 首次入库 07-03 18:28（73/100 战役中），"0.0295"
      07-06 战役后。改为如实措辞："standard finite-simulation rules [33], applied
      uniformly"，可加注其保守性（plus-one/上界使头条 p 从 0.0099 弱化为 0.030——
      中途采纳了更保守的规则,方向与自利相反,这是最好的辩护）。
- [x] **全文时间声明审计（2026-07-08）**：11 处历史性声明逐条对 git/会话时间戳。
      为真：摘要与 Sec. II 的冻结顺序（10:26 冻结 < 11:29 首个命运结果）、L139 判据先于
      命运计算、L182 已知答案测试先于科学运行、L641 双向可发表在案、L720 A-001 先于
      命运分析（11:20 签署 < 11:29）。为假：L147/279/851（→#10）、L918（→#11）、
      L635 日期（→#8）。修辞性"before any photon/data arrive"（L106/258/426）为
      逻辑陈述,不涉历史时序,豁免。
- [x] ~~参考文献核对~~（2026-07-08 完成）：[11] = Wolf+2025（跨参数化稳健性,2502.04929）、
      [25] = Wolf & Ferreira 2023（underdetermination,2310.07482）——两篇 Wolf 均在承重
      位置,与预审人选一致；[7,8] = Andrei-Ijjas-Steinhardt PNAS 2022 + Gialamas
      2025 PRD ✓；[12,13] = Muir 2020 + Andrade 2025 ✓；[17] Caldwell、[32] Rosenblatt、
      [33] Phipson-Smyth 等 32 个可核条目 arXiv 号全部无误。
      **补丁 #12（扩展为文献完备性批次）**：
      (a) Union3 三处使用（main.tex:326/513/951）零引用——补 Rubin et al., arXiv:2311.12098,
          VII A 首次出现处挂引;
      (b) Planck 2018 本体未引——摘要即用 "Planck 2018 distance priors",补 Planck
          Collaboration VI, arXiv:1807.06209,Sec. III 首次出现处挂引;
      (c) SH0ES 锚点未引——补 Riess et al., arXiv:2112.04510,Sec. III 挂引;
      (d) 渲染修复：JCAP 条目年份被吞（编译版 [10][11][13][22][29] 无年份）;[16] 缺
          卷页年（应为 JCAP 02 (2019) 028）;[12] Muir 缺卷页（MNRAS 494, 4454）。
          修 refs.bib 字段,重编译核对。
- [x] v1.1 编译产物逐页校对完成（2026-07-21）：30 页，检查上标（10⁴、Δχ²）、
      F1--F6、T1--T5、Appendix A--F 连续性、A-004 分页及参考文献；无裁切、重叠、
      缺字或未解析引用。

## 四、A-004 matched-prior 问题预案

**问题：既然原生坐标先验不同，为什么不把四个语法重加权到共同函数先验？**

答案：已做事后结构审计，并在计算权重之前停止。七点 `w(a)` 摘要的环境维数为 7，
CPL/JBP/BA 的推前支持维数为 2，BIN4 为 4；共同交集只有零原生先验质量的一维常数
历史。所需 Radon--Nikodym 比不存在。对奇异协方差加对角正则只会创造人工重叠，
因此 A-004 是全局 No-Go，所有 matched 概率、ESS 和 overlap 均不报告。未来研究必须
预先指定共同生成式函数先验及合法拉回，或预注册更低维估计量。
