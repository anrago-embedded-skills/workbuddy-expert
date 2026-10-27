# 网络现场观测命令

> 仅在需要路由/接口状态、进程 fd 证据、有限抓包或较长趋势时读取。单独判断 Send-Q/Recv-Q 或 TCP 重传时，使用较短的 [network-cheatsheet.md](network-cheatsheet.md)；socket 代码和选项见 [socket-implementation.md](socket-implementation.md)。

以下命令在 TARGET Linux 上运行。IFACE 必须来自目标 ip link 输出或操作人员确认；PID 必须是目标进程列表中的数字值。先确认工具和权限。路径缺失或命令失败表示证据不可用，不能记成零，也不能用开发主机的值替代。

## 连接与接口快照

```bash
# TARGET / 只读。IFACE 应来自目标 ip link 输出。
if [ -z "$IFACE" ]; then printf '请设置目标上已确认的 IFACE 接口名\n' >&2; exit 2; fi
ip link show dev "$IFACE" || exit 2
ip -s link show dev "$IFACE"
ip addr show dev "$IFACE"
ip route show
ss -s
ss -tan state time-wait
ss -tan state close-wait
cat /proc/net/sockstat
```

接口 drop/error 是累计值；比较已知时间间隔内的变化。累计值非零不能证明本次故障来自链路。CLOSE_WAIT 表示对端 FIN 已到达而本端尚未关闭 socket；检查进程归属和存续时间。主动关闭后出现 TIME_WAIT 可能正常，应结合连接速率和实际端口压力判断。

## 路由探测

路由探测只使用已针对目标确认的目的地址、配置网关、对端主机名和服务端口：

```bash
# TARGET / 只读路由查询和有限探测；探测会产生网络流量。
if [ -z "$DESTINATION" ] || [ -z "$GATEWAY" ] || [ -z "$HOST" ] || [ -z "$PORT" ]; then
  printf '请设置已确认的 DESTINATION、GATEWAY、HOST 和 PORT\n' >&2
  exit 2
fi
ip route get "$DESTINATION"
timeout 10s ping -c 3 -W 3 "$GATEWAY"
timeout 5s getent ahosts "$HOST"
timeout 5s nc -vz -w 3 "$HOST" "$PORT"
```

路由查询应显示选用的路由、接口和源地址。TCP 建连成功只证明该端口当时完成握手。ICMP 或 TCP 探测可能被过滤；ping 成功不证明应用可达，ping 失败也不证明服务已停止。

## 进程 fd 证据

```bash
# TARGET / 只读进程快照。PID 必须是目标进程列表中的数字值。
if [ -z "$PID" ]; then printf '请设置目标进程列表中的数字 PID\n' >&2; exit 2; fi
case "$PID" in
  *[!0-9]*) printf 'PID 必须为十进制目标进程号\n' >&2; exit 2 ;;
esac

if FD_LIST=$(ls -1A "/proc/$PID/fd" 2>/dev/null); then
  if [ -n "$FD_LIST" ]; then
    FD_COUNT=$(printf '%s\n' "$FD_LIST" | awk 'END { print NR }')
  else
    FD_COUNT=0
  fi
else
  FD_COUNT=unavailable
fi
printf 'fd_count=%s\n' "$FD_COUNT"
cat "/proc/$PID/limits"
ls -l "/proc/$PID/fd"
```

fd 目录项名称是数字；成功读取且为空的目录计数为零，`ls` 失败时记作 `unavailable`，不能记成零。在等价负载下多次比较同一 PID，并查看 fd 链接与 socket 状态，再判断增长是否像泄漏。进程退出、PID 重用或权限受限都会使比较失效。出现 `EMFILE` 时，将计数与软/硬 open files 限额比较；只有测得描述符需求支持时才提高限额。还需确认累积的是 socket、未关闭文件、fork 继承的 fd，还是其他有意保留的描述符。

## 当前 socket 缓冲值

```bash
# TARGET / 只读。参数文件是否存在取决于内核版本和配置。
cat /proc/sys/net/core/rmem_default
cat /proc/sys/net/core/wmem_default
cat /proc/sys/net/core/rmem_max
cat /proc/sys/net/core/wmem_max
cat /proc/sys/net/ipv4/tcp_rmem
cat /proc/sys/net/ipv4/tcp_wmem
ss -tnm
```

路径不可用可能由内核配置/版本或权限限制造成；不要复制主机值。参数解释和变更保护条件见 [kernel-network-tuning.md](kernel-network-tuning.md)。

## 有界抓包

```bash
# TARGET / 在 /tmp 新建抓包文件；需要 tcpdump 和抓包权限。
if [ -z "$IFACE" ] || [ -z "$PORT" ]; then printf '请设置已确认的 IFACE 和服务 PORT\n' >&2; exit 2; fi
CAPTURE=$(mktemp /tmp/net-cap.XXXXXX.pcap) || exit 1
timeout 30s tcpdump -i "$IFACE" -nn -s 96 -c 1000 "port $PORT" -w "$CAPTURE"
```

抓包在 30 秒或 1000 包时停止，以先达到者为准。`-s 96` 将包内容限制为最多 96,000 字节，加上 pcap 记录/文件头后总量约为 112 kB。即使限制长度，pcap 仍可能含敏感流量。权限错误、没有匹配数据或缺少 `timeout`/`tcpdump` 表示观测条件不符或不可用，不能说明链路正常。

只在终端显示的快照命令 `timeout 10s tcpdump -i "$IFACE" -nn -s 96 -c 100` 最多运行 10 秒或采集 100 包，不写 pcap 文件。

## 可选进程跟踪

```bash
# TARGET / 附加到运行中的进程，可能改变时序，最长 10 秒。
if [ -z "$PID" ]; then printf '请设置目标进程列表中的数字 PID\n' >&2; exit 2; fi
case "$PID" in
  *[!0-9]*) printf 'PID 必须为十进制目标进程号\n' >&2; exit 2 ;;
esac
timeout 10s strace -c -p "$PID" -f -e trace=network
```

10 秒限制附加窗口；`strace` 仍会改变时序且需要权限。超时只结束观测窗口，不会结束目标进程。已有应用日志和 socket 快照足以回答问题时优先使用它们。

## 长跑 fd、socket 与 drop 采样

仅在问题需要趋势时使用。命令每隔 5 分钟记录一次，共 13 个样本，从首次到末次最多 60 分钟；日志最多 13 行、3328 字节，并在 TARGET `/tmp` 创建新文件。命令正常运行完毕无需 Ctrl-C；采集前确认 PID 和接口。

```bash
# TARGET / 最多 13 个样本、60 分钟；日志上限 3328 字节。
if [ -z "$PID" ] || [ -z "$IFACE" ]; then printf '请设置数字 PID 和已确认的 IFACE\n' >&2; exit 2; fi
case "$PID" in
  *[!0-9]*) printf 'PID 必须为十进制目标进程号\n' >&2; exit 2 ;;
esac
ip link show dev "$IFACE" || exit 2
LOG=$(mktemp /tmp/net-longrun.XXXXXX.log) || exit 1

fd_count() {
  listing=$(ls -1A "/proc/$PID/fd" 2>/dev/null) || { printf 'unavailable'; return 0; }
  if [ -n "$listing" ]; then printf '%s\n' "$listing" | awk 'END { print NR }'; else printf '0'; fi
}
state_count() {
  rows=$(ss -H -tan state "$1" 2>/dev/null) || { printf 'unavailable'; return 0; }
  if [ -n "$rows" ]; then printf '%s\n' "$rows" | awk 'END { print NR }'; else printf '0'; fi
}
rx_drop_count() {
  value=$(cat "/sys/class/net/$IFACE/statistics/rx_dropped" 2>/dev/null) || { printf 'unavailable'; return 0; }
  case "$value" in ''|*[!0-9]*) printf 'unavailable' ;; *) printf '%s' "$value" ;; esac
}

i=1
while [ "$i" -le 13 ]; do
  stamp=$(date -u +%Y%m%dT%H%M%SZ 2>/dev/null) || stamp=unavailable
  printf '%s fd=%s time_wait=%s close_wait=%s rx_drop=%s\n' \
    "$stamp" "$(fd_count)" "$(state_count time-wait)" \
    "$(state_count close-wait)" "$(rx_drop_count)" >> "$LOG" || exit 1
  [ "$i" -eq 13 ] || sleep 300 || exit 1
  i=$((i + 1))
done
printf 'log=%s\n' "$LOG"
cat "$LOG"
```

读取 `ls`、`ss` 或 sysfs 失败时字段保持 `unavailable`；成功读取的空 fd 目录或空 `ss -H` 输出才是零。任一字段不可用时，不能当作零或宣称趋势完整。接口计数是累计值，应比较首末 `rx_drop`。每个计数至多 20 位十进制数或字符串 `unavailable`；固定时间戳和标签使每行不超过 256 字节。查看样本时间和日志路径，再解释趋势。
