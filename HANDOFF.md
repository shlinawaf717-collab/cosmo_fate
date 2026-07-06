# 交接文档（2026-07-03，机器迁移用）

本仓库自包含：新机器上凭本文档 + 仓库即可无损复活全部研究。机器本地的 AI 记忆不随迁移,
本文档即"外置大脑"。

## 一、项目状态一览

预注册计划 `plan/ANALYSIS_PLAN.md`（tag `prereg-v1`，正文冻结），修订见 `plan/AMENDMENTS.md`（A-001 已生效）。

| 里程碑 | 状态 | 关键数字 |
|---|---|---|
| Gate 1 管线验证 | ✅ 通过（含 A-001） | 四参数与 DESI DR2 官方偏差 ≤0.5σ；Δχ²=7.44→2.25σ（压缩 CMB） |
| D0 全后验终局概率 | ✅ | DECAY 99.82%±0.06%，RIP 0.18%，DS=0（语法伪影），boundary≈0 |
| nested 复核（§6） | ✅ | P(RIP)=0.165%±0.038% 与 MCMC 一致；**lnB(CPL/ΛCDM)=−1.76±0.31 反挺 ΛCDM** |
| D5 显著性阶梯 | ✅ | Pantheon+ 2.25σ / Dovekie 2.81σ / Union3 3.27σ——文献摇摆复现 |
| Gate 2 空校准 | 🔄 73/100 | 判对率 50.0%，P_heat 均匀（KS p=0.83），mock P_RIP 地板 2.68% vs 真实 0.18%（校准 p<0.017）；mock000（零噪声）P_heat=52.3% |
| Gate 1 官方链对比 | ⏸ 待 DESI 账号 | data.desi.lbl.gov 注册后照 DR1 路径模式下载 DR2 chains |

已测脆弱性轴：F_data(SN) 摆 1σ；F_data(SH0ES) H₀+1.35/w₀−0.034；F_CMB 摆 0.5σ；F_statistic 方向翻转。
待跑：F_prior(P2/P3)、D1–D4、F_param(BA/JBP/BIN4/GP)、约束视界 a_h。

## 二、新机器复活步骤

```bash
git clone <本仓库>  && cd cosmo_fate
python3 -m venv .venv && .venv/bin/pip install numpy 'scipy==1.16.2' camb cobaya dynesty getdist Py-BOBYQA
# scipy 必须钉 1.16.2（1.18 与 camb 1.6.6 BBN 接口不兼容,见 MANIFEST）
.venv/bin/cobaya-install sn.pantheonplus sn.pantheonplusshoes sn.union3 sn.desdovekie \
    bao.desi_dr2 --packages-path data/cobaya_packages
# 数据校验: 对照 data/MANIFEST.md 的 SHA256 逐条 shasum -a 256
.venv/bin/python pipeline/test_fate.py          # 分类器 8/8
# 管线自检: 零噪声 mock 在真值点 chi2=0
```

## 三、续跑 Gate 2（剩余 27 组 mock）

mock 由 seed 42 确定性再生,`runs/gate2/results.jsonl`（已提交,含 73 组）驱动断点续跑:

```bash
.venv/bin/python pipeline/make_mocks.py 100 42   # 再生全部 mock 目录(数据逐位相同)
.venv/bin/python pipeline/run_gate2.py 1 100 --jobs=4   # 自动跳过 jsonl 已有的 73 组
```

跑完后:汇总判对率/均匀性 KS/校准 p 值,出 GATE2_REPORT.md,起草 A-002
（Gate 2 判据对骑线真值原则不可满足——参照 A-001 格式,PI 签字）。
核心图:mock P_heat 直方图(均匀)+真实数据 0.998 红线 + mock000 标记。

## 四、后续路线（优先级序）

1. **F_prior**：P2（逐点 w(a)≥−1,拒绝采样或先验内实现）、P3（wₐ≤0 且 w₀≥−1）× D0,预期 P(RIP) 恒 0——"由先验排除"是合法结论
2. **D1–D4**：改 d0_cpl_p1.yaml 的 likelihood 块(D1 去 SH0ES 用 pantheonplus;D2 去 CMB 加 BBN 先验 ombh2~N(0.02218,0.00055);D3 去 BAO;D4 去 SN)
3. **F_param**（最大部件,适合一个完整深度周）：BA/JBP 改 camb 的 dark_energy 或自写背景;BIN4/GP 需自定义 w(a) 表接口(camb set_w_a_table);每种配 fate.py 的 ln_fde/w_of_a
4. **约束视界 a_h**：BIN4 后验-先验 KL(a)
5. 论文:核心图已有三张(阶梯表/直方图/52-48);目标 PRD/JCAP,PRL 可试投
6. 升级项(下期):PR4+ACT 压缩先验,分解 F_CMB 的 0.5σ

## 五、等人类完成的事

- DESI 数据门户注册(data.desi.lbl.gov)→ 任务:官方链逐等高线对比
- camb GitHub 上报 scipy 1.18 BBN 兼容 bug(半小时,入网动作)
- ICTP 曼谷学校(2026-12)申请窗口核查;9-10 月盯 Tonale/ICIC
- LJMU 远程 MSc 资格确认邮件(若走该路线)

## 六、重要教训存档(勿重蹈)

1. 压缩先验的抽取端/预测端公式约定必须一致(ℓ_A 3σ 伪影事件)
2. 与文献比显著性必须对齐 CMB 信息含量(A-001)
3. 尾概率(<1%)必须 nested 复核后才进正文(§6)
4. 跨模型比较用 likelihood-only chi2 列,勿用含先验体积的 minuslogpost
