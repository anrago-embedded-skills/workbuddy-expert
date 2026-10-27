# 网络断连、恢复与部分 I/O：教学案例

> **合成教学输入**：以下症状、日志和分支是测试夹具，不是某块板的历史，也不包含实测吞吐或恢复时间。用来组织下一步证据，不代表任何特定根因已经发生。

## 输入与目标

一台嵌入式 Linux 客户端在链路中断后报告消息缺失。夹具记录按阶段排序：

1. 应用已建立 TCP 连接，正在读取长度前缀帧；一次 `recv()` 返回少于本次请求的字节数。
2. 无线/有线接口或路由发生中断，应用继续在旧 socket 上读写并立即重试。
3. 接口恢复后新 TCP 连接可以建立，但业务未恢复；测试日志缺少应用重组缓冲区、连接代次和协议会话状态。

待补输入：目标内核/网络管理器、接口和对端身份、使用的上层协议/版本、errno/协议响应、断连与恢复时间线、socket 所属 PID、可复现负载，以及旧连接/会话如何作废和重建。未取得这些字段时保持各分支为候选，不先改 sysctl、Wi-Fi 功率或服务配置。

## 候选原因与区分证据

| 候选 | 区分证据 | 下一步 |
|---|---|---|
| 无线关联/漫游丢失 | 目标侧 `iw ... link`/事件与 AP 侧断开记录同窗变化 | 核对关联、安全模式、频段/重试及恢复时间；无无线事件时不把 TCP 错误归因于 RF |
| 路由、地址或 DNS 变化 | `ip addr`, `ip route`, resolver 记录与失败时点对齐 | 用目标配置的网关和已知 peer 测试；DNS 问题仅影响名称解析，不能解释已有 socket 的帧分片 |
| TCP 连接失效/重传 | 多次 `ss -tinm`、errno、限定窗口的包迹显示 FIN/RST、重传或未确认数据 | 先建立新的 socket 代次；不要把一次超时或单次队列值当作根因 |
| 应用未正确保留部分帧 | 同一连接的字节流在任意位置拆分后，parser 丢弃未满 header/payload 的缓冲 | 检查帧长度、字节序、上限、EINTR/EAGAIN/EOF 分支和断连时缓冲清理；实现细节见 [socket-implementation.md](socket-implementation.md) |
| 应用协议会话没有恢复 | TCP 已连通但 MQTT 等未收到预期握手/订阅确认或会话状态不符 | 与 [protocols-embedded](../../protocols-embedded/SKILL.md) 对齐 CONNACK/SUBACK、session 和幂等行为 |

`recv()` 可以返回少于请求长度；`0` 表示有序关闭，`EINTR`、`EAGAIN`/`EWOULDBLOCK` 和其他 errno 分别处理。参考 [Linux `recv(2)`](https://man7.org/linux/man-pages/man2/recv.2.html) 与 [TCP `tcp(7)`](https://man7.org/linux/man-pages/man7/tcp.7.html)。

## 活跃检测与重连

TCP keepalive 用于探测空闲 TCP 对端，不证明对端应用或业务健康；按目标内核读取 keepalive 时间、间隔、探测次数和 socket 是否启用，不能假定默认值。需要核对参数时见 [kernel-network-tuning.md](kernel-network-tuning.md)。应用层心跳只有在协议定义了有效响应时才可代表相应业务状态。

| 接收结果 | 处理边界 |
|---|---|
| 正数 | 消费已读字节并保留未完成帧状态；不要假设读满请求长度 |
| `0` | 对端有序关闭；使当前连接代次失效并清理其未完成帧 |
| `EINTR` | 按调用契约重试，不当作断线 |
| `EAGAIN` / `EWOULDBLOCK` | 非阻塞读取暂时无数据或读取截止时间到；用产品/协议的绝对失败期限和心跳响应判断，单次超时不等于断线 |
| 其他错误 | 记录原始 errno，按连接状态关闭旧 socket，并建立新的连接代次 |

重试使用有上限的退避并加入抖动，失败期间不回到紧密循环；成功后按定义复位重试状态，再重建订阅、序列号或其他协议会话状态。阈值由服务容量和产品恢复时限决定，本例不规定统一数字。

## 最小变更边界

只修复证据支持的层。若证实是部分 I/O，修正 parser 的缓冲和状态机，限制长度字段，并把未完成帧与连接代次关联；不要一次性扩大 socket 缓冲区。若证实断连恢复路径，关闭已失效 socket、建立新连接、采用受限且带抖动的退避，并按应用协议重新建立订阅/序列状态。具体退避间隔由服务端容量和产品恢复要求决定；本例不规定统一数字。只有参数证据支持时才考虑网络 sysctl，按 [kernel-network-tuning.md](kernel-network-tuning.md) 保存原值并把目标内核版本写进记录。

## 验收与验证边界

在 HOST Linux stream fixture 或网络命名空间中，把 header 和 payload 分别切分在每个字节边界，插入 EOF、EINTR、EAGAIN 及连接重置；然后重复断开/恢复周期。验收要求：

- parser 只产出完整、校验通过且顺序正确的帧；断连时未完成帧不会被误当成成功消息。
- 旧 socket 关闭且新连接/协议会话按设计恢复；失败重试不形成紧密循环，成功后重试状态按定义清零。
- fd、队列和未确认业务请求在多轮后回到设定基线范围，重复/丢失符合应用幂等和确认语义。
- 记录确切 fixture、目标配置和测试层级。主机模拟不能证明无线驱动、真实 AP 漫游、目标内核或物理链路行为；这些需单独的目标验证。

## 命令前提

文中的 `iw`, `ip`, `ss`, `tcpdump` 和 `strace` 是 TARGET 工具示例；IFACE 必须来自目标 `ip link` 或操作人员确认，PID 必须是目标进程列表中的数字值，端口应来自已知服务配置。`iw scan` 会请求射频扫描；捕获窗口及 snaplen 上限见 [network-observation.md](network-observation.md)；`strace -p` 会附加进程并改变时序，最多观察 10 秒。缺少工具/权限或空捕获应解释为观测条件不足，不是网络正常。队列字段见 [network-cheatsheet.md](network-cheatsheet.md)，通用接口/路由/进程采样见 [network-observation.md](network-observation.md)。
