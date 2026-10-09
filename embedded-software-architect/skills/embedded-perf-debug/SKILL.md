---
name: embedded-perf-debug
description: |
  Performance and stability forensics: OOM root-cause classification, kernel Oops symbolization, CPU/memory-bandwidth/IO bottleneck analysis.
  TRIGGER when: OOM、内存泄漏、内存不足、内存占用高、out of memory、killed process、OOM killer、碎片化、内存耗尽、卡死、无响应、假活、僵尸进程、Zombie、TracerPid、oops、panic、段错误、kernel crash、内核崩溃、符号化、Call trace、性能瓶颈、CPU 占用高、内存带宽、上下文切换、iostat、vmstat、长跑稳定性、跑久了变慢、发热降频、内存涨、涨内存、内存越来越高、内存一直涨、吃内存、占内存、跑久了会崩、跑久了变慢、用久了就崩、跑一会就死、隔一会崩一次、卡死、卡住、没反应、不动了、假死、耗电、发热、烫、掉速、变卡、越来越慢、看门狗咬死、被 kill、莫名重启、无故重启、设备卡死、机器卡死、板子卡死、越用越慢、越来越慢、越来越卡、跑久了不行、用久了就断、跑一会儿就挂、跑一会儿就没反应、断电重启、老是重启、莫名其妙重启,
  DO NOT TRIGGER when: fd 泄漏与 socket 卡顿（用 embedded-networking）；图像/视频处理慢（用 media-pipeline-linux 或 display-compositor-gpu）,
---

# embedded-perf-debug

> 性能与稳定性排障方法论：**取证 → 定性 → 定位 → 修复 → 长跑验证**。平台无关。

## 核心原则

**先取证，再动手。** 看到 OOM、崩溃、"跑久了变慢"，第一件事永远是抓证据，不是改代码。

---

## 标准取证命令集

```bash
# 1. 内核日志（OOM killer / oops 通常在这里）
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

# 5. DMA / CMA 内存（嵌入式重点）
grep -E "CmaTotal|CmaFree" /proc/meminfo

# 6. swap（0 swap 板子要特别注意）
swapon --show      # 空 = 无 swap

# 7. 文件系统（磁盘满也会表现为异常）
df -h
```

---

## OOM 定性（关键：区分四种根因）

`dmesg` 里有 OOM killer 记录，只是起点。**必须区分**：

| 根因 | 特征 | 判定方法 |
|---|---|---|
| **内存泄漏** | RSS 单调增长 | 隔 N 分钟采样 `ps`，看 RSS 是否单调上升 |
| **碎片化** | 总内存充足但分配失败 | `MemAvailable` 充足但大块分配失败；`Slab` 大 |
| **总量耗尽** | `MemAvailable` 低 | `MemFree` + `MemAvailable` 都低 |
| **外设链路失效** | 进程存在但假活 | 进程在但被 ptrace 冻结/僵尸/状态异常 |

### 泄漏验证（最常见）

```bash
for i in $(seq 1 10); do
  echo "=== $i ==="; date; ps -o pid,rss,comm -p <pid>; sleep 60
done
```

**单调增长且无平台期 → 泄漏**。有平台期 → 可能只是缓存。

### 碎片化 vs 总量

```bash
cat /proc/meminfo | grep -E "MemFree|MemAvailable|Slab|SReclaimable"
```

- `MemFree` 高但应用仍分配失败 → **碎片化**（缺大块连续内存）
- `MemFree` + `MemAvailable` 都低 → **总量耗尽**

---

## 0 swap 板子的特殊性

嵌入式板子（尤其 RK3588）**常常0 swap**：

- `SwapTotal: 0` 是**正常现象**，不是配置错误
- 没有 swap buffer，**OOM 就是真 OOM**，进程直接被杀
- 排查时**不能指望 swap 换页缓解**，必须从内存占用入手
- 部分板子即使显示 swap，也可能因 zram 未配置而无效

---

## 「进程在但应用假活」

这比崩溃更隐蔽——进程还在，但不响应。常见原因：

| 状态 | 含义 | 检查 |
|---|---|---|
| `T` (Stopped) | 被信号暂停 | `cat /proc/<pid>/status \| grep State` |
| `t` (Tracing stop) | 被 ptrace 冻结 | 同上 |
| `Z` (Zombie) | 已退出但父进程未回收 | `ps -ef \| grep defunct` |

```bash
cat /proc/<pid>/status | grep -E "^State|^TracerPid"
```

**`TracerPid` 非 0 说明有人在 ptrace 它**——这是「假活」的关键线索。

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

### 离线符号化流程（Windows 主机可做）

```bash
# 1. 抓取崩溃现场
ssh root@<board> "dmesg | tail -100 > /tmp/oops.txt"
ssh root@<board> "cat /proc/kallsyms > /tmp/kallsyms.txt"

# 2. 拉取内核符号表（关键）
#    System.map 需与板上运行的**完全同版本**内核

# 3. 提取崩溃地址
grep -A20 "Call trace" /tmp/oops.txt
#    形如：[<c010a1b8>] (unwind_backtrace) from [<c010a2cc>] (show_stack+0x10/0x14)

# 4. 符号化：addr - symbol_base 得偏移，结合 System.map 定位源码行
```

**要点**：
- **System.map 必须与板上内核完全同版本**，否则符号全错位
- 需要该内核构建时的符号信息（未 strip 的 vmlinux，或 System.map）
- 无匹配符号表时，只能符号化到 `unwind_backtrace`这类通用帧

---

## 性能瓶颈定位

按此顺序排查，不要跳步。

### 1. CPU

```bash
top -H                      # 按线程看
pidstat -p <pid> 1          # 单进程
vmstat 1                    # 看 r（就绪队列）和 cs（上下文切换）
```

- 单核 100% → 该核为瓶颈
- 大量上下文切换 → 锁竞争或频繁调度
- 大量 runnable → CPU 不够

### 2. 内存带宽

```bash
perf stat -e cache-misses,cache-references ...   # 需内核支持
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

稳定性问题必须用时间换置信度：

```bash
while true; do
  echo "$(date) mem=$(free -m | awk '/Mem:/{print $3}') \
        rss=$(ps -o rss= -p <pid>) \
        temp=$(cat /sys/class/thermal/thermal_zone0/temp)"
  sleep 300
done | tee /tmp/longrun.log
```

记录到日志，出问题时能回看趋势，定位恶化起点。

---

## 边界与注意

- **禁止不取证就改代码**——本skill 最核心的规则
- OOM 定性必须区分四种根因，不要看到 OOM 就一律加内存
- Oops 符号化需要匹配版本的 System.map，拿不到就明说
- 不要把「跑久了变慢」一律归因泄漏，先查温度降频
- 实测数据用具体数字，不用「内存偏高」「性能较差」这类描述