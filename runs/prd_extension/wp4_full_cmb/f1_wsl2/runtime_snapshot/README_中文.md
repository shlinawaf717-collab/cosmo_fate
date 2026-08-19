# WP4 F1 Windows / WSL2 任务包

本包用于在家里的 x86-64 Windows 电脑上，通过 WSL2 Ubuntu 从零运行
PRD extension 的 WP4 F1。它包含 F1 所需的全部已注册 likelihood 数据、
代码、proposal、输入清单、Mac 固定点参考、环境锁、预检、smoke、四链
driver、盲态 convergence controller、可逆 finalizer 和结果回传工具。

## 最重要的科学边界

- 只允许在 WSL2 Ubuntu 中运行，不运行原生 Windows 版 Python。
- Windows 四链必须从零开始；Mac 当前链和 checkpoint 不得复制进来。
- 若 Windows 预检通过并开始采样，Windows 四链就是唯一正式 F1 链集；
  不得根据未来速度或结果在 Mac/Windows 中择优。
- 预检失败时不会生成正式样本；请保留错误报告，由 Mac F1 继续。
- 运行期间不查看参数均值、区间、likelihood、最佳点或 fate。
- RTX 5070 Ti 不参与计算；本任务主要使用 CPU。

## Windows 上的操作顺序

1. 将整个解压后的 `WP4_F1_WSL2_TASKPACK_20260813` 文件夹放在 Windows
   本地 SSD（不要直接从机械硬盘、网络盘或移动盘长期运行）。
2. 如果尚未安装 WSL2，以管理员 PowerShell 运行：

   `powershell -ExecutionPolicy Bypass -File wsl\00_install_wsl.ps1`

   按提示重启；第一次打开 Ubuntu，创建 Linux 用户和密码。
3. 双击 `windows\01_launch_preflight.cmd`。首次执行会把任务包复制到
   WSL2 的 Linux 文件系统 `~/WP4_F1_WSL2_TASKPACK_20260813`，安装严格
   版本环境并运行全部门。预计 20--60 分钟，取决于网络和 CPU。
4. 只有窗口最后明确显示 `PRE-FLIGHT PASS`，才双击
   `windows\02_start_f1.cmd`。
5. 用 `windows\03_status.cmd` 查看进程、四链行数和盲态 R-1/ESS。
6. controller 达成连续两次通过后会自动执行 finalizer。看到
   `EXTERNALLY_STOPPED` 后，双击 `windows\04_package_results.cmd`；结果包
   会复制回本任务包的 Windows 文件夹。

## 预检必须全部通过

- Linux x86-64 / WSL2 身份；
- 本包逐文件 SHA256；
- 1,305 个注册 likelihood 文件、3,577,141,302 字节及逐文件 SHA256；
- 上述 1,305 项中包含旧冻结清单已登记的 2 个 AppleDouble `._*`
  兼容记录（共 711 字节）；它们不被 likelihood 读取，但为保持冻结清单
  的路径、字节数和 SHA256 不变而原样保留；
- Python 3.13.13 和严格科学包版本；
- CAMB 几何量与全谱跨平台漂移门；
- full-F1 固定点总及分项 chi-square 绝对差均不超过 0.10；
- F1 no-sampling smoke，包括 DESI、Pantheon+SH0ES、P1、`Mb`、两套
  low-l clik、NPIPE 和 ACT lensing；
- Windows 本地运行 YAML、政策、controller/finalizer 和输入哈希闭环。

## 正式停止门

- 18维四链联合 R-1，50% burn-in 后严格小于 0.01；
- 20%和70% burn-in 的 R-1 均严格小于 0.02；
- `w`、`wa` 的 bulk ESS 均大于1000，tail ESS 均大于400；
- 全部门连续通过两次，中间每链新增至少320行且哈希变化；
- finalizer 暂停子进程，验证文件稳定并复算全部门后才停止。

## 断电、重启与恢复

本包会保留 Cobaya checkpoint。Windows 重启后再次双击
`windows\02_start_f1.cmd`，driver 会检测 checkpoint 并使用 `--resume`；
启动脚本会拒绝重复 driver/controller。不要手工复制、拼接或删除 chain。

## 预计时间与空间

- 解压后数据约4--5 GB；正式链还应预留至少20 GB。
- 9700X 等8个高性能CPU核预计约3--6天，但实际由冻结收敛门决定。
- Windows电源设置应设为不自动睡眠；显示器可以关闭。

## 发生错误时

不要绕过门或编辑 JSON 里的 PASS/FAIL。保留：

- `logs/setup_preflight.log`
- `work/preflight/`
- `work/f1/*/run.log`
- `work/f1/driver_events.jsonl`
- `work/f1/external_monitor/`

把这些文件打包传回 Mac 后诊断。不要把账号、密码或密钥放进包中。

## 身份

- 源 Git commit：`e50d842`（包含 WSL2 迁移政策；任务代码快照来自同一
  分支的 F1 冻结系统）
- F1 静态冻结 commit：`aaaa6d1`
- F1 smoke commit：`5ea2616`
- 迁移政策：`payload/plan/WP4_F1_WINDOWS_MIGRATION_POLICY.md`
