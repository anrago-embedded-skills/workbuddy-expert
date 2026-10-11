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

## 标准取证命令集

```bash
# TARGET（目标机）：除非另有 HOST 标注，下列只读快照均在受影响系统执行
# 1. 内核日志（OOM killer / Oops 线索）
dmesg -T | tail -200
dmesg | grep -iE "oom|killed process|out of memory"

# 2. 内存全局
cat /proc/meminfo
free -h

# 3. 各进程内存占用
ps -eo pid,ppid,user,vsz,rss,stat,comm --sort=-rss | head -30
cat /proc/*/status 2>/dev/null | grep -E "^Name|^Pid|^VmRSS|^VmSwap|^Threads"

# 4. 进程内存映射（看谁在吃内存）
cat /proc/<pid>/maps
pmap -x <pid> | tail -30

# 5. CMA 快照（仅在系统启用 CMA 时；数值本身不证明分配成功或失败）
grep -E "CmaTotal|CmaFree" /proc/meminfo

# 6. 高阶分配候选线索；需与失败日志中的 order / zone / GFP 约束一起看
cat /proc/buddyinfo
cat /proc/zoneinfo

# 7. swap 是否实际配置
swapon --show      # 查看当前已启用的 swap

# 8. 文件系统（磁盘满也可能造成应用异常）
df -h

# 9. 进程所在 cgroup（按 /proc/<pid>/cgroup 选择对应挂载点和层级）
cat /proc/<pid>/cgroup
```

对于 cgroup v2，找到进程所在的 cgroup 目录，对比事件前后的 `memory.current`、`memory.max` 和 `memory.events`。对于 cgroup v1，检查已挂载的 memory controller 及其限额和失败计数。具体路径和计数器取决于目标系统的 cgroup 版本与服务管理器。

---

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

```bash
for i in $(seq 1 10); do
  echo "=== $i ==="; date; ps -o pid,rss,comm -p <pid>; sleep 60
done
```

RSS 单调增长可作为泄漏或无界保留的候选线索，但不能证明根因：负载规模、页缓存、分配器 arena、文件映射和内核记账内存都可能产生不同趋势。判定原因前，先找出增长类别及其所有者。曲线趋于平稳符合有界缓存的表现，但不能单独排除其他类别仍有泄漏。

### 分配约束与全局余量

```bash
cat /proc/meminfo | grep -E "MemFree|MemAvailable|Slab|SReclaimable"
```

- 分配失败时 `MemFree` 或 `MemAvailable` 仍高，**不能证明发生碎片化**。先确认申请 order/大小、可用 zone、DMA/CMA 需求、cgroup 记账、回收策略，以及调用方是否会重试。
- 将 `/proc/buddyinfo` 中的 order 与请求阶数比较，并查看 `/proc/zoneinfo` 水位；仅在内核支持且与问题有关时再查 pagetype/CMA。它们只是瞬时快照，因为分配器状态会变化。
- `MemAvailable` 低表示内存压力，单独不能证明 OOM 范围或根因。应与同一时段的内核日志和 cgroup 计数交叉确认。

---

## 未配置 swap 时的注意事项

部分嵌入式系统未配置 swap。用 `swapon --show` 或 `/proc/swaps` 查看当前实际状态：

- `SwapTotal: 0` 表示当前没有配置 swap，不能据此判断全局内存耗尽，也不能解释某次进程被杀。
- 没有 swap 时无法通过换页回收匿名内存，但 OOM 仍可能由 memcg 限额或受约束分配触发。
- 只有在 zram 已配置并启用时才考虑它；应检查目标系统，不要根据板卡型号或 swap 总量推测。

---

## 「进程在但应用假活」

这比崩溃更隐蔽——进程还在，但不响应。常见原因：

| 状态 | 含义 | 检查 |
|---|---|---|
| `T` (Stopped) | 作业控制停止 | `cat /proc/<pid>/status \| grep State` |
| `t` (Tracing stop) | 当前处于 ptrace tracing stop | 同上，并检查 `TracerPid` |
| `Z` (Zombie) | 已退出但父进程未回收 | `ps -ef \| grep defunct` |

```bash
cat /proc/<pid>/status | grep -E "^State|^TracerPid"
```

`TracerPid` 非 0 表示有 tracer 附加，但本身不表示任务已停止。应与 `State` 一起判断：小写 `t` 表示 tracing stop，大写 `T` 表示 job-control stop。多线程进程的线程状态可能不同，可查看相关 `/proc/<pid>/task/<tid>/status`。

---

## Kernel Oops 符号化

### 症状特征

```
[ 123.456] BUG: kernel NULL pointer dereference
[ 123.456] Unable to handle kernel ...
[ 123.456] Internal error: Oops: ...
[ 123.456] Call trace:
```

**看到 Oops 就停手，先取证。**

### 离线符号化流程（在可访问构建产物的主机上执行）

```bash
# HOST: 从 TARGET 通过 SSH 读取日志；重定向会将文件保存在主机
ssh root@<board> 'dmesg -T' > ./oops.txt

# 另一种方式：如果日志已保存在目标机上，改用 scp 传到主机；不要把它当作上面 SSH 命令的后续步骤：
# scp root@<board>:/tmp/oops.txt ./oops.txt

# 2. HOST: 选择与运行内核和模块匹配的构建产物
#    保留带 CONFIG_DEBUG_INFO 的未 strip vmlinux 和匹配的模块 .ko 文件。

# 3. HOST: 查看调用栈
grep -A20 "Call trace" ./oops.txt
#    形如：[<c010a1b8>] (unwind_backtrace) from [<c010a2cc>] (show_stack+0x10/0x14)

# 4. HOST: 使用匹配内核源码树中的解码脚本
./scripts/decode_stacktrace.sh ./vmlinux /path/to/kernel/source /path/to/modules < ./oops.txt
```

**要点**：
- 内核映像必须与目标机当前运行的构建完全匹配；仅源码版本相同还不够。源码行解码需要匹配的、未 strip 且带 `CONFIG_DEBUG_INFO` 的 `vmlinux`。模块栈帧需要相同构建的模块文件和调试信息。
- `System.map` 是内核符号地址表，可辅助解析符号名，但本身不含源码行信息，不能替代 `vmlinux` 调试信息。
- 解释绝对地址时要考虑运行时重定位/KASLR。使用目标机运行时偏移及匹配的内核解码工具，不要任意用符号地址做减法。
- 目标机负责提供日志；主机使用匹配的构建树和产物解码。若产物或调试信息缺失，应说明哪些栈帧仍无法解析。

---

## 性能瓶颈定位

根据当前最强证据选择下一项测量。温度曲线可能直接指向降频；分配失败可指向内存约束；持续增长的 `Send-Q` 可提示传输路径问题。证据已定位问题时，无需先排除无关层。

### 1. CPU

```bash
top -H                      # 按线程看
pidstat -p <pid> 1          # 单进程
vmstat 1                    # 看 r（就绪队列）和 cs（上下文切换）
```

- 单核接近 100% 是该核可能饱和的线索；结合任务亲和性、有效工作量和 per-CPU 负载确认。
- 上下文切换很多可能来自锁竞争、频繁唤醒或正常高并发；用锁/调度跟踪进一步区分。
- runnable 队列较长表示存在 CPU 调度压力；需结合每核利用率和任务可运行状态判断。

### 2. 内存带宽

```bash
perf stat -e cache-misses,cache-references -- <command> [args]   # 需内核支持
```

多路缩放/格式转换密集场景，**内存带宽常先于 CPU 成为瓶颈**。

### 3. IO

```bash
iostat -x 1                 # %util、await
vmstat 1                    # bi/bo
dmesg | grep -i slow
```

### 4. 温度与降频（易误判）

```bash
cat /sys/class/thermal/thermal_zone*/temp
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq
```

**关键**：过热降频会让性能问题「跑一会儿就变慢」，**极易被误判为内存泄漏**。先查温度再下结论。

---

## 长跑测试

复现长时间问题时，应覆盖触发窗口并记录采样时长。按 Ctrl-C 停止采样；短时间未复现只说明该观察区间内未出现问题。

```bash
while true; do
  echo "$(date) mem=$(free -m | awk '/Mem:/{print $3}') \
        rss=$(ps -o rss= -p <pid>) \
        temp=$(cat /sys/class/thermal/thermal_zone0/temp)"
  sleep 300
done | tee /tmp/longrun.log
```

选择可写且空间充足的日志目录。采样中的相关性只能作为线索；应结合事件时序和资源证据判断原因。

记录到日志，出问题时能回看趋势，定位恶化起点。

---

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
