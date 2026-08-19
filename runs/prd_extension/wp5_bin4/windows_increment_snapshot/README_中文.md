# WP5 full-likelihood BIN4 Windows/WSL2 增量包

本包复用 `~/WP4_F1_WSL2_TASKPACK_20260813` 的完整 likelihood 数据和
Python环境，不包含重复的4 GB数据。

注意：WP5 不应与 WP4 nested 同时占满同一台 Windows。先完成
WP4 nested，再启动 WP5 正式12链。

## 固定任务

- 三个宽度：`0.005,0.01,0.02`；
- 每宽度4链，共12链；
- 最多8个单线程链并行；
- 每个宽度独立通过20维 R-1/ESS 和两次通过门；
- 采样期不显示参数均值、likelihood、fate或宽度比较。

## 操作

1. 解压本包到 Windows SSD。
2. 双击 `windows\20_install_and_preflight.cmd`。
3. 只有看到 `WP5 PRE-FLIGHT PASS` 后，才可双击
   `windows\21_start_wp5.cmd`。
4. 用 `windows\22_status.cmd` 查看盲态进度。
5. 三个 final audit 全部完成后，双击
   `windows\23_package_results.cmd`。

预检约30--90分钟；正式三宽度计算2--5周。
