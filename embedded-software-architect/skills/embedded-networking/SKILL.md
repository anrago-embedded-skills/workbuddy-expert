---
name: embedded-networking
description: |
  用于诊断嵌入式 Linux socket/TCP/UDP 传输、连接与队列、丢包、重连，以及网络相关文件描述符压力。
---

# embedded-networking

> 嵌入式 Linux 网络应用的**网络负载、socket 缓冲区、fd 泄漏、长连接卡顿**排查方法论。平台无关。

## 主用与配合

本技能主用于 socket 和 TCP/UDP 传输、连接状态、收发队列、丢包、重连及网络 socket 相关 fd 生命周期。MQTT 等应用协议的主题、消息和语义问题配合 [protocols-embedded](../protocols-embedded/SKILL.md)；Wi-Fi 关联、射频、信号或固件问题配合 [wireless-connectivity](../wireless-connectivity/SKILL.md)。根因或责任层尚不明确时，配合 [embedded-debug-workflow](../embedded-debug-workflow/SKILL.md)。

需要一次性网络现场命令、队列字段或 fd/连接状态速查时，按需读取 [network-cheatsheet.md](references/network-cheatsheet.md)。

## 任务输入、证据分支与交付

先记录目标设备/内核版本、接口和网络命名空间、进程/服务版本、对端与端口、TCP/UDP 及上层协议、故障时间线、负载和原始错误（errno、退出码或协议状态）。缺项时把它列为未知，不从主机环境或接口名猜目标配置。

| 证据 | 主查层与下一项区分证据 |
|---|---|
| Wi-Fi 关联或漫游事件与业务中断同时发生 | 转 [wireless-connectivity](../wireless-connectivity/SKILL.md) 对齐无线事件与时间；若应用协议同时报错，再查协议层 |
| 已建 TCP socket 的重传、持续 Send-Q 或 Recv-Q 变化 | 采集多次 `ss -tinm`、进程归属和同窗抓包/应用耗时；区分本地不读、对端不确认与链路问题 |
| TCP 连通但 MQTT/TLS 返回错误、订阅或消息行为不符 | 转 [protocols-embedded](../protocols-embedded/SKILL.md) 检查协议状态、证书验证和 broker 日志 |
| `recv()` 读到少于帧长度、消息合并或分片 | 检查应用帧解析与部分 I/O 循环；TCP 是字节流，不以一次 `send()`/`recv()` 作为消息边界 |
| fd、`CLOSE_WAIT` 或连接数随负载积累 | 多时点关联 PID、fd 链接、socket 状态与清理路径；单个快照不判泄漏 |

交付时间线、责任层及其区分证据、最小修复范围、回归负载和接受标准。断连恢复至少覆盖连续断连与恢复周期：业务恢复、连接/协议状态正确重建、退避不复位成紧密重试、fd/队列在空闲后回到基线范围。若目标上未执行，分别标出资料核对、主机测试和目标验证状态。跨领域公共流程见 [工程工作流](../embedded-debug-workflow/references/engineering-workflow.md)；声明验证层级时见 [验证策略](../embedded-debug-workflow/references/validation-policy.md)。

## 命令环境

本页诊断命令默认运行在 **TARGET Linux**，不是开发主机；以目标上可用的 `ss`、`iproute2`、`procfs`、`timeout` 和权限为前提。`<pid>`、`<port>`、`<interface>`、`<peer>` 是必须替换的模板字段。`ss`、`ip -s link`、`cat /proc` 是状态快照；抓包会写捕获文件且通常需要权限，`strace -p` 会附加到进程并可能改变时序。先记录现场再做变更。

## 适用范围

- 网络负载与带宽分析
- socket 收发缓冲区（SO_RCVBUF / SO_SNDBUF）调优
- **fd（文件描述符）泄漏**
- TCP 粘包/拆包
- 长连接掉线与重连
- 网络卡顿、延迟抖动、丢包定位

---

## 核心原则

1. **先测量再调参** — 网络问题必须看实际指标，不要凭感觉调缓冲区
2. **区分「发送阻塞」「接收处理慢」「网络丢包」** — 三者现象相似但根因不同
3. **计数器只是线索** — fd 增长、队列深度和接口丢包需结合进程、socket 和时间相关的证据判断。
4. **卡顿要区分内核网络栈 vs 应用处理** — 分层定位

---

## 网络负载分析

### 基础命令

```bash
# TARGET / read-only snapshot. Replace IFACE with an interface shown by `ip link`.
IFACE=eth0
# 连接状态统计（关键：看 TIME_WAIT / CLOSE_WAIT 堆积）
ss -s
ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn

# 按状态看连接
ss -tan state time-wait | wc -l
ss -tan state close-wait | wc -l      # 对端 FIN 已到；本端尚未 close 这些 sockets

# 端口占用排行
ss -tan | awk '{print $4}' | cut -d: -f2 | sort | uniq -c | sort -rn | head

# 网卡状态与流量
ip -s link show dev "$IFACE"
ip addr show dev "$IFACE"

# 连接统计快照（多次采样看趋势）
ss -s
```

预期得到 TCP 状态计数和接口累计计数。命令非零、接口不存在或 `/proc` 不可读表示该目标的工具、名称、权限或内核接口不满足前提；接口计数须用两个时间点的增量解释，不能由单次非零值判定链路故障。

### 关键指标解读

| 指标 | 可见现象 | 需要进一步确认 |
|---|---|---|
| **TIME_WAIT** | 短连接或本端主动关闭连接时可能正常累积 | 检查连接创建/关闭速率、四元组复用和实际端口压力；单独的数量不能说明异常。 |
| **CLOSE_WAIT** | 对端 FIN 已到达，本地端尚未关闭 socket | 查明所属进程和 socket 存续时间。持续积累可能表示清理延迟，但单独不能证明泄漏。 |
| **SYN_RECV** | 握手或连接请求尚未完成 | 结合速率、监听 backlog、重传和抓包，再判断是否为过载或攻击。 |
| **Recv-Q / Send-Q** | 含义取决于 socket 状态和角色 | 对已建立 socket，Recv-Q 是等待本地应用读取的数据，Send-Q 是尚未确认的数据；对监听 socket，这两个值表示 accept 队列占用量和 backlog 上限。一次快照无法说明队列为何增长。 |
| **接口 drop/error 计数器** | 网卡设备的汇总计数 | 比较一段时间内的变化，并检查驱动、队列、协议和对端证据；计数器本身不能确定硬件或链路根因。 |

读取队列值时要同时查看 socket 状态、进程归属和多次采样。通过抓包或应用处理耗时，区分消费慢、网络拥塞和对端行为。

---

## socket 缓冲区

### 查看与设置

```bash
# TARGET / read-only snapshot
# 查看当前连接缓冲区
ss -tnm | head -20

# 系统默认值
cat /proc/sys/net/core/rmem_default
cat /proc/sys/net/core/wmem_default
cat /proc/sys/net/core/rmem_max
cat /proc/sys/net/core/wmem_max

# TCP 相关
cat /proc/sys/net/ipv4/tcp_rmem
cat /proc/sys/net/ipv4/tcp_wmem
```

预期读取到当前目标的默认值、上限和 TCP 自动调优范围；路径缺失可能表示内核未启用该项或该版本采用不同接口，不能据此套用主机值。

### 可选运行时调参（状态变更）

只有观测到缓冲限制是瓶颈，且已确认目标内核参数及其命名空间/系统范围后，才评估如下 **TARGET 模板**。先保存原值并安排同负载对照；写入参数会立即改变运行内核设置，数值是占位示例，不是通用推荐值。

```bash
# TARGET / state-changing template; replace values from measured requirements.
: "${MEASURED_BYTE_LIMIT:?set from measured requirement and target limit}"
sysctl -w "net.core.rmem_max=$MEASURED_BYTE_LIMIT"
```

成功输出应回显已应用值；权限拒绝、参数不存在或值被拒绝说明该目标不支持该操作或调用权限不足。随后以 `sysctl net.core.rmem_max` 验证实际值；不能只因写入命令退出码为零就断言 socket 使用了该容量。TCP 自动调优、缓冲内存和 `getsockopt()` 结果也需复查。

在 Linux 上，`net.core.rmem_max` 和 `wmem_max` 会限制普通的单 socket `SO_RCVBUF` / `SO_SNDBUF` 请求；TCP 自动调优还会使用 `tcp_rmem` / `tcp_wmem` 范围。调优前先检查运行内核的配置值和 socket 的实际生效值。

### 程序侧设置

```c
// C API fragment / per-socket state change. Use a measured value and check every return.
int rcvbuf = measured_rcvbuf;
if (setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &rcvbuf, sizeof(rcvbuf)) < 0) { /* inspect errno */ }
int effective = 0;
socklen_t effective_len = sizeof(effective);
if (getsockopt(fd, SOL_SOCKET, SO_RCVBUF, &effective, &effective_len) < 0) { /* inspect errno */ }

// Optional per-socket state change; measure latency/packet-rate before enabling.
int flag = 1;
if (setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag)) < 0) { /* inspect errno */ }
```

**关键点**：
- Linux 会为内核记账将 `SO_RCVBUF` / `SO_SNDBUF` 的设置值翻倍；检查 `getsockopt()` 返回值，并按目标内核确认实际行为。
- `TCP_NODELAY` disables Nagle for that socket; it may lower some small-write latency while increasing packet overhead. Measure before enabling.
- 缓冲区不是越大越好——太大掩盖消费慢的问题，且占内存

---

## TCP 粘包/拆包

### 为什么会发生

TCP 是**字节流**协议，没有消息边界。一次 `send` 的数据可能被拆成多次 `recv`，也可能多次 `send` 被一次 `recv` 读走。

### 解决方案（按场景选）

| 方案 | 适用场景 |
|---|---|
| **固定长度** | 数据结构固定大小，最简单高效 |
| **分隔符** | 文本协议（如 `\n`），注意分隔符本身可能出现在内容中需转义 |
| **长度前缀** | **二进制协议推荐**——前 4 字节存后续长度 |
| **TLV** | 字段类型可变 |

```c
// C fragment, not a complete function. Validate endianness and max_len before allocation.
// recv may return a short read; helper preserves partial progress across EAGAIN.
uint32_t len;
if (recv_full(fd, &len, sizeof(len)) != READ_COMPLETE) goto reset_connection;
len = ntohl(len);
if (len > max_len) goto protocol_error;
uint8_t* buf = malloc(len);
if (buf == NULL) goto allocation_error;
if (recv_full(fd, buf, len) != READ_COMPLETE) goto reset_connection;  // discard partial frame
free(buf);
```

**铁律**：每次 `recv` 都要检查返回值；EOF 表示对端有序关闭，`EINTR` 可重试，非阻塞 socket 的 `EAGAIN` 表示目前没有数据，其他错误需结合连接状态处理。检查帧长度上限、字节序、部分帧跨超时保留方式，以及连接关闭时是否释放未完成帧。预期输出应是完整且顺序正确的协议帧；短读本身不是 TCP 故障。

---

## fd 泄漏

### 判断是否泄漏

```bash
# TARGET / read-only process snapshot; supply the intended target PID.
: "${PID:?set PID to the intended target process}"
# 当前打开的 fd 数
ls "/proc/$PID/fd" | wc -l

# 系统 fd 上限
cat "/proc/$PID/limits" | grep -i "open files"

# 20 samples at 60-second intervals (20 minutes total), if sleep/procfs are available.
i=1
while [ "$i" -le 20 ]; do
  echo "$(date) fd=$(ls "/proc/$PID/fd" 2>/dev/null | wc -l)"
  sleep 60
  i=$((i + 1))
done
```

预期获得 PID 的 fd 数、软/硬 `open files` 限额及采样趋势；`No such file` 表示进程已退出或 PID 错误，权限拒绝表示采样范围不足。只针对同一 PID、同类负载和采样间隔比较。

多次采样发现 fd 增长可作为泄漏候选线索，但不能据此定论。结合负载、socket 状态和 `/proc/<pid>/fd` 链接，查明累积的是哪类描述符，以及清理是否延迟或有意复用。一次稳定快照也不能排除间歇性增长或尚未达到观测上限的泄漏。

### fd 泄漏的常见来源

| 来源 | 特征 |
|---|---|
| **socket 清理问题** | 持续存在的 `CLOSE_WAIT`，并伴随对应进程的 fd 增长；还需确认 socket 存续时间和应用生命周期 |
| **文件未关闭** | `/proc/<pid>/fd` 里出现大量 `*.tmp`、`deleted` |
| **fd 被子进程继承** | fork 后子进程不关继承的 fd |
| **fd 上限触顶** | `EMFILE` 报错，新连接/文件全部打不开 |

### fd 上限触顶的排查

```bash
# TARGET / read-only; supply the intended target PID.
: "${PID:?set PID to the intended target process}"
cat "/proc/$PID/limits" | grep -i "open files"

# 查看各类型 fd 分布
ls -l "/proc/$PID/fd" | awk '{print $NF}' | sed 's/[0-9]*$//' | sort | uniq -c
```

出现 `EMFILE` 时，将进程限额与当前描述符清单对比。只有测得容量需求支持时才提高限额；先确认描述符是否在非预期地累积。

---

## 长连接卡顿与重连

### 掉线排查

```bash
# TCP keepalive 参数
# TARGET / read-only; values vary by kernel and runtime configuration.
cat /proc/sys/net/ipv4/tcp_keepalive_time
cat /proc/sys/net/ipv4/tcp_keepalive_intvl
cat /proc/sys/net/ipv4/tcp_keepalive_probes

# Keepalive settings are read-only here. Choose TCP or application heartbeat based on which failure they detect.
#   - 许多 Linux 配置会在较长空闲时间后才开始 TCP keepalive 探测；检查目标系统实际值，不要假定默认值。
#   - 应用层心跳可自定义超时，快速发现断线
```

预期是目标实际配置的秒数和探测次数；路径缺失时需按目标内核/网络命名空间确认。TCP keepalive 只探测空闲 TCP 对端，不等于业务健康检查。

### 心跳设计要点

```c
// C pseudocode: choose a deadline from the protocol/product requirement.
while (running) {
    ret = recv_with_timeout(fd, buf, sizeof(buf), read_interval);
    if (ret > 0) { idle_count = 0; }
    else if (ret == 0) {
        close(fd);                        // 对端正常关闭，收到 EOF
        reconnect();
    }
    else if (ret < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) {
        if (failure_deadline_expired()) { // use the helper's timeout/deadline contract
            close(fd);
            reconnect();
            idle_count = 0;
        }
    }
    else if (ret < 0 && errno == EINTR) {
        continue;
    }
    else {
        close(fd);
        reconnect();
    }
}
```

此伪代码假设 `recv_with_timeout()` 超时返回 `-1` 并设置 `EAGAIN` 或 `EWOULDBLOCK`。实际辅助函数需区分超时、EOF 和其他错误：`recv()` 返回 0 表示对端正常关闭；`EAGAIN`/`EWOULDBLOCK` 表示非阻塞读取或截止时间已到时仍没有数据。`failure_deadline_expired()` 仅代表应用策略判断，不是 Linux API。

**要点**：单次 `recv` 超时不等于断线；按应用截止时间、心跳响应和 socket 错误组合判定，避免无依据的固定“连续 N 次”规则。

### 重连策略

- 用有界退避并加入抖动；最大间隔、失败复位条件和协议恢复步骤由服务容量/产品时限决定
- 避免没有退避的快速循环，并为同时重连的设备分散请求时点
- **重连后要重建完整状态**（订阅关系、序列号对齐），不只是重开 socket

---

## 卡顿定位：分层排查

```text
Recv-Q 持续增长 → 检查本地应用读取速度；监听 socket 则检查 accept 速度
Send-Q 持续增长 → 检查 ACK、重传、路由和抓包证据
接口计数变化   → 检查驱动、队列并对比同一时间段的增量
```

```bash
# 1. 看队列堆积
ss -tn | awk '{print $1, $2}' | head -20
ss -tnm

# 2. 看网卡丢包
: "${IFACE:?set IFACE to the interface shown by ip link}"
ip -s link show dev "$IFACE"

# 3. TARGET / writes a bounded capture file; replace IFACE and PORT first.
: "${PORT:?set PORT to the target service port being investigated}"
CAPTURE="$(mktemp /tmp/net-cap.XXXXXX.pcap)" || exit 1
timeout 30s tcpdump -i "$IFACE" -nn -c 1000 "port $PORT" -w "$CAPTURE"

# 4. TARGET / attaches tracing to the process; may affect timing and needs permission.
: "${PID:?set PID to the intended target process}"
timeout 10s strace -p "$PID" -c -f -e trace=network
```

预期抓包输出有限于 1000 包或 30 秒，路径由 `CAPTURE` 保存；无匹配数据、权限错误或空文件可能表示接口、capture capability、过滤器或目标流量有误。`strace` 超时表示观察窗口结束，不是目标进程出错；若不可附加，改用既有应用日志或非侵入式采样。

**关键**：区分「网络慢」和「应用处理慢」——两者都表现为卡顿，但修法不同。详细的断连、退避、恢复状态和部分读写教学流程见 [网络断连与恢复案例](references/connection-recovery-case.md)。

---

## 内核网络参数（嵌入式调优）

```bash
# TCP 拥塞控制可用选项
cat /proc/sys/net/ipv4/tcp_available_congestion_control

# 队列长度
cat /proc/sys/net/core/netdev_max_backlog

# 查看 TIME_WAIT 复用设置；行为和默认值因内核版本而异。
cat /proc/sys/net/ipv4/tcp_tw_reuse

# 连接队列
cat /proc/sys/net/core/somaxconn

# TIME_WAIT 数量
cat /proc/sys/net/ipv4/tcp_max_tw_buckets
```

**注意**：这些参数影响范围取决于目标内核，可能作用于网络命名空间或整个系统。记录当前值，查阅对应内核文档；只有证据支持时才做有针对性的修改。`tcp_tw_reuse` 的默认值和可选值因内核版本而异，不能作为短连接问题的通用修复。

---

## 长跑网络验证

```bash
# TARGET / bounded only by the operator; creates a new sample log in /tmp.
: "${PID:?set PID to the intended target process}"
: "${IFACE:?set IFACE to the target interface}"
LOG="$(mktemp /tmp/net-longrun.XXXXXX.log)" || exit 1
while true; do
  echo "$(date) \
    fd=$(ls "/proc/$PID/fd" 2>/dev/null | wc -l) \
    tw=$(ss -tan state time-wait 2>/dev/null | wc -l) \
    cw=$(ss -tan state close-wait 2>/dev/null | wc -l) \
    rx_drop=$(ip -s link show dev "$IFACE" | awk '/^[[:space:]]*RX:/{getline; print $4}')"
  sleep 300
done | tee "$LOG"
```

此循环每 5 分钟写一行到新建的 `$LOG`，按 Ctrl-C 结束。预期 fd/socket/接口计数可跨采样比较；如果工具/权限不可用，会缺字段，不能把空字段解释为零。旧版 `ip` 输出格式不匹配时改为保留完整 `ip -s link` 样本，不依赖 awk 字段位置。

**重点观察 fd 与 CLOSE_WAIT 的变化**——它们可以帮助发现需要进一步调查的候选问题。

这些计数器用于发现候选问题。将其称为泄漏前，应确认描述符归属和生命周期。按 Ctrl-C 停止持续采样，并记录采样时长。

---

## 边界与注意

- **缓冲区调优前先看 Recv-Q/Send-Q**，不要盲目加大缓冲区掩盖消费慢的问题
- **CLOSE_WAIT** 表示本地已收到对端 FIN，但尚未关闭 socket；检查所属进程和 socket 存续时间
- 队列深度、fd 增长和接口计数器需要结合其他证据，不能单独作为诊断结论
- 仅在测得容量需求时调整文件描述符限额，并确认 fd 增长是否属于非预期行为
- **粘包靠长度前缀或分隔符解决**，不要假设一次 recv 就是完整数据
- 心跳误判会导致频繁重连，反而加重负载
- 内核参数的作用范围依目标内核而定；变更前记录当前值，并在升级时确认配置仍适用
- 实测数据用具体数字（延迟 ms、丢包率、fd 数），不用「网络有点慢」

## 参考资料

- [Linux socket buffer options (`socket(7)`)](https://man7.org/linux/man-pages/man7/socket.7.html)
- [Linux TCP behavior and buffer tuning (`tcp(7)`)](https://man7.org/linux/man-pages/man7/tcp.7.html)
- [Linux kernel IP sysctls, including `tcp_tw_reuse`](https://docs.kernel.org/networking/ip-sysctl.html)
- [Linux `ss(8)` socket state and queue fields](https://man7.org/linux/man-pages/man8/ss.8.html)
- [Linux `recv(2)` short reads and EOF](https://man7.org/linux/man-pages/man2/recv.2.html)
- [Linux `tcp(7)` byte-stream behavior](https://man7.org/linux/man-pages/man7/tcp.7.html)
