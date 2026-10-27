---
name: embedded-perf-debug
description: |
  用于诊断嵌入式 Linux 的 OOM、内存分配失败或增长、内核 Oops/panic，以及 CPU、内存带宽或 I/O 性能退化。
---

# embedded-perf-debug

> 性能与稳定性排障方法：**取证 → 假设 → 验证 → 修复 → 回归**。平台无关。

## 主用与配合

需要分析受限证据采集结果时，读取 [embedded-debug-workflow 的采集说明](../embedded-debug-workflow/references/evidence-collection.md)；memcg OOM 教学示例见 [memcg-oom.md](references/cases/memcg-oom.md)。

本技能主用于已出现明确内存压力/分配失败、OOM、内核 Oops/panic 或性能退化的任务。症状尚未定位、责任层不明时，配合 [embedded-debug-workflow](../embedded-debug-workflow/SKILL.md)；socket 队列、连接或网络相关 fd 问题，配合 [embedded-networking](../embedded-networking/SKILL.md)。需要一次性系统取证命令或字段速查时，按需读取 [forensics-cheatsheet.md](references/forensics-cheatsheet.md)。

## 任务入口与交付

- **目标**：区分全局内存压力、memcg 限额、受约束分配和性能路径问题，并用下一项测量验证候选原因。
- **输入**：故障表现、负载/触发条件和时间窗、运行版本、内核日志、全局或进程资源读数，以及可用的 cgroup/挂载证据。缺少目标或时间信息时标为未知；可从已有日志和有限快照继续。
- **可继续与需补充的信息**：能够根据最强观测提出一个可证伪假设时即可继续。若要定性 memcg OOM，应补足进程 cgroup 路径、对应的挂载映射、有效祖先限制和故障前后事件计数；无法取得时报告具体缺项。
- **证据分支**：把 kernel OOM 记录与进程归属和 cgroup 事件对应；全局 OOM 与 memcg OOM 分开；申请阶数、zone、GFP 或 DMA/CMA 约束作为单独分支；CPU、内存带宽、I/O、温度按观察选择，不能由一个 RSS 读数推断。
- **产物**：按时间列出来源、原始观测和采样窗口，再列候选原因、预期证据、反证和下一项低成本测量；给出最小修复边界和针对性回归条件。
- **成功/失败标准**：成功是观测支持具体范围，且回归覆盖相同负载和时间窗；未能复现或缺少关键归属数据时应报告未决问题。主机快照、合成示例和静态分析不能宣称为目标板验证。

## 核心原则

**先取证，再判断。** 观测值用于提出假设，不能单独证明泄漏、耗尽或碎片化。每轮记录预期、证据和下一步；新证据可以直接指向任一层，不要求固定顺序。

---

## 命令与字段速查

需要系统快照、cgroup、进程、Oops 获取、CPU/I/O 或设备字段命令时，按当前故障分支读取 [forensics-cheatsheet.md](references/forensics-cheatsheet.md)。指定进程的 PID/TID 验证、线程状态、长跑 RSS 与 thermal 采样统一见 [embedded-debug-workflow 的 process-sampling.md](../embedded-debug-workflow/references/process-sampling.md)。所有现场命令须明确在 HOST 或 TARGET 执行；权限、工具或字段不可用时记录具体原因。

## OOM 范围与候选方向

`dmesg` 中的 OOM 或分配失败记录只是起点。先判断失败涉及全局内存、某个 memcg 限额，还是受分配约束的路径；不要只凭 RSS、`free` 或一次分配失败下结论。反复故障还应记录失败频率、采样间隔和内存增长速率，以区分持续压力与短时尖峰。

| 候选方向 | 可观察线索 | 需要的佐证 |
|---|---|---|
| **进程或内核内存持续增长** | RSS、匿名内存、slab、socket memory 或 cgroup usage 上升 | 多次采样确认增长类别；需要堆/对象归属或分配器证据才能判定泄漏。RSS 上升也可能来自缓存、负载变大或分配器保留内存。 |
| **memcg 限额** | OOM 日志指向 memory cgroup；事件附近 v2 `memory.events` 计数变化 | 检查任务所属 cgroup、祖先层级的有效限额、`memory.current`、`memory.max` 和 `memory.events`。主机仍有空闲内存也可能发生 cgroup OOM。 |
| **全局回收 / OOM** | 内核日志显示全局 OOM 路径；系统压力和回收证据在时间上吻合 | 将完整内核日志与 `/proc/meminfo`、可用时的 PSI，以及同一时段的负载采样对照。`MemAvailable` 或 `MemFree` 单独都不是定论。 |
| **受约束分配 / 可能的碎片化** | 有些空闲内存，但某类分配失败 | 从失败现场确认申请的 order/大小、zone、GFP 或 DMA/CMA 约束；适用时查看 `/proc/buddyinfo`、`/proc/zoneinfo` 和 CMA 证据。空闲内存总量不能单独证明碎片化。 |

外设或传输链路失败本身不能作为 OOM 根因。它可能是相关症状，也可能是独立故障；应根据自身日志和上述内存证据分别判定。

### 内存增长取证

跨时段的 RSS 增长可提示泄漏或无界保留，但也可能来自负载规模、页缓存、分配器 arena、文件映射或内核记账。按 [process-sampling.md](../embedded-debug-workflow/references/process-sampling.md) 的有界 sampler 观察同一进程；若要定性 OOM，还需对照相同时间窗内核日志、进程 cgroup 归属、适用的祖先限制和事件计数。只有 RSS 曲线不能判定泄漏，曲线趋稳也不能排除其他类别继续增长。

### 分配约束与全局余量

```bash
# TARGET：仅在 procfs 可读时检查全局内存快照
cat /proc/meminfo | grep -E "MemFree|MemAvailable|Slab|SReclaimable"
```

- 分配失败时 `MemFree` 或 `MemAvailable` 仍高，**不能证明发生碎片化**。先确认申请 order/大小、可用 zone、DMA/CMA 需求、cgroup 记账、回收策略，以及调用方是否会重试。
- 将 `/proc/buddyinfo` 中的 order 与请求阶数比较，并查看 `/proc/zoneinfo` 水位；仅在内核支持且与问题有关时再查 pagetype/CMA。它们只是瞬时快照，因为分配器状态会变化。
- `MemAvailable` 低表示内存压力，单独不能证明 OOM 范围或根因。应与同一时段的内核日志和 cgroup 计数交叉确认。

---

## 未配置 swap 时的注意事项

部分嵌入式系统未配置 swap。在 TARGET 上用 `swapon --show` 或读取 `/proc/swaps` 查看当前状态；命令/文件不可用时记录具体原因：

- `SwapTotal: 0` 表示当前没有配置 swap，不能据此判断全局内存耗尽，也不能解释某次进程被杀。
- 没有 swap 时无法通过换页回收匿名内存，但 OOM 仍可能由 memcg 限额或受约束分配触发。
- 只有在 zram 已配置并启用时才考虑它；应检查目标系统，不要根据板卡型号或 swap 总量推测。

---

## 进程存在但没有响应

指定进程/线程的 PID/TID 命令参数和状态观察统一见 [process-sampling.md](../embedded-debug-workflow/references/process-sampling.md)。`TracerPid` 非零表示有 tracer 附加，不等于任务停止；与 `State` 联读：`t` 是 tracing stop、`T` 是 job-control stop、`Z` 是已退出但未回收。多线程进程需按证据检查相关 TID；等待点和系统调用只是观测，不单独证明死锁。

## Kernel Oops 符号化

**看到 Oops 或 panic 时先保留现场。** 从 TARGET 获取的日志及其构建身份必须与 HOST 上待解码的未 strip `vmlinux`、模块和源码完全匹配；源码行解码需要匹配的 `CONFIG_DEBUG_INFO`。`System.map` 只含内核符号地址，不能提供源码行。解释绝对地址时应考虑运行时重定位/KASLR，使用目标运行时偏移和匹配的解码工具，不要凭符号地址任意相减。构建信息或调试数据缺失时，报告未解析的栈帧。

若日志还未导出，只有在目标 SSH 配置、权限与采集通道都已确认时才使用 [forensics-cheatsheet.md](references/forensics-cheatsheet.md) 中的 HOST 采集示例；否则标注 Oops 日志 unavailable，不猜目标主机或写入路径。

## 性能瓶颈定位

按最强观测选择下一项测量，不要求先排除无关层。进程级 CPU/RSS 或传感器长期趋势需要先加载 [process-sampling.md](../embedded-debug-workflow/references/process-sampling.md)；具体工具、字段与前置条件见 [forensics-cheatsheet.md](references/forensics-cheatsheet.md)。

### CPU

确认单核利用率、任务亲和性和 runnable 队列是否与响应退化同一时间出现。单核接近 100% 是该核可能饱和的线索，不代表系统所有核都饱和；上下文切换多可能来自锁竞争、唤醒或正常并发，需跟踪区分。

### 内存带宽

多路缩放和格式转换等场景中，内存带宽可能先于 CPU 成为瓶颈。若目标内核支持硬件计数器，比较同一工作负载下的 cache/bandwidth 事件；采集工具和计数器缺失时记录 unavailable。

### I/O

结合设备队列、吞吐、延迟、内核错误和同步写入时长判断。单个 `%util` 或 `await` 值不足以证明设备故障；存储类型与驱动会影响这些指标的解释。

### 温度与降频

温度曲线和频率变化可能解释“运行一段时间后变慢”。读取热区时使用统一 sampler，保留每个 zone 的 `type` 和原始值；只有目标 BSP/驱动映射已确认时才赋予具体传感器含义。标准 thermal sysfs `temp` 单位为 millidegree Celsius，不可将未知 vendor 字段套用该单位，也不可默认 thermal zone 0 是 CPU。

## 长跑测试

采样应覆盖实际触发窗口，报告间隔、持续时长和目标身份。指定进程的 RSS、系统 load average 与 thermal 使用唯一的 [process-sampling.md](../embedded-debug-workflow/references/process-sampling.md) 采样器：最多 121 行、5 秒间隔、默认输出当前终端、不创建或覆盖文件。它不解析 `top` 输出列，也不把 load average 当 CPU 利用率。时间窗口内没有复现只能说明该窗口内未出现故障。

## 边界与注意

- **先记录现场、假设和验证结果**；让新证据决定下一步
- OOM 诊断至少区分全局压力、memcg 限额和分配约束；不要从单一指标宣布根因
- Oops 源码行需要匹配的 `vmlinux` 调试信息；`System.map` 不能单独提供源码行
- 不要把「跑久了变慢」一律归因泄漏，先查温度降频
- 实测数据用具体数字，不用「内存偏高」「性能较差」这类描述

## 参考资料

- [Control Group v2 memory controller](https://docs.kernel.org/admin-guide/cgroup-v2.html)
- [The `/proc` filesystem: buddyinfo and fragmentation diagnostics](https://docs.kernel.org/filesystems/proc.html)
- [CMA debugfs interface](https://docs.kernel.org/admin-guide/mm/cma_debugfs.html)
- [Kernel bug hunting and Oops decoding](https://docs.kernel.org/admin-guide/bug-hunting.html)
- [`/proc/<pid>/status` field definitions](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html)
