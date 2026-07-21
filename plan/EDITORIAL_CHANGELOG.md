# 编辑变更日志（Editorial Changelog）

与预注册修订记录（AMENDMENTS.md）的关系：AMENDMENTS 管**分析选择**的变更，本日志管
**散文/排版/文献/报告措辞**的变更。本批次零分析变动：不重跑任何链、不改任何判据、
不动任何后验数字的数值——唯一新增的数字（E-09 的 ΔAIC/ΔBIC）由已发表量解析导出。

## E-2026-07-08（正文解冻批次 1：全文精读补丁 #1–#12）

来源：2026-07-08 逐字精读审计（法证记录见 REVIEW_PREP.md）。
正文冻结（2026-07-07 639189c "main text frozen"）由本批次解除并即时重冻。

### 诚实性措辞（最高优先级）

- **E-01（原 #10）** 六条 mock 预测的时间声明，三处（Sec. II、Sec. VI、App. D）：
  "registered before the campaign ran" / "blind in the strict sense" →
  "logged mid-campaign (after ~17 of 100 mocks), derived from the PIT argument,
  before completion; the zero-noise prediction alone preceded its run"。
  依据：会话存档法证时间线（战役开跑 07-03 14:35 → 中期报告 17/100 15:42 →
  预测注册 16:08 → mock000 结果 16:19）。App. B 的 "predicted during" 原本就是
  准确版本，本次对齐。科学结果零影响（null 校准结论不依赖预测盲性）。
- **E-02（原 #11）** App. E 报告规则："(frozen before the campaign)" → 删除时间
  声明，改注 "adopted during the campaign and applied uniformly; they weaken,
  not strengthen, the headline bound"。依据："k+1" 首次入库 07-03 18:28（73/100），
  "0.0295" 07-06 战役后。保守性注记如实：plus-one/上界使头条 p 从 0.0099 弱化为 0.030。

### 事实/逻辑修正

- **E-03（原 #6）** "the full combination is the most moderate of all subsets"
  （正文 + 图 4 注，两处）→ "more moderate than any probe-removal subset (D2–D4)"。
  依据：表 II 自证伪（D1 wa=−0.55 比 D0 −0.62 更温和）。
- **E-04（原 #7）** Sec. VII E 首 bin KL：3.04 → 3.03。权威源 ah.json = 3.0347
  （图 6 原本正确）；已由宏机制（见下）结构性防复发。
- **E-05（原 #8）** App. A 冻结日期："(2026-07-02, ...)" →
  "(drafted 2026-07-02, tagged 2026-07-03, ...)"。依据：tag prereg-v1 →
  commit 98abc20 = 2026-07-03 10:26:34 +0800。
- **E-06（原 #12a–c）** 缺失引用三条：Union3（Rubin et al., 2311.12098，VII A 挂引）、
  Planck 2018 VI（1807.06209，Sec. III 挂引）、SH0ES（Riess et al., 2112.04510，
  Sec. III 挂引）。

### 预注册履约

- **E-07（原 #9）** Sec. VII C 补报注册而未报的 ΔAIC/ΔBIC：
  ΔAIC = Δχ²+2Δk = −3.4（挺 CPL）、ΔBIC = Δχ²+Δk·lnN = +7.4（挺 ΛCDM；
  Δk=2, N=1673）。由已发表 Δχ²=7.44 解析导出，无新计算。

### 清晰度/一致性

- **E-08（原 #1）** 导言 "dissipation versus rip" → "decay versus rip"（与分类器
  术语统一）。
- **E-09（原 #2）** "2–3σ" → "2–3.3σ"，两处（导言结论段、Sec. VI 末）——3.27σ
  超出原区间。σ 三分类核查：2.25σ（精确值）与 Discussion 末 "2σ"（深度）不动。
- **E-10（原 #3）** 导言路线图补 Sec. V：" (Sec. IV)" → "and report the baseline
  verdict (Secs. IV–V)"。
- **E-11（原 #4）** 摘要 99.8% → 99.82%（与 0.18% 精度对齐；99.82+0.18=100.00
  使 P(ds)≡0 可见）。
- **E-12（原 #5）** 图 1 注补 "Here and throughout, contour pairs show the 68%
  and 95% credible regions."
- **E-13（原 #12d）** refs.bib 字段修复：JCAP 六条改 ADS 卷式（volume=年份,
  number=期号）以修复 apsrev4-2 吞年份；[16] 补卷页（JCAP 02 (2019) 028）；
  Muir 补卷页（MNRAS 494, 4454）。

### 结构性配套

- **E-20**（2026-07-21，归档 DOI 热修）GitHub--Zenodo 同步产生 v1.1 后，发现
  正文仍引用仅指向 v1.0 的版本 DOI `10.5281/zenodo.21332434`。现改为概念 DOI
  `10.5281/zenodo.21332433`，由 Zenodo 稳定解析到该归档序列的最新版本。
  同步将发布元数据版本改为 v1.1.1；不改分析、代码、数字或科学结论。
- **E-19**（2026-07-13，可复现性）App F 的 "(an archival snapshot with a DOI
  will accompany submission)" 替换为实际 DOI：`10.5281/zenodo.21332434`
  （GitHub release `v1.0-submission` 通过 Zenodo-GitHub 集成自动归档，
  50.1MB 快照，MIT 许可证，Software 类型；`.zenodo.json` 元数据于本次提交前
  已配置）。兑现 App F 的书面承诺。零分析变动。
- **E-18**（2026-07-13，文献补全+论证补强）Discussion 的 "conveniences, not
  theories" 二分句改为三分：承认 CPL 是对 quintessence 类动力学的**校准压缩**
  （补引 Caldwell & Linder 2005 PRL 95, 141301；Linder 2006 PRD 73, 063010；
  de Putter & Linder 2008 JCAP 0810:042，三条均对 arXiv 核实），随即划界——
  校准认证的是窗口内对模型类的忠实，把忠实延伸到 a>1 恰是采纳该类为先验，
  即 Sec. fprior 已定价的 P2 轴。动机：原二分句未接校准文献，是"作者不了解
  CPL 校准论证"型审稿攻击的敞口；新句承认对方最强论据后核心主张原样成立。
  零分析变动。refs.bib 新增三条（JCAP 条目按 E-13 的 ADS 卷式）。
- **E-17**（2026-07-09，文献补全）Discussion 的 "eventually decidable or
  permanently undecidable" 句补引 Wolf & Read 2026（arXiv:2501.13521,
  "permanent underdetermination"）——本文的永久不可判定分支是该概念在
  零宽度边界上的定量实例,智力谱系应显式归属。refs.bib 新增一条。
- **E-16**（2026-07-09，图形排版）图 6 的 "0.1 nat horizon threshold" 标签
  原位于虚线与 w4 KL 条之间（被两者遮压，可读性差），移至虚线下方空白区
  （make_paper_figs.py: y=0.16 → y=0.08, va="top"）。纯排版，数据与标注值无涉。
- **E-15**（2026-07-09，预审稿准备）删除 Acknowledgments 末尾的
  `\todo{friendly reviewers}` 占位。预审人致谢按惯例在对方给出意见并同意
  被致谢之后添加；预审稿以定稿形态发出。`\todo` 宏定义保留（无引用即无渲染）。
- **E-14** 新增 pipeline/gen_paper_numbers.py → paper/numbers.tex 宏机制：
  正文引用的 12 个高频数字（KL 四值、null 五统计量、D0 三概率）改由脚本从
  runs/ JSON 生成，消灭"一个数字两个舍入者"缺陷类（E-04 的病根）。
  机制可增量扩展至其余数字。
