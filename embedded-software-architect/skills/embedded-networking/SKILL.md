---
name: embedded-networking
description: |
  用于诊断嵌入式 Linux socket/TCP/UDP 传输、连接与队列、丢包、重连，以及网络相关文件描述符压力。
---

# embedded-networking

> 诊断嵌入式 Linux 网络传输、socket 生命周期和链路问题。先按证据选层，再决定是否需要命令或实现细节。

## 主辅边界

本技能主查 TCP/UDP 传输、socket 状态与队列、重传、网络 socket fd 生命周期和断连恢复。MQTT、TLS 等协议状态、消息和证书语义配合 [protocols-embedded](../protocols-embedded/SKILL.md)；Wi-Fi 关联、漫游、射频、信号或固件问题配合 [wireless-connectivity](../wireless-connectivity/SKILL.md)。故障层尚不明确时先用 [embedded-debug-workflow](../embedded-debug-workflow/SKILL.md) 建立现场证据。

## 证据与决策

先记录目标设备和内核版本、网络命名空间、已确认的接口、相关服务版本、对端/端口、传输与上层协议、负载、故障时间线及原始 errno/退出码/协议状态。进程相关问题记录目标上的**数字 PID**。无法确认的字段标成未知，不用开发主机的接口、路由、`/proc` 或内核值填补。

| 证据 | 先查什么 | 条件分流 |
|---|---|---|
| 已建立 TCP socket 的 Send-Q、Recv-Q 或重传在多个时点变化 | 同一连接角色、进程归属、多个 `ss` 样本、应用耗时和对端/抓包证据 | 精确命令与队列字段见 [network-cheatsheet.md](references/network-cheatsheet.md) |
| 接口错误/drop 累计值变化，或路由、地址、DNS、端口可达性不明 | 比较同一时间窗的接口计数增量，逐层验证目标路由、解析和 TCP 建连 | 需要接口、路由或探测命令时见 [network-observation.md](references/network-observation.md)；无线链路证据转无线技能 |
| fd、`CLOSE_WAIT` 或连接数随负载累积 | 多时点关联数字 PID、fd 链接、socket 状态和关闭路径 | 一次快照不能判泄漏；需要 fd 命令时见 [network-observation.md](references/network-observation.md) |
| TCP 读到短帧、消息合并/拆分，或准备更改 socket 选项 | 检查字节流解析、部分 I/O、长度上限、缓冲区生效值和每条错误路径 | 仅在代码/选项问题触发时读 [socket-implementation.md](references/socket-implementation.md) |
| 链路恢复后业务未恢复、快速重试、消息重复或丢失 | 检查旧 socket 退出、新连接代次、退避及协议会话重建 | 需要恢复步骤时读 [connection-recovery-case.md](references/connection-recovery-case.md)；协议语义转协议技能 |
| 证据指向内核网络参数可能是瓶颈 | 先记录目标内核版本、命名空间、原值及测得负载 | 仅在评估 sysctl 时读 [kernel-network-tuning.md](references/kernel-network-tuning.md) |

## 解读与操作约束

- 对**已建立** socket，Recv-Q 是等待本地应用读取的数据，Send-Q 是尚未确认的数据；对监听 socket，两列表示 accept 队列占用量和 backlog 上限。Send-Q 单独不能区分本地拥塞、对端未确认或链路问题。
- 队列、重传、fd、`CLOSE_WAIT` 与接口 drop/error 都是线索。用多个可比较时点、进程/对端行为和同窗应用证据解释；接口计数按增量解释，不能凭单次非零值归因。
- 调缓冲区或 sysctl 前先证明容量限制是瓶颈并保存原值；增大缓冲不能修复应用消费慢或错误的帧处理。参数作用范围与默认值依目标内核和命名空间而异。
- TCP 是字节流；一次 `send()`/`recv()` 不代表一帧。短读不是网络故障。TCP 建连成功也不代表 MQTT/TLS 业务可用；Wi-Fi 已关联也不代表端到端服务可达。
- `tcpdump -w` 会创建含实时流量的捕获文件；[观测参考](references/network-observation.md)限制在 30 秒、1000 包和 96 字节 snaplen。`strace -p` 会附加到目标进程并可能改变时序，参考窗口最多 10 秒。先采集只读证据，再做有影响的操作。
- 用实测数字表达症状和验收，例如延迟毫秒、丢包增量、队列字节数和 fd 数，不用“网络有点慢”代替证据。

## 交付

说明责任层、支持和反对该判断的证据、最小修复范围、复现负载和验收标准。断连恢复验收覆盖重复断连/恢复周期，并检查业务及协议状态、退避行为和空闲后 fd/队列是否回到设定基线。分别标记资料核对、主机测试和目标验证；没有目标执行记录时不能称为板上通过。跨领域流程和验证层级见 [engineering-workflow.md](../embedded-debug-workflow/references/engineering-workflow.md) 与 [validation-policy.md](../embedded-debug-workflow/references/validation-policy.md)。
