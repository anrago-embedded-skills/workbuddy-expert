---
name: embedded-debug-workflow
description: |
  用于排查根因或责任层尚未明确的嵌入式 Linux 异常，包括进程/IPC 卡住；也适用于涉及 Docker/nginx 或 POSIX 线程、epoll 的应用运行与部署问题。
---

# embedded-debug-workflow

> 嵌入式排障的通用方法：**取证 → 假设 → 验证 → 更新判断 → 回归**。平台无关。

## 主用与配合

本技能主用于症状尚未定位、需要用证据判断从应用、系统、驱动或硬件哪一层开始的问题。遇到明确的 OOM、内存分配失败/增长、Oops/panic 或 CPU/内存带宽/I/O 退化时，配合 [embedded-perf-debug](../embedded-perf-debug/SKILL.md)；已指向 socket、网络队列或网络相关 fd 时，配合 [embedded-networking](../embedded-networking/SKILL.md)。

- 需要一份精简的现场采集、假设验证和修复检查清单时，读取 [debug-playbook.md](references/debug-playbook.md)。
- 需要使用受限的系统证据采集器时，读取 [evidence-collection.md](references/evidence-collection.md)；脚本位于 [scripts/collect-evidence.sh](scripts/collect-evidence.sh)。
- 任务明确涉及 Docker/nginx、POSIX 线程或 epoll，或证据需要检查容器部署限额/应用线程时，读取 [app-runtime.md](references/app-runtime.md)。
- 跨领域任务、命令和交付约定见 [engineering-workflow.md](references/engineering-workflow.md)；来源、版本和验证记录要求见 [validation-policy.md](references/validation-policy.md)。

## 任务入口与交付

- **目标**：用可复查证据缩小故障责任层，并给出区分候选原因的下一项检查。
- **输入**：现象、触发条件/复现频率、近期变更、固件或软件版本，以及可用日志、目标快照或进程 PID。目标型号、复现条件或日志缺失时，将其标为未知；可先从已有材料继续。
- **可继续与需补充的信息**：现有证据足以选择一个低风险区分实验时即可继续；若结果会依赖目标专有路径、权限或采样时点，则列出所需的精确目标数据，不把推测填成事实。
- **证据分支**：按现有观测选择应用/进程、系统/内核、驱动或硬件方向；OOM、资源增长、Oops/panic 或明确性能退化时配合 `embedded-perf-debug`。网络队列或 socket 证据指向网络路径时配合 `embedded-networking`。
- **产物**：记录带来源和时间的观测、竞争假设、各自预期、能区分它们的下一步测量、最小修复边界和回归验收条件；区分已验证事实与待验证判断。
- **成功/失败标准**：成功是现有证据能支持一个明确范围，且修复回归匹配实际目标条件；证据不足时应报告具体缺项和可执行的下一次采样。主机或离线夹具检查不能算作板上验证。

## 核心原则

1. **证据决定起点** — 从日志、跟踪、测量或可复现故障所指向的层开始，再沿证据跨层追查。
2. **区分观测和假设** — 记录测量结果、可能含义，以及什么结果会推翻假设。
3. **验证修复时一次只改一个变量** — 保留足够证据，以便判断变化带来的结果。
4. **按实际条件验证** — 有目标板时验证板上行为；没有目标板时报告主机检查结果，并注明板上行为尚未验证。

---

## 证据驱动的定位

根据第一条可靠观测选择排查层，再沿调用关系、依赖和影响追查。例如，Kernel Oops 可从驱动或内核开始；`read()` 失败可从应用或 IPC 边界开始；测得电压跌落可从供电开始。没有固定的层级顺序。

### 各层的证据来源

| 层 | 排查手段 |
|---|---|
| **应用层** | 日志、`strace`、`gdb` 断点、代码走查 |
| **系统层** | `systemctl status`、`journalctl`、`dmesg`、资源占用 |
| **驱动层** | `dmesg` 驱动日志、`/sys/class/video4linux`、`media-ctl -p`、`/proc/interrupts` |
| **硬件层** | 万用表/示波器、寄存器读值、芯片手册 |

一条观测可能同时指向多个层。明确记录竞争假设，并优先选择能区分它们且成本最低的测量。

---

## 标准排障流程

### Phase 1：澄清与现状固化

收集当前可获得的信息：目标板型号、SoC 和固件/构建版本；可复现性和触发条件；此前尝试；近期代码、配置或硬件变更。如果无法访问板子或日志，应把未知的目标信息明确标为未知。

### PID/TID 命令参数

先在同一个 TARGET shell 运行此参数段，再执行后续使用 PID/TID 的命令。将两个示例数字替换为目标现场确认的十进制 PID/TID；没有单独线程检查时，`target_tid` 保持为进程主线程 ID。后续命令引用验证过的变量，并对路径和参数加引号。

```sh
# TARGET：在同一个目标 shell 中先设置并验证 PID/TID；替换为现场确认的十进制 ID
target_pid=4242
target_tid=$target_pid
is_positive_decimal_id() {
  case "$1" in ''|*[!0-9]*|0*) return 1 ;; *) return 0 ;; esac
}
for target_id in "$target_pid" "$target_tid"; do
  if ! is_positive_decimal_id "$target_id"; then
    printf '%s\n' 'PID/TID must be a positive decimal integer' >&2
    exit 2
  fi
done
target_proc="/proc/${target_pid}"
target_status="${target_proc}/status"
target_task="${target_proc}/task/${target_tid}"
target_task_status="${target_task}/status"
```

```bash
# TARGET：固化目标系统现状；不要在 HOST 读取本机 /proc 代替目标证据
uname -a
cat /etc/os-release
cat /proc/device-tree/model
free -h
df -h
```

### Phase 2：取证（不是猜测）

```bash
# TARGET：采集目标系统内核和服务日志
dmesg -T | tail -200        # 内核侧
journalctl -b -p err        # 系统侧
```

使用 `timeout` 的示例要求目标系统提供兼容的 BusyBox/coreutils 命令；先确认工具选项，缺少时换用目标上可用的有界方式。关键是**抓到出问题的那一刻**，而不是事后回忆。

### Phase 3：假设与验证

写明假设、它预期出现的观测，以及什么结果会削弱这个假设。例如：

> 假设：进程内存持续增长可能与 OOM 有关
> 验证：采样约 10 分钟，记录 RSS、所属 cgroup 计数和内核 OOM 日志

```bash
# TARGET：复用同一 shell 中已验证的 target_status；共 11 次采样，间隔 60 秒
i=0
while [ "$i" -le 10 ]; do
  date
  awk '$1 == "VmRSS:" { print "rss_kb=" $2; found=1 } END { if (!found) print "rss_kb=unavailable" }' "$target_status"
  if [ "$i" -lt 10 ]; then sleep 60; fi
  i=$((i + 1))
done
```

RSS 增长只是线索，不能证明泄漏；下结论前先查明增长的内存类别及其归属。证据直接指向其他层时，可立即从该层开始调查，无需先完成无关检查。

### Phase 4：修复与验证

修复后按当前条件验证受影响的行为。有目标板时检查目标功能和相关日志；没有目标板时报告主机构建、静态检查结果，并注明尚待完成的目标验证。若变更可能影响相关功能，也应做回归检查。

### Phase 5：长跑验证

长时间故障应覆盖复现窗口进行采样，并记录采样时长。下文的 TARGET 采样器将初始窗口限制在约 10 分钟；Ctrl-C 可提前停止。短时间运行只能说明采样区间内的行为。

---

## 「进程在但没反应」的排查

这类问题最耗时间，先用这三招：

```bash
# TARGET：PID 参数段须已在同一 shell 中验证
grep -E "^State|^TracerPid" "$target_status"
ps -eo pid,ppid,stat,comm | awk '$3 ~ /Z/'   # 僵尸进程
cat "${target_proc}/wchan"                    # 内核态阻塞在哪
```

- `TracerPid` 非 0 → 有 tracer 附加；不能单独证明任务已停止
- `State: t` → tracing stop；`State: T` → job-control stop
- `State: Z` → 僵尸，父进程没回收
- `wchan` 显示阻塞函数 → 内核态卡在某处

多线程进程中的线程状态可能不同。先从目标任务目录的输出确认 TID，再在同一 shell 中设置并验证线程 ID：

```sh
# TARGET：把 4343 替换为从目标任务目录确认的十进制 TID
target_tid=4343
if ! is_positive_decimal_id "$target_tid"; then
  printf '%s\n' 'target_tid must be a positive decimal integer' >&2
  exit 2
fi
target_task="${target_proc}/task/${target_tid}"
target_task_status="${target_task}/status"
```

```sh
# TARGET：读取已验证 TID 的线程状态
grep -E "^State|^TracerPid" "$target_task_status"
```

```bash
# TARGET：附加到已验证的目标 PID，最多跟踪 10 秒
timeout 10s strace -p "$target_pid" -f
```

**不要一上来就重启服务**——重启会毁掉现场，先取证。

---

## 进程模型与 IPC

多进程架构下的问题常被误判为"程序崩了"，实际是**进程间通信阻塞**或**子进程没被回收**。

### 进程树与状态

```bash
# TARGET：PID 参数段须已在同一 shell 中验证
ps -ef --forest                       # 进程树，看父子关系
ps -eo pid,ppid,stat,comm --sort=ppid # 按父进程排序
grep -E "^State|^Threads|^FDSize" "$target_status"
ls "${target_proc}/task"             # 线程 ID 列表
```

### 僵尸进程（子进程已退出，父进程未回收）

```bash
# TARGET：检查目标系统上的僵尸进程
ps -eo pid,ppid,stat,comm | awk '$3 ~ /Z/'
```

僵尸已退出，不再执行用户态代码；在父进程回收前，仍占用 PID，并保留少量内核任务记录与记账信息。单个僵尸不执行代码；大量未回收的僵尸会占用 PID 空间。

```c
// 父进程必须回收子进程
while (waitpid(-1, &status, WNOHANG) > 0);   // 循环回收所有已退出子进程
```

带 `WNOHANG` 的循环只回收当前已退出的子进程；返回 0 表示仍有匹配子进程运行。使用选项 0 的 `waitpid()` 会等待子进程退出，这种等待本身不证明死锁。

### 管道与命名管道（FIFO）

先确认目标临时路径未被占用，再创建 FIFO。读写命令需要在两个 TARGET 终端并发运行，各自最多等待 10 秒。

```sh
# TARGET：确认路径未被占用后创建临时命名管道
if [ -e /tmp/myfifo ]; then
  printf '%s\n' 'temporary FIFO path already exists' >&2
  exit 2
fi
mkfifo /tmp/myfifo
ls -l /tmp/myfifo
```

```sh
# TARGET 终端 A：等待写端，最多 10 秒
timeout 10s cat /tmp/myfifo
```

```sh
# TARGET 终端 B：在终端 A 等待期间执行，最多 10 秒
timeout 10s sh -c 'printf "hello\\n" > /tmp/myfifo'
```

FIFO 端点打开时可能等待对端；有限的管道缓冲区写满后，写操作会阻塞；所有写端关闭后，读端才会收到 EOF。Linux 上 FIFO 的 `O_RDWR` 打开方式可能让写端始终保持打开，从而收不到 EOF；紧密循环重试 `EAGAIN` 则可能占满一个 CPU 核。应用应按读写角色选择打开模式，使用 `poll`/`epoll` 或截止时间，处理 `EINTR`、`EAGAIN` 和 EOF，并提供取消机制。诊断等待应像上面的命令一样设置时限。

### 其他 IPC 手段

| 手段 | 特点 | 适用 |
|---|---|---|
| **pipe()** | 匿名 fd；常由 fork 继承，也可由进程间 fd 传递 | 本地进程间通信 |
| **FIFO** | 有名，任意进程 | 无关进程间 |
| **socketpair** | 双向，全双工 | 父子双向通信 |
| **Unix Domain Socket** | 本地套接字 | 本地服务（最灵活） |
| **消息队列** | 内核管理 | 少量数据 |
| **共享内存** | 需配信号量 | 大块数据 |

```c
// Unix Domain Socket（推荐：支持双向、可多客户端）
int fd = socket(AF_UNIX, SOCK_STREAM, 0);
struct sockaddr_un addr = {.sun_family = AF_UNIX};
strcpy(addr.sun_path, "/tmp/my.sock");
bind(fd, (struct sockaddr*)&addr, sizeof(addr));
listen(fd, 5);
```

**共享内存的坑**：没有同步机制，**必须配信号量或互斥锁**，否则数据竞争难以复现。

### 进程卡死排查

```bash
# TARGET：复用同一 shell 中已验证的 PID/TID 参数
grep -E "^State|^TracerPid" "$target_status"
cat "${target_proc}/wchan"              # 内核态阻塞在哪
timeout 10s strace -p "$target_pid"    # 限时采样系统调用
ls -l "${target_proc}/fd"                # 查看目标持有的 fd
```

**判断逻辑**：
- 阻塞在 FIFO `read` → 当前没有可读数据；检查两端 fd、写入时序和系统调用记录，不能推断对端此前是否读过数据
- 阻塞在 `waitpid` → 可能正在等待仍运行的子进程；结合目标子进程状态和 `waitpid` 选项判断
- 阻塞在 `write` + FIFO 缓冲满 → 对端消费慢

---

## 交叉编译与部署

部署命令由实际 SDK/BSP 和目标环境决定，不存在通用的 `make ARCH`、工具链前缀或 `ssh` 路径。准备并记录以下信息后，再按项目已有的构建/部署说明执行：

- **HOST 构建身份**：实际 SDK/BSP 版本、源码与配置、编译器 target triple、sysroot、用户态 ABI，以及构建输出的完整路径和校验值。
- **TARGET 身份**：可核验的板卡/设备标识、运行固件与应用版本、目标 ABI，以及可访问的部署通道。不能用 HOST 的 `uname` 或 `/proc` 代替 TARGET 证据。
- **产物匹配**：确认将部署的具体文件由上述构建生成，并与目标 ABI、运行时依赖和服务路径匹配。
- **状态变更范围**：说明将替换的文件/配置、是否重启服务或设备、影响范围及已有授权；按任务范围执行，不把构建成功当成部署完成。
- **恢复路径**：保留当前目标文件/配置或已验证的旧产物，确认失败时可用的访问方式和恢复步骤；数据或启动介质变更还要明确相应备份与恢复条件。

部署后从 TARGET 读取版本/构建标识，验证目标功能和相关日志，并记录实际执行的命令、结果及未完成的板上检查。

---

## 长跑稳定性验证

```bash
# TARGET：复用 PID 参数段中的 target_status；VmRSS 单位为 kB，窗口最多约 10 分钟
sample_thermal() {
  found=0
  for zone_dir in /sys/class/thermal/thermal_zone*; do
    [ -r "${zone_dir}/type" ] && [ -r "${zone_dir}/temp" ] || continue
    zone_type=$(cat "${zone_dir}/type") || continue
    zone_value=$(cat "${zone_dir}/temp") || continue
    printf '%s:%s=%s_mC ' "${zone_dir##*/}" "$zone_type" "$zone_value"
    found=1
  done
  if [ "$found" -eq 0 ]; then printf '%s' unavailable; fi
}
sample=0
while [ "$sample" -le 120 ]; do
  rss_kb=$(awk '$1 == "VmRSS:" { print $2; found=1 } END { if (!found) print "unavailable" }' "$target_status")
  loadavg=$(awk '{ print $1 "/" $2 "/" $3 }' /proc/loadavg)
  thermal=$(sample_thermal)
  printf '%s rss_kb=%s loadavg_1_5_15=%s thermal_zones=%s\n' "$(date)" "$rss_kb" "$loadavg" "$thermal"
  if [ "$sample" -lt 120 ]; then sleep 5; fi
  sample=$((sample + 1))
done
```

在同一 TARGET shell 先运行 PID/TID 参数段。采样上限为 121 行、间隔 5 秒；Ctrl-C 可提前停止，结果输出到当前终端，不创建或覆盖文件。`loadavg` 是系统负载，不是 CPU 利用率；这里不解析依赖 `top` 列位置的值。thermal 记录逐项显示目标实际提供的 `type` 和温度值；Linux thermal sysfs ABI 的 `temp` 单位为 millidegree Celsius。`type` 是驱动提供的 zone 标签；只有目标 BSP/驱动资料能将其对应到实际传感器时，才按该传感器解释。没有成功读取的 type/temp 项时，thermal 字段标为 `unavailable`；传感器含义未知的读数保留为带 zone/type 标签的原始数据，不解释为某个具体传感器。若厂商接口的单位未确认，也不据此得出温度结论。不要把 `thermal_zone0` 默认视作 CPU 温度。

此示例给出有界采样。按复现窗口调整间隔和次数前，估算输出量并选择实际可用的记录位置。

---

## 边界与注意

- 让直接证据决定定位起点；无需先排除无关层
- **不要在没取证时重启服务**——会毁掉现场
- 尽量隔离一个因果变量；需要成组保持接口或生命周期不变量时，按最小完整修复验证
- 报告采样时长；结论只覆盖实际观察到的窗口
- 按现有环境完成验证，并明确列出尚未执行的目标板检查
- 实测数据用具体数字，不用「正常」「没问题」这类描述

## 参考资料

- [`/proc/<pid>/status` state and TracerPid fields](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html)
- [Linux FIFO behavior](https://man7.org/linux/man-pages/man7/fifo.7.html)
- [Linux pipe buffer and blocking behavior](https://man7.org/linux/man-pages/man7/pipe.7.html)
- [Linux thermal sysfs interface and temperature units](https://docs.kernel.org/driver-api/thermal/sysfs-api.html)
