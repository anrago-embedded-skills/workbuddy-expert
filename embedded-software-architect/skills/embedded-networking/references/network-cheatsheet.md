# 网络队列速查表

> 仅在需要精确 Send-Q/Recv-Q 或 TCP 重传命令、字段解释时读取。路由、接口、fd、抓包、进程跟踪或长跑趋势见按需读取的 [network-observation.md](network-observation.md)。

以下命令运行在 TARGET Linux，读取当前状态，不改变 socket 或内核参数。先确认目标工具和权限。

## 队列与重传

```bash
# TARGET / 只读快照；可用时包含 TCP 与 socket 内存详情。
ss -tinmp state established
nstat -az
```

对已建立 socket，Recv-Q 是等待本地应用读取的数据，Send-Q 是尚未确认的数据；对监听 socket，两列表示 accept 队列占用量与 backlog 上限。`ss -i` 在目标版本支持时显示 TCP 诊断，`-m` 显示 socket 内存记账。`nstat -az` 提供内核或网络命名空间计数器，名称和可用性因目标而异。

在同一故障时间窗内取得多个可比较样本，并确认 socket、数字 PID、应用耗时与对端行为。Send-Q 增长说明字节仍未被确认，单独不能区分发送调度、接收端行为、拥塞或路径故障。不要从一次快照调大缓冲区。队列字段见 [Linux `ss(8)`](https://man7.org/linux/man-pages/man8/ss.8.html)。

若 TCP 连通但应用协议应答/会话异常，转 [protocols-embedded](../../protocols-embedded/SKILL.md)。若证据落在 Wi-Fi 关联、漫游、信号或固件，再转 [wireless-connectivity](../../wireless-connectivity/SKILL.md)。
