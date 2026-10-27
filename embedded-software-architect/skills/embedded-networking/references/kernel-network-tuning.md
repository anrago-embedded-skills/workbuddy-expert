# 内核网络参数核对

> 仅当队列、重传或容量证据使某个内核参数成为可检验假设时读取。单个 Send-Q、`TIME_WAIT` 数量或接口计数不能单独支持 sysctl 调整。

## 先读目标的实际配置

命令在 TARGET Linux 上运行。先确认内核版本和网络命名空间；有些参数按命名空间隔离，有些作用范围更广。目标缺少路径或权限不足时记作不可用，不能用开发主机的值代替。

```bash
# TARGET / 只读。文件缺失可能由内核版本或配置差异造成。
for setting in \
  /proc/sys/net/core/rmem_default \
  /proc/sys/net/core/wmem_default \
  /proc/sys/net/core/rmem_max \
  /proc/sys/net/core/wmem_max \
  /proc/sys/net/core/netdev_max_backlog \
  /proc/sys/net/core/somaxconn \
  /proc/sys/net/ipv4/tcp_rmem \
  /proc/sys/net/ipv4/tcp_wmem \
  /proc/sys/net/ipv4/tcp_available_congestion_control \
  /proc/sys/net/ipv4/tcp_keepalive_time \
  /proc/sys/net/ipv4/tcp_keepalive_intvl \
  /proc/sys/net/ipv4/tcp_keepalive_probes \
  /proc/sys/net/ipv4/tcp_tw_reuse \
  /proc/sys/net/ipv4/tcp_max_tw_buckets
do
  if [ -r "$setting" ]; then
    value=$(cat "$setting" 2>/dev/null) || { printf '%s=unavailable\n' "$setting"; continue; }
    printf '%s=%s\n' "$setting" "$value"
  else
    printf '%s=unavailable\n' "$setting"
  fi
done
```

输出是目标的当前配置，不是推荐值。`net.core.rmem_max` / `wmem_max` 会限制普通 socket 缓冲请求；TCP 自动调优还使用 `tcp_rmem` / `tcp_wmem`，实际效果应结合 socket 的 `getsockopt()` 值核对。解释 `tcp_tw_reuse` 等较少使用的参数前，先阅读对应目标内核版本的文档；默认值和可接受值曾随内核版本变化，它不是短连接负载的通用修复。backlog、拥塞控制、keepalive 和 socket 缓冲参数控制不同的行为，不应作为一组一起改。详见 [Linux kernel IP sysctl 文档](https://docs.kernel.org/networking/ip-sysctl.html)。

## 运行时变更条件

只有测量指出具体参数限制、作用范围已确认且存在等价基线负载时才修改一个参数。先保存原值和回滚命令。`sysctl -w` 会立即改变运行中的目标；权限拒绝、键不存在或数值被拒绝都表示变更没有应用。

```bash
# TARGET / 状态变更模板；填入经测量且处于目标限制内的十进制数值。
: "${MEASURED_BYTE_LIMIT:?请填入经测量且未超过目标限制的十进制数值}"
case "$MEASURED_BYTE_LIMIT" in
  ''|*[!0-9]*) printf 'MEASURED_BYTE_LIMIT 必须是十进制字节数\n' >&2; exit 2 ;;
esac
sysctl -w "net.core.rmem_max=$MEASURED_BYTE_LIMIT"
sysctl net.core.rmem_max
```

记录原值、目标版本、命名空间、负载、socket 实际值和变更前后结果。参数被拒绝或 socket 行为未按预期变化时，停止并恢复原值。`sysctl -w` 成功只确认参数写入，不证明 socket 使用了请求容量。单 socket 的 `SO_RCVBUF`、`SO_SNDBUF` 或 `TCP_NODELAY` 行为见 [socket-implementation.md](socket-implementation.md)。
