# 网络取证速查表

> 网络问题排查最常用的命令。详细方法论见主 SKILL.md。

## 一次抓全网络现场

```bash
ss -s # 连接总览（ESTAB/TIME-WAIT/CLOSE-WAIT 统计）
ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn   # 按状态分布
ss -tan state time-wait | wc -l   # 短连接过多？
ss -tan state close-wait | wc -l  # 本端没 close？（泄漏）
ip -s link show eth0# 丢包与错误
ip addr show eth0
cat /proc/net/sockstat
```

## 队列堆积判读

```bash
# Recv-Q 大 = 本端消费慢；Send-Q 大 = 对端慢/拥塞
ss -tnm | head -20
```

## fd 与连接数

```bash
ls /proc/<pid>/fd | wc -l
cat /proc/<pid>/limits | grep -i "open files"
ss -tan | wc -l# 总连接数
```

## 缓冲区

```bash
cat /proc/sys/net/core/rmem_max
cat /proc/sys/net/ipv4/tcp_rmem
ss -tnm# 各连接实际缓冲区
```

## 分层连通性

```bash
ping -c 3 <gateway>       # 网关
ping -c 3 8.8.8.8         # 外网
nslookup <domain>          # DNS
ip route show default
```

## 抓包

```bash
tcpdump -i eth0 -nn port <port> -w /tmp/cap.pcap
tcpdump -i eth0 -nn -c 100        # 实时看
```

## 应用侧

```bash
strace -p <pid> -f -e trace=network
ss -tnp | grep <pid>              # 该进程持有的连接
```

## 长跑采样

```bash
while true; do
  echo "$(date) \
    fd=$(ls /proc/<pid>/fd 2>/dev/null | wc -l) \
    tw=$(ss -tan state time-wait 2>/dev/null | wc -l) \
    cw=$(ss -tan state close-wait 2>/dev/null | wc -l)"
  sleep 300
done | tee /tmp/net-longrun.log
```

## 关键判读

| 现象 | 结论 |
|---|---|
| CLOSE_WAIT 堆积 | **本端没调 close()** |
| Recv-Q 堆积 | 本端消费慢（应用问题） |
| Send-Q 堆积 | 对端慢或网络拥塞 |
| fd 单调增长 | fd 泄漏 |
| 网卡 drop 增长 | 队列溢出/链路问题 |

## 边界

- 抓包需root 权限
- `ss -tan | wc -l` 在高连接数时可能很慢，加 `-s` 更高效
- 内核网络参数是全局的，改前先记录当前值