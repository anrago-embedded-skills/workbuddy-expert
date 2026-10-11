# 排障流程速查表

> 根据现场证据选择下一步。详细方法见主 SKILL.md。

## 排障流程

1. **整理现状** — 记录现象、触发条件、复现频率、近期变更和可用的目标板信息；未知项明确标注。
2. **采集现场** — 在问题发生时保存相关的 `dmesg`、`journalctl`、进程状态或网络数据。
3. **建立假设并验证** — 写明预期观测；新证据可直接指向任一层，不要求固定顺序。
4. **测试修复** — 一次只改一个变量；按现有条件验证受影响行为，并注明尚未执行的目标板检查。
5. **观察复现窗口** — 长时间问题应记录采样时长；按 Ctrl-C 停止持续采样。

## 证据对应的排查方向

| 观测 | 可先检查 | 注意事项 |
|---|---|---|
| 应用日志或 `strace` 指向某个调用 | 应用参数、调用方和时序 | 确认错误码及对应的输入/状态 |
| `dmesg` 出现 Oops 或驱动错误 | 内核、驱动及相关设备状态 | 保留完整日志和匹配的构建信息 |
| 进程阻塞在 `read()` / `write()` | 对应 fd、IPC 对端和队列状态 | 区分正常等待、超时和死锁 |
| 目标电压/温度测量异常 | 供电或热管理路径 | 记录测量条件和数值 |

## 进程无响应

```bash
cat /proc/<pid>/status | grep -E "^State|^TracerPid"
ps -eo pid,ppid,stat,comm | awk '$3 ~ /Z/'
cat /proc/<pid>/wchan
timeout 10s strace -p <pid> -f
```

| 状态 | 含义 |
|---|---|
| `TracerPid` 非 0 | 有 tracer 附加；不能单独证明进程已停止 |
| `State: t` | tracing stop |
| `State: T` | job-control stop |
| `State: Z` | 僵尸，父进程尚未回收 |

多线程进程应检查相关 `/proc/<pid>/task/<tid>/status`，因为线程状态可能不同。重启前先保存能解释故障的现场；若服务恢复需要立即处理，注明哪些证据未能采集。

## 部署验证

```bash
scp myapp root@<board>:/usr/bin/
ssh root@<board> "systemctl restart myapp"
ssh root@<board> "myapp --version"
```

部署命令需使用匹配目标 ABI 的构建产物。目标板不可用时，报告已完成的主机检查，并标明版本和功能尚未在板上验证。

## 长跑采样

```bash
# 按复现窗口采样；Ctrl-C 停止
while true; do
  echo "$(date) rss=$(ps -o rss= -p <pid>) cpu=$(top -bn1 -p <pid> | tail -1 | awk '{print $9}') temp=$(cat /sys/class/thermal/thermal_zone0/temp)"
  sleep 300
done | tee /tmp/longrun.log
```

## 常见误判

| 现象 | 候选方向 | 需要补充的证据 |
|---|---|---|
| RSS 增长 | 泄漏、缓存或负载变化 | 找出增长类别和所有者；RSS 趋势本身不是泄漏证明 |
| 进程有 `TracerPid` | 调试器或其他 tracer 附加 | 同时检查 `State`；只有 `State: t` 表示 tracing stop |
| `CLOSE_WAIT` 存在 | 对端 FIN 已到，本端尚未关闭 socket | 查所属进程、socket 存续时间和清理逻辑 |
| 编译成功但目标行为异常 | 目标 ABI、版本、配置或运行环境 | 核对实际部署版本、日志和目标状态 |

## 边界

- 让直接证据决定定位起点，不要先排除无关层
- 采样时长和观察范围应随结论一起报告
- 修复验证应匹配现有环境，并写清未执行的检查
- 使用具体测量值，不用「正常」「没问题」代替证据

## 参考资料

- [`/proc/<pid>/status` state and TracerPid fields](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html)
- [Linux FIFO behavior](https://man7.org/linux/man-pages/man7/fifo.7.html)
