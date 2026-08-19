# WP4 F1 nested evidence Windows/WSL2 增量包

本包复用 Windows WSL2 中已有的
`~/WP4_F1_WSL2_TASKPACK_20260813`，不重复携带 4 GB likelihood 数据。
它安装 OpenMPI/PolyChordLite，生成并哈希冻结 12 个正式运行，以
4 MPI ranks × 2 并行作业使用 9700X 的 8 个核心。

## 科学边界

- 3 个固定种子：2026082001--2026082003。
- 每个种子必须完成 full CPL、RIP 分层、DECAY 分层和 LCDM。
- `nlive=500`、`num_repeats=5d`、`precision_criterion=0.01`，不得中途改变。
- 中途状态不显示 logZ、参数均值或 fate 概率。
- 不得因某个种子的结果而停止或删除其他种子。
- 运行可断电续跑；只能使用原命令恢复。

## 操作顺序

1. 把整个增量包解压到 Windows 本地 SSD。
2. 双击 `windows\10_install_and_preflight.cmd`。第一次需联网，且会运行一个
   20-dead-point 计时 pilot，约 30--120 分钟。pilot 的样本与证据绝不进入
   科学结果，只用于验证 MPI/PolyChord 真正可运行并估算工期。
3. 只有明确看到 `NESTED PRE-FLIGHT PASS` 后，双击
   `windows\11_start_nested.cmd`。
4. 双击 `windows\12_status.cmd` 只查看进程、resume 文件和完成数。
5. 12/12 完成且自动生成 `nested_endpoints.json` 后，双击
   `windows\13_package_results.cmd`。

## 预计时间

这是18/16维 full-CMB nested sampling，在 pilot 之前按 2--6 周窗口规划。
真实时间由 PolyChord 的亡点数和慢块调用决定；预检会记录
`pilot_runtime_seconds`，据此再收窄预估，但不设置事后最大时间截止。

如果预检失败，不要绕过 JSON 状态。保留
`nested_increment_20260819/logs/` 和 `work/f1_nested/` 进行诊断。
