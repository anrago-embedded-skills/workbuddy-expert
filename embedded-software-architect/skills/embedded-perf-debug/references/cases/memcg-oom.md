# 教学案例：memcg 限额触发 OOM

> 下列内容全部是教学夹具，不是板卡采样、历史故障或已验证结果。

## 输入与现象

假设有一次合成采样记录：

| 来源 | 教学输入 |
|---|---|
| 内核日志 | `oom-kill:constraint=CONSTRAINT_MEMCG,...`；`Memory cgroup out of memory: Killed process 4242 (worker)` |
| `/proc/4242/cgroup` | `0::/service.slice/worker.service` |
| `/proc/4242/mountinfo` | `30 21 0:28 / /sys/fs/cgroup rw - cgroup2 cgroup rw` |
| 服务 cgroup `memory.max` | `50331648` 字节 |
| 同一 cgroup `memory.current`（事件前） | `49283072` 字节 |
| 同一 cgroup `memory.events`（事件前 → 事件后） | `max: 3 → 7`；`oom: 0 → 1`；`oom_kill: 0 → 1` |
| 同时段 `/proc/meminfo` | `MemAvailable: 1045120 kB` |

这些教学值与 `CONSTRAINT_MEMCG` 日志、cgroup v2 计数变化相符：容器/服务受到记账限额约束，而主机全局可用内存仍较多。单次 `memory.current` 接近限额本身不足以定性；本例的因果线索来自同一时段的内核日志和事件计数增量。

## 假设与区分检查

1. **服务 cgroup 限额过低或负载突增**：确认运行中的层级、服务和父 cgroup 的 `memory.max`、`memory.high`、`memory.current`、`memory.events`，并将事件增量与负载及 OOM 时间对齐。
2. **服务内存在持续增长**：在相同请求速率下连续记录 `memory.current` 与 `memory.stat` 的匿名内存、文件缓存等类别；需要对象/堆归属证据后才能称为泄漏。
3. **全局 OOM 或受约束分配失败**：检查完整内核事件中的约束类型、目标 zone/order/GFP/DMA 要求，并对照同一时段的系统级内存和回收证据。主机空闲内存较多支持排查 memcg，但不能单独排除其他限制。
4. **路径或归属误读**：用 mountinfo 的 cgroup2 挂载根和挂载点映射进程 cgroup 路径；检查适用的祖先层级。不能把宿主机同名路径或另一个容器的计数器当作进程所属 cgroup。

## 下一步证据

- 保存包含 OOM 前后行的完整内核日志和运行内核版本。
- 在故障复现期间多次读取进程 `cgroup`、对应 mountinfo、每级 `memory.current` / `memory.max` / `memory.events`，记录采样时间。
- 检查 `memory.stat` 分类与应用负载、缓存上限和工作集大小；如限制在父级，继续检查子级记账和兄弟服务用量。
- 采集器只保存进程 cgroup 与 mountinfo 作为跟进依据，不会自动解析挂载或读取整棵 cgroup 树。必要时在目标上使用只读命令定位正确目录，并核实服务所属层级。

## 最小修复边界与回归

先依据产品内存预算和同负载峰值判断是配置预算不足，还是服务自己的占用无界。如果确认限制设置偏低，只调整该服务或经过证据确认的父层级预算；如果确认应用持续增长，修复对应分配/缓存所有者并保留合理上限。不要仅因一次 OOM 就全局放宽内存策略、关闭 OOM 处理或增加 swap。

回归应使用与故障一致的请求速率、数据规模和持续时间，记录 cgroup 事件计数、内存类别和服务响应。验收要求是复现窗口内不再增加目标层级的 `oom` / `oom_kill` 计数，内存使用符合产品预算，且系统内其他服务仍有预期资源余量。只有合成数据时，回归结论仅适用于夹具；目标板和实际负载验证仍未完成。

## 边界

该例演示怎样根据证据提出可证伪假设，不表示任何特定板卡、产品、内核版本或服务实际发生过 memcg OOM。没有故障时间点前后的计数器或可复现负载时，不应据此宣布根因或修复已验证。

## 依据与验证范围

计数器和层级语义依据 [Linux cgroup v2 memory controller 文档](https://docs.kernel.org/admin-guide/cgroup-v2.html)；进程 `status` 与 cgroup 文件范围可参考 [proc 文件系统文档](https://docs.kernel.org/filesystems/proc.html)。案例中的路径和数字均为手工构造夹具，没有执行目标采样、目标构建或板测。主机上的工具测试只验证采集器对离线夹具的行为。
