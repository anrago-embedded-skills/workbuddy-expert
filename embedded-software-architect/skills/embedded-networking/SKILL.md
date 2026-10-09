---
name: embedded-networking
description: |
  Embedded networking: network load analysis, socket buffers, fd leak, TCP sticky-packet, long-connection stalls and reconnect.
  TRIGGER when: 网络、socket、TCP、UDP、粘包、拆包、fd 泄漏、文件描述符、句柄泄漏、连接数、收发缓冲、SO_RCVBUF、SO_SNDBUF、TCP_NODELAY、TIME_WAIT、CLOSE_WAIT、Recv-Q、Send-Q、重连、心跳、KeepAlive、断线、掉线、网络卡顿、延迟抖动、丢包、带宽、ss -tan、ip -s link、网络负载、长连接、连不上、连不上服务器、时断时续、断了又连、掉线、老是掉线、网络不稳、网速慢、延迟高、卡在连接、连着连着就断了、socket 断了、发不出去、收不到数据、包丢了、端口占用、socket卡、fd泄漏、句柄泄漏、socket 泄漏、fd 数量涨、句柄不够、socket 占用、连接数爆了、文件描述符耗尽、accept 失败、send 阻塞、recv 阻塞,
  DO NOT TRIGGER when: 应用无响应但确认是内存问题（用 embedded-perf-debug）；WiFi/蓝牙硬件连接问题（用 wireless-connectivity）,
---

# embedded-networking

> 嵌入式 Linux 网络应用的**网络负载、socket 缓冲区、fd 泄漏、长连接卡顿**排查方法论。平台无关。

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
3. **fd 泄漏是渐进的** — 短时间测试看不出来，必须长跑采样
4. **卡顿要区分内核网络栈 vs 应用处理** — 分层定位

---

## 网络负载分析

### 基础命令

```bash
# 连接状态统计（关键：看 TIME_WAIT / CLOSE_WAIT 堆积）
ss -s
ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn

# 按状态看连接
ss -tan state time-wait | wc -l
ss -tan state close-wait | wc -l      # CLOSE_WAIT 多 = 对端没收到 FIN，通常是本端没 close

# 端口占用排行
ss -tan | awk '{print $4}' | cut -d: -f2 | sort | uniq -c | sort -rn | head

# 网卡状态与流量
ip -s link show eth0
ip addr show eth0

# 丢包与错误
ip -s link show eth0 | grep -iE "drop|error|miss"

# 连接统计快照（多次采样看趋势）
ss -s
```

### 关键指标解读

| 指标 | 正常 | 异常含义 |
|---|---|---|
| **TIME_WAIT** 堆积 | 少量 | 短连接过多，服务端没复用连接 |
| **CLOSE_WAIT** 堆积 | 接近 0 | **本端没调 close()** — 常见泄漏点 |
| **SYN_RECV** 堆积 | 少量 | SYN flood 或 accept 队列打满 |
| **Recv-Q/Send-Q** 高 | 接近 0 | 对端不消费（应用处理慢）或缓冲区太小 |
| **网卡 drop/error** | 0 | 队列溢出、硬件或链路问题 |

**核心判据**：Recv-Q 持续堆积 = **本端消费慢**（应用侧问题）；Send-Q 堆积 = **对端接收慢或网络拥塞**。

---

## socket 缓冲区

### 查看与设置

```bash
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

# 临时调整（嵌入式慎用，会影响全局）
sysctl -w net.core.rmem_max=8388608
sysctl -w net.ipv4.tcp_rmem="4096 87380 8388608"
```

**重要**：`rmem_max` 是**单 socket 上限**，设太大也不会超限生效。

### 程序侧设置

```c
// 必须 SO_RCVBUF / SO_SNDBUF 都设
int rcvbuf = 4 * 1024 * 1024;
setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &rcvbuf, sizeof(rcvbuf));
setsockopt(fd, SOL_SOCKET, SO_SNDBUF, &sndbuf, sizeof(sndbuf));

// 禁Nagle：实时性场景（注意：会牺牲带宽效率）
int flag = 1;
setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag));
```

**关键点**：
- `setsockopt(SO_RCVBUF)` 实际生效值是内核 **2 倍**（内核会翻倍分配）
- `TCP_NODELAY` 解决小包延迟，代价是**包头开销增加**，批量传输场景不要开
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
// 长度前缀 + 完整读取循环（关键：recv 可能返回部分数据）
uint32_t len;
recv_full(fd, &len, sizeof(len));          // 循环读满 4 字节
uint8_t* buf = malloc(len);
recv_full(fd, buf, len);                    // 循环读满 len 字节
free(buf);
```

**铁律**：**每次 `recv` 都要检查返回值**，一次 `recv` 不保证拿到全部数据。

---

## fd 泄漏

### 判断是否泄漏

```bash
# 当前打开的 fd 数
ls /proc/<pid>/fd | wc -l

# 系统 fd 上限
cat /proc/<pid>/limits | grep -i "open files"

# 采样看增长趋势（核心判定方法）
for i in $(seq 1 20); do
  echo "$(date) fd=$(ls /proc/<pid>/fd 2>/dev/null | wc -l)"
  sleep 60
done
```

**判定**：**单调增长且不回落 → 泄漏**。稳定在某个值 → 不是泄漏。

### fd 泄漏的常见来源

| 来源 | 特征 |
|---|---|
| **socket 未 close** | `CLOSE_WAIT` 堆积 + fd 数增长 |
| **文件未关闭** | `/proc/<pid>/fd` 里出现大量 `*.tmp`、`deleted` |
| **fd 被子进程继承** | fork 后子进程不关继承的 fd |
| **fd 上限触顶** | `EMFILE` 报错，新连接/文件全部打不开 |

### fd 上限触顶的排查

```bash
cat /proc/<pid>/limits | grep -i "open files"
# 若为 1024（默认），长跑服务几乎必然触顶

# 查看各类型 fd 分布
ls -l /proc/<pid>/fd | awk '{print $NF}' | sed 's/[0-9]*$//' | sort | uniq -c
```

**解决**：提高上限（`LimitNOFILE=` in systemd unit，或 `ulimit -n`）**但这只是缓解，根本是修泄漏**。

---

## 长连接卡顿与重连

### 掉线排查

```bash
# TCP keepalive 参数
cat /proc/sys/net/ipv4/tcp_keepalive_time
cat /proc/sys/net/ipv4/tcp_keepalive_intvl
cat /proc/sys/net/ipv4/tcp_keepalive_probes

# 心跳设计要点：应用层心跳比 TCP keepalive 更可靠
#   - TCP keepalive 默认 2 小时才首次探测，太慢
#   - 应用层心跳可自定义超时，快速发现断线
```

### 心跳设计要点

```c
// 心跳超时判定：不能只看一次 recv 超时，要累计
int idle_count = 0;
while (running) {
    ret = recv_with_timeout(fd, buf, sizeof(buf), 200);  // 200ms
    if (ret > 0) { idle_count = 0; }
    else if (ret == 0 || errno == EAGAIN) {
        if (++idle_count > 25) {          // 200ms × 25 = 5s 无数据
            reconnect();
            idle_count = 0;
        }
    }
    else {
        reconnect();
    }
}
```

**要点**：单次 recv 超时不代表断线；必须连续 N 次超时才判定。防止正常网络抖动导致频繁重连。

### 重连策略

- **指数退避**：1s → 2s → 4s → 8s → 上限 30s
- **不要无脑立即重连** —— 服务端重启时会瞬间被大量客户端打垮
- **重连后要重建完整状态**（订阅关系、序列号对齐），不只是重开 socket

---

## 卡顿定位：分层排查

```
应用处理慢 → Recv-Q 堆积
     ↓
网络拥塞   → Send-Q 堆积 / 丢包
     ↓
网卡问题   → link drop/error 计数
```

```bash
# 1. 看队列堆积
ss -tn | awk '{print $1, $2}' | head -20
ss -tnm

# 2. 看网卡丢包
ip -s link show eth0

# 3. 抓包分析（最直接）
tcpdump -i eth0 -nn port <port> -w /tmp/cap.pcap

# 4. 应用侧确认处理耗时
strace -p <pid> -c -f -e trace=network
```

**关键**：区分「网络慢」和「应用处理慢」——两者都表现为卡顿，但修法完全不同。

---

## 内核网络参数（嵌入式调优）

```bash
# TCP 拥塞控制可用选项
cat /proc/sys/net/ipv4/tcp_available_congestion_control

# 队列长度
cat /proc/sys/net/core/netdev_max_backlog

# TIME_WAIT 复用（短连接服务必开）
sysctl -w net.ipv4.tcp_tw_reuse=1

# 连接队列
cat /proc/sys/net/core/somaxconn

# TIME_WAIT 数量
cat /proc/sys/net/ipv4/tcp_max_tw_buckets
```

**注意**：这些是**全局**参数，改动影响整个系统，必须记录并在升级时保留。嵌入式设备变更前先确认当前值。

---

## 长跑网络验证

```bash
# 持续采样网络与 fd 指标
while true; do
  echo "$(date) \
    fd=$(ls /proc/<pid>/fd 2>/dev/null | wc -l) \
    tw=$(ss -tan state time-wait 2>/dev/null | wc -l) \
    cw=$(ss -tan state close-wait 2>/dev/null | wc -l) \
    rx_drop=$(ip -s link show eth0 | grep -i RX | awk '{print $5}')"
  sleep 300
done | tee /tmp/net-longrun.log
```

**重点看 fd 与 CLOSE_WAIT**——它们是网络类泄漏的最直接指标。

---

## 边界与注意

- **缓冲区调优前先看 Recv-Q/Send-Q**，不要盲目加大缓冲区掩盖消费慢的问题
- **CLOSE_WAIT 堆积几乎总是本端问题**，不要一上来就怀疑对端
- **fd 上限提高只是缓解**，必须同时修泄漏
- **粘包靠长度前缀或分隔符解决**，不要假设一次 recv 就是完整数据
- 心跳误判会导致频繁重连，反而加重负载
- 内核参数是全局的，变更需记录，设备升级要保留
- 实测数据用具体数字（延迟 ms、丢包率、fd 数），不用「网络有点慢」