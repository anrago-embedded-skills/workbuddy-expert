# 网络取证速查表

> 网络问题排查最常用的命令。详细方法论见主 SKILL.md。

以下均为 TARGET Linux 例子；先确认接口/PID/端口与工具版本。带 `$VAR` 的命令要求先设置目标值，角括号占位符不是可直接运行的 shell 命令。只读快照与写捕获/附加进程的操作分开标出；`timeout`, `tcpdump`, `strace` 等不一定存在于精简 rootfs。期望/失败解释跟随各节。

## 一次抓全网络现场

```bash
# TARGET / read-only snapshots; confirm IFACE from `ip link` first.
: "${IFACE:?set IFACE to the target interface}"
ss -s # 连接总览（ESTAB/TIME-WAIT/CLOSE-WAIT 统计）
ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn   # 按状态分布
ss -tan state time-wait | wc -l   # 查看 TIME_WAIT 数量，需结合连接速率判断
ss -tan state close-wait | wc -l  # 对端 FIN 已到；本端尚未 close
ip -s link show dev "$IFACE"      # 丢包与错误计数
ip addr show dev "$IFACE"
cat /proc/net/sockstat
```

预期为当前 socket、接口累计计数和地址状态。非零/缺字段表示工具、接口、权限或内核支持不足；比较两个时间点的计数增量，不能凭非零累计数断定有丢包。

## 队列堆积判读

```bash
# 已建立 socket：Recv-Q 是待本地应用读取的数据；Send-Q 是尚未确认的数据。
# 监听 socket 的两列表示 accept 队列占用量和 backlog 上限。
ss -tnm | head -20
```

## fd 与连接数

```bash
# TARGET / read-only process snapshot.
: "${PID:?set PID to the intended target process}"
ls "/proc/$PID/fd" | wc -l
cat "/proc/$PID/limits" | grep -i "open files"
ss -tan | wc -l # 总连接数
```

多次采样发现 fd 增长可作为泄漏候选线索。对照 `"/proc/$PID/fd"` 链接和 socket 状态，查明累积的是哪些描述符；进程退出/权限拒绝会导致查询失败，单独的计数不能证明泄漏。

## 缓冲区

```bash
# TARGET / read-only current settings; file existence is kernel/config dependent.
cat /proc/sys/net/core/rmem_max
cat /proc/sys/net/ipv4/tcp_rmem
ss -tnm # 各连接实际缓冲区
```

预期输出当前目标参数/队列缓冲数据；路径缺失或字段不支持表示不能从该目标读取该证据，不能套用主机值。

## 分层连通性

```bash
# TARGET / read-only route and bounded probes. Use known target endpoints.
: "${DESTINATION:?set destination IP/host}"
: "${GATEWAY:?set configured target gateway}"
: "${HOST:?set intended peer hostname}"
: "${PORT:?set intended service port}"
ip route get "$DESTINATION" # 查找实际路由
ping -c 3 "$GATEWAY"        # ICMP 可达性；peer 可能禁 ping
getent ahosts "$HOST"      # 使用系统 resolver 查询 DNS
nc -vz -w 3 "$HOST" "$PORT" # TCP 端口连通性（若系统提供 nc）
ip route show default
```

`ip route get` 应显示选用路由/接口/源地址；DNS 预期返回地址，`nc` 成功表示目标端口完成 TCP 建连。Ping success does not prove an application port is reachable; ping failure does not prove the host or service is down. 测试会发出网络流量，ICMP/TCP 也可能被网络策略过滤。

## 抓包

```bash
# TARGET / packet capture writes a new file; usually requires root/capture capability.
: "${IFACE:?set IFACE to the target interface}"
: "${PORT:?set PORT to the intended service port}"
CAPTURE="$(mktemp /tmp/net-cap.XXXXXX.pcap)" || exit 1
timeout 30s tcpdump -i "$IFACE" -nn -c 1000 "port $PORT" -w "$CAPTURE"
# Bounded display-only capture, still captures live traffic.
timeout 10s tcpdump -i "$IFACE" -nn -c 100
```

预期写入的 pcap 最多 1000 包或持续 30 秒；无包/权限错误表示抓取条件、接口、过滤器或流量窗口不匹配，不证明线路正常。pcap 可能含敏感流量，按目标数据处理规则保存。

## 应用侧

```bash
# TARGET / strace attaches to a live process and can affect timing; requires permission.
: "${PID:?set PID to the intended target process}"
timeout 10s strace -p "$PID" -f -e trace=network
ss -tnp | grep "$PID"              # 该进程持有的连接
```

超时表示观察窗口结束；拒绝附加表示权限、Yama/ptrace policy 或 PID 问题。先用 `ss` 与现有应用日志，只有需要时才 attach。

## 长跑采样

```bash
# TARGET / continuous sampler; creates a new log until interrupted with Ctrl-C.
: "${PID:?set PID to the intended target process}"
LOG="$(mktemp /tmp/net-longrun.XXXXXX.log)" || exit 1
while true; do
  echo "$(date) \
    fd=$(ls "/proc/$PID/fd" 2>/dev/null | wc -l) \
    tw=$(ss -tan state time-wait 2>/dev/null | wc -l) \
    cw=$(ss -tan state close-wait 2>/dev/null | wc -l)"
  sleep 300
done | tee "$LOG"
```

每一行是趋势采样，不是单次定论；PID 消失/权限不足会导致字段缺失。按 Ctrl-C 停止并记录时长，日志写入路径见 `$LOG`。

## 候选线索

| 现象 | 结论 |
|---|---|
| CLOSE_WAIT 持续存在 | 对端 FIN 已到，本端还未关闭 socket；确认进程归属和存续时间 |
| 已建立 socket 的 Recv-Q 持续增长 | 本地应用读取不及；结合处理耗时和 socket 角色检查 |
| 已建立 socket 的 Send-Q 持续增长 | 数据尚未被确认；检查重传、路由、抓包和对端行为 |
| fd 多次采样持续增长 | 检查累积的描述符类型和所属进程；增长本身不能证明泄漏 |
| 网卡 drop/error 计数增加 | 对比采样间隔内的增量，再查驱动、队列和协议证据 |

## 边界

- 抓包通常需 root 或相应 capability
- `ss -tan | wc -l` 在高连接数时可能很慢，加 `-s` 更高效
- 网络参数的作用范围依目标内核而定；更改前先记录当前值并查阅对应版本文档
- 持续采样按复现窗口运行；按 Ctrl-C 停止并记录采样时长
