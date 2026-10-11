# 应用线程、容器与服务运行时

> 仅当任务明确涉及嵌入式应用线程/事件循环、epoll、Docker 部署或 nginx 配置时加载；通用故障定位仍以 [embedded-debug-workflow](../SKILL.md) 为入口。内核 IRQ、workqueue 或驱动锁问题转到 [linux-device-drivers](../../linux-device-drivers/SKILL.md)。容器 OOM、内存压力或 CPU/内存瓶颈以 [embedded-perf-debug](../../embedded-perf-debug/SKILL.md) 为主，本页只补充运行时配置背景。

## 应用线程与异步 IO

诊断线程卡住或事件循环不响应时，先记录线程数、线程状态、CPU 使用和等待点，并按 [embedded-debug-workflow](../SKILL.md) 的方法保留故障现场。不要仅凭“线程多”或“事件循环卡”就改变调度策略。

- **CPU 亲和性**：`taskset` 或 `sched_setaffinity` 可限制线程/进程可运行的 CPU，但不保证吞吐或延迟改善。
- **线程优先级**：`SCHED_FIFO` 需要相应权限（常见为 `CAP_SYS_NICE`）；不受控的实时优先级可能饿死普通任务。
- **并发度**：线程数超过可用 CPU 会增加调度和切换开销；线程池大小要结合实际负载与等待比例测量。
- **锁与等待**：更细的锁粒度可能降低共享资源间的争用，但会增加锁管理和顺序约束的复杂度；根据测得的锁等待和线程栈证据选择。
- **异步 IO**：高 fd 数量场景可评估 `epoll`。异步与多线程混用会扩大竞态面，应明确所有权、取消、超时和背压处理。

以下命令会影响指定进程的调度或 CPU 亲和性。只有在用户授权的运维/调优范围内，确认目标 PID、回滚方式并先后记录负载测量后才应用：

```bash
taskset -c 2,3 ./app
chrt -f 80 ./app
```

## Docker 部署与资源限制

仅在目标镜像包含 Docker 且任务确实涉及容器部署时使用。以下命令是配置示例，会创建并启动容器；确认镜像、卷路径、网络、重启策略和资源预算后再应用：

```bash
docker run -d --name app --restart always \
  -v /data/config:/app/config \
  --memory=512m --cpus=1.5 \
  myapp:latest

docker stats
docker logs -f app
```

- 嵌入式部署要为服务配置经核算的内存和 CPU 资源上限；应按设备可用资源、其他进程、cgroup 版本及 swap 配置设定，不能直接套用示例中的 `512m`、`1.5`。容器限制控制资源上限，但不保证宿主机不会 OOM。
- 通过 `docker stats`、运行时 inspect 信息和目标 cgroup 计数观测实际用量；同时记录采样时长、并发负载与峰值，不用单次快照替代趋势分析。
- `--restart always` 适合确有自恢复需求的服务；部署前确认它与设备启动流程、维护窗口及停止行为兼容。
- `overlay2` 使用分层文件系统；`vfs` 可能在特定嵌入式环境更简单，但通常有额外开销。先确认 Docker 支持的 storage driver 和实际磁盘预算。
- 精简镜像可降低存储占用和传输成本；保留运行所需库、证书和诊断工具。

若证据指向容器内存耗尽、cgroup OOM 或宿主资源压力，主线转到 [embedded-perf-debug](../../embedded-perf-debug/SKILL.md)；本节只用于核对部署参数。磁盘/块设备枚举、健康状态和有界存储基准属于 [storage-hardware-io](../../storage-hardware-io/SKILL.md)。

## nginx 反向代理

仅在任务涉及 nginx 服务或反向代理配置时加载。下面配置是示意，应按目标 nginx 版本、TLS/认证要求、上游服务和设备资源调整：

```nginx
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    client_max_body_size 50m;
    keepalive_timeout 30;
}
```

- worker 数量、`worker_connections` 和文件描述符上限要按 CPU、内存、`ulimit -n` 与实际并发测量设定。
- 静态缓存可能减少重复磁盘读取，但要依据访问模式、可用空间与缓存失效策略验证。
- `nginx -t` 检查配置；`nginx -s reload` 会改变运行服务，仅在已授权的部署/维护范围内执行，并保留当前配置以便回滚。

## 测量与操作边界

调度策略、容器限制、重启策略和服务配置都是运行时行为的一部分。先以固定负载和时间窗口记录 CPU、内存、线程状态、请求延迟或吞吐，再一次调整一个参数并复测；报告采样条件、测量值和未验证项。诊断请求默认先使用观测证据；启动/停止容器、改变调度参数或 reload 服务前，确认该状态变更属于用户授权范围。
