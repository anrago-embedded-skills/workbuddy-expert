---
name: embedded-debug-workflow
description: |
  用于排查根因或责任层尚未明确的嵌入式 Linux 异常，包括进程/IPC 卡住；也适用于涉及 Docker/nginx 或 POSIX 线程、epoll 的应用运行与部署问题。
---

# embedded-debug-workflow

> 嵌入式排障的通用方法：**取证 → 假设 → 验证 → 更新判断 → 回归**。平台无关。

## 主用与配合

本技能主用于症状尚未定位、需要用证据判断从应用、系统、驱动或硬件哪一层开始的问题。遇到明确的 OOM、内存分配失败/增长、Oops/panic 或 CPU/内存带宽/I/O 退化时，配合 [embedded-perf-debug](../embedded-perf-debug/SKILL.md)；已指向 socket、网络队列或网络相关 fd 时，配合 [embedded-networking](../embedded-networking/SKILL.md)。

- 需要精简排障清单，或证据已指向进程树、IPC、FIFO、线程等待时，读取 [debug-playbook.md](references/debug-playbook.md)。
- 需要特定进程/线程状态、PID/TID 命令参数、长跑资源采样或热区数据时，读取唯一规范 [process-sampling.md](references/process-sampling.md)。
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

## 排障流程

1. **澄清现状** — 收集目标板型号、SoC、固件/构建版本、复现条件、此前尝试和近期变更；不可用信息标为未知。
2. **保存现场** — 在故障出现时保留时间戳、相关系统/应用日志和最小相关状态；需要进程细节时先读取 [process-sampling.md](references/process-sampling.md)。
3. **建立可证伪假设** — 写出假设、预期观测、反证，以及能区分候选原因的低风险下一步测量。RSS 增长、阻塞状态或一次错误都只是线索。
4. **修复并回归** — 一次只改一个因果变量；按原触发条件检查功能与日志，注明主机检查和目标板验证各自完成到哪一步。

## 进程无响应与 IPC

进程仍存在不等于应用正常；问题也可能在 IPC 对端、子进程回收、容器限额或系统调用等待。需要 PID/TID 命令时先加载 [process-sampling.md](references/process-sampling.md)，再用同一个 TARGET shell 中已验证的变量。

- `TracerPid` 非零表示有 tracer 附加，不单独表示任务停止；`State: t` 是 tracing stop，`T` 是 job-control stop，`Z` 是已退出而未回收的僵尸。
- `wchan`、系统调用栈和阻塞调用说明当时的等待点，不单独证明死锁或根因。FIFO `read` 可表示当前无数据；`waitpid()` 可等待仍运行的子进程；FIFO `write` 可等待缓冲区空间。
- 重启通常会丢失现场；若必须先恢复服务，应记录未能采集的证据。
- FIFO、多进程树、僵尸回收、Unix socket、共享内存和有界双端 FIFO 检查的条件说明见 [debug-playbook.md](references/debug-playbook.md)。

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

长时间故障应覆盖触发窗口并报告采样间隔与持续时长。需要进程 RSS、系统负载或热区趋势时，使用 [process-sampling.md](references/process-sampling.md) 的唯一有界采样器；它最多输出 121 行到当前终端，不会创建或覆盖日志。没有在短采样窗口内复现，只能说明该观察区间内未出现问题。

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
