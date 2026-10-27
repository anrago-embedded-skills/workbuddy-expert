# 嵌入式 Linux 证据采集

[collect-evidence.sh](../scripts/collect-evidence.sh) 提供不改变设备运行状态、有限大小的环境、内核日志和进程快照，并写入指定的新报告目录。输出路径按 Unix 字面量处理，合法文件名中的反斜杠会保留；控制字符路径不支持。它保存现场数据供后续分析，不会自动诊断 OOM、内存泄漏或故障根因。

## 在目标 Linux 上采集

把脚本放到目标机可执行的位置，在目标 Linux 上运行。输出目录必须尚不存在，其父目录必须已存在且可写：

```sh
# TARGET：仅读取常规 Linux 文件和 dmesg；输出创建在目标机的 /tmp 下
sh ./collect-evidence.sh --mode env --output /tmp/incident-env

# TARGET：对正在运行的正整数 PID 读取进程状态、限额、等待点、cgroup 和挂载信息
sh ./collect-evidence.sh --mode process --pid 4242 --output /tmp/incident-process-4242

# TARGET：采集有界内核日志
sh ./collect-evidence.sh --mode kernel --output /tmp/incident-kernel
```

这些命令不需要 `sudo`，也不改变 sysctl、硬件、设备树、服务、模块或网络。权限不足会记录在 manifest 中；只有读取 dmesg 的目标权限允许时，kernel 模式才能得到该项数据。live 模式先确认运行平台为 Linux，其他平台以非零状态退出。

## 在主机上检查离线快照

先由用户或既有流程把目标文件复制到一个目录，再在主机上明确传入真正的目标快照根目录。根目录会规范化；如果最终指向主机根目录 `/`（包括经符号链接指向 `/`），采集器会拒绝运行。采集器不能证明输入目录确实来自目标机，也不保证快照在采集期间保持不变：

```sh
# HOST：data/fixture-root 内必须是目标快照，不会回退读取主机 /proc、/sys、uname 或 dmesg
sh ./collect-evidence.sh --mode env --source-root /path/to/target-snapshot --output /tmp/incident-env
sh ./collect-evidence.sh --mode kernel --source-root /path/to/target-snapshot --output /tmp/incident-kernel
sh ./collect-evidence.sh --mode process --pid 4242 --source-root /path/to/target-snapshot --output /tmp/incident-process-4242
```

离线模式仅从指定树的固定相对路径读取文件。它会拒绝样本路径中的符号链接，避免通过链接读出快照目录以外的数据。调用者负责提供真实的目标快照；采集器无法证明来源，也不保证该目录在采集期间不变。`collector_time_utc` 是运行采集器时使用的主机时钟；它不是快照采集时间，也不表示目标当时在线。

支持的快照路径如下：

| 模式 | 采集路径 |
|---|---|
| `env` | `proc/version`、`etc/os-release`、`proc/cmdline`、`proc/meminfo`、`proc/swaps`、`proc/device-tree/model`、`proc/device-tree/compatible` |
| `kernel` | 候选 `var/log/kern.log`、`var/log/messages`、`var/log/dmesg`、`proc/last_kmsg`；逐项记录是否存在 |
| `process` | `proc/<pid>/status`、`limits`、`wchan`、`cgroup`、`mountinfo` |

live 环境模式从目标 `/proc`、`/etc` 和设备树文件采集；若目标 `/etc/os-release` 是符号链接，只接受标准目标 `/usr/lib/os-release` 或 `../usr/lib/os-release`，并在 manifest 中记录实际读取的相对路径。其他符号链接或缺少 `readlink` 时会记录为 `unsafe_path` / `tool_missing`，不会跟随读取。live kernel 模式读取目标 `dmesg`。进程模式只读取列出的五个 `/proc/<pid>` 文件。采集器不会默认导出 `environ`、完整 `cmdline`、core dump、内存映射或整棵 sysfs。离线模式的启动参数文件来自目标快照的 `proc/cmdline`，应按目标系统的数据分发规则保管输出；离线模式不跟随任何样本符号链接。

## 输出与状态

成功创建后，输出目录包含：

- `manifest.json`：模式、live/offline 来源、来源根目录、PID（适用时）、采集器时间、逐项来源/文件/状态/错误说明和 `command_exit_code`（文件项为 `null`，live dmesg 在可用时记录实际退出码），采样范围和截断上限。
- `summary.txt`：上述范围与状态的便于阅读摘要。
- 按采集项命名的文本文件，例如 `proc-meminfo.txt`、`kernel-dmesg.txt` 或 `process-4242-cgroup.txt`。

每个采集项状态为 `collected`、`truncated`、`empty`、`missing`、`permission_denied`、`unsafe_path`、`tool_missing` 或 `error`。任何缺项、权限错误、空数据或截断都会使总体 `collection_status` 为 `partial`；采集流程已完成时，部分结果仍以退出码 0 返回。源文件读失败会按项记录为 `error`，仍可交付其他项；输出目录的临时文件、逐项 metadata、manifest 或 summary 写入失败则以非零状态退出，不打印成功摘要。无效参数、已有输出路径、不能创建输出目录或不支持的 live 平台也以非零状态退出。

采集限制按输入类型区分，并写在 `manifest.json` 中：

- 环境和进程文件从开头读取最多 66,560 字节（64 KiB 加一个 1 KiB 探测块），最多保留 65,536 字节，然后最多输出 120 行、每行 240 字节。单项文本输出最多 28,920 字节。
- 离线 kernel 日志用 `tail -c` 保留最近 65,536 字节，再由环形行缓冲保留最近 120 行、每行最多 240 字节。`wc -c` 会检查日志总大小，`tail` 的实现可能需要扫描整个源日志；保存到输出目录的数据仍受上限约束。
- live `dmesg` 作为命令流直接送入有限行缓冲，只保留末尾 120 行、每行最多 240 字节。输入字节没有单独上限，范围是目标内核提供的有限日志环；采集器不把完整输出写入临时文件。stderr 与日志合并保存在有界输出中；manifest 记录生产命令实际退出码，并区分 `permission_denied`、`error` 和成功但无记录的 `empty`。

DT model/compatible 的 NUL 分隔符会转换为换行，控制字符会被替换以便安全查看。脚本使用 `head -c`、`tail -c`、`awk`、`wc`、`tr` 等 Linux/BusyBox 常用工具，不需要 GNU 专有选项；必需元工具缺失时会在创建输出目录前以非零状态退出，可选的 `dmesg`、`tail` 或 `tr` 缺失会写入逐项状态。输出目录和文件按当前用户私有权限创建。

## 解读边界

这是一组非原子快照。进程、计数器和内核日志可能在采样期间继续变化；离线快照也可能不完整或早于故障。缺少可选文件、没有 dmesg 权限或单次读数都不代表目标健康。`/proc/<pid>/cgroup` 和 `mountinfo` 仅为后续检查提供证据，采集器不会猜测 cgroup 挂载根、自动遍历祖先限额或读取 memory controller 计数器。

解释 OOM 时，应把同一故障时段的内核记录与进程 cgroup、对应挂载、有效祖先限制和事件计数对照；继续按 `embedded-perf-debug` 的分支区分 memcg 限额、全局回收/OOM 和受约束分配。RSS、MemAvailable、一次 dmesg 或本工具的 `partial` 状态都不足以独立证明根因。主机工具测试和教学夹具不能替代目标板验证。
