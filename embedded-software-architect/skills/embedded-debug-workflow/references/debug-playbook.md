# 排障清单与进程/IPC 参考

> 在主技能正文不足以处理进程树、IPC 或 FIFO 细节时按需读取；PID/TID 参数和资源/热区采样的唯一规范见 [process-sampling.md](process-sampling.md)。

## 排障清单

1. **整理现状** — 记录现象、复现条件/频率、近期变更、目标版本和已有日志；未知信息明确标注。
2. **保存现场** — 在故障发生时保留有时间戳的相关应用、系统或内核证据；先检查是否有数据/现场会因重启消失。
3. **区分候选原因** — 对每个假设列出预期观测和反证，优先选择低风险且能区分原因的下一项检查。
4. **验证修复** — 一次调整一个因果变量，并在相同触发条件下回归；分别报告 HOST 检查与 TARGET 验证。
5. **长跑观察** — 覆盖复现窗口并报告采样范围与时长；进程 RSS 和 thermal 使用 `process-sampling.md` 的有界采样器。

| 观测 | 可先检查 | 注意 |
|---|---|---|
| 应用日志或系统调用跟踪指向某个调用 | 调用方、参数、错误码和时序 | 相关性不等于根因 |
| `dmesg` 有 Oops 或驱动错误 | 匹配的内核、驱动及设备状态 | 保存完整日志和构建信息 |
| 进程阻塞在 `read()` / `write()` | fd、IPC 对端、队列状态和发生时序 | 区分正常等待、超时与死锁 |
| 目标电压/温度测量异常 | 供电或热管理路径 | 记录来源、单位和测量条件 |

## 进程树与任务状态

需要指定进程时，先在同一个 TARGET shell 运行 [process-sampling.md](process-sampling.md) 的 PID/TID 验证段。以下命令假设 `target_pid`、`target_proc` 和 `target_status` 已在该 shell 中设置。目标 `ps` 可能是 procps 或 BusyBox 变体；使用前确认选项，缺少时记为 unavailable。

```sh
# TARGET：可选进程树视图；仅当目标 ps 支持这些选项时使用
ps -ef --forest
ps -eo pid,ppid,stat,comm --sort=ppid

# TARGET：使用 process-sampling.md 验证的进程路径
cat "$target_status"
ls "${target_proc}/task"
```

`TracerPid` 非零表示有 tracer 附加，不单独证明进程停止；`State: t` 表示 tracing stop，`T` 表示 job-control stop。线程状态可能不同，应检查确认的相关 TID。读取 `wchan`、调用栈或系统调用只能说明采样时观察到的等待点。

### 僵尸与子进程回收

```sh
# TARGET：目标 ps 支持这些字段时列出僵尸及父 PID
ps -eo pid,ppid,stat,comm | awk '$3 ~ /Z/'
```

僵尸已退出，不再执行用户态代码；父进程回收前仍占用 PID，并保留少量内核任务记录和记账信息。单个僵尸不会继续执行代码；大量未回收的僵尸可能耗尽 PID 空间。

```c
// 示意：循环回收当前已退出的子进程；生产代码还须处理 waitpid() 错误
while (waitpid(-1, &status, WNOHANG) > 0) {
    /* reap each child */
}
```

`WNOHANG` 返回 0 表示仍有匹配子进程运行；循环只回收当前已退出的子进程。选项为 0 的 `waitpid()` 会等待子进程退出，这个等待本身不证明死锁。

## FIFO 与其他 IPC

FIFO 命令要求 TARGET 提供 `mkfifo`、`timeout` 和兼容的 POSIX shell，且当前账号有权限。先确认工具选项；不可用时记录 unavailable，不能改成无期限等待。下例固定路径只在目标上不存在时创建，已存在（包括悬空符号链接）时停止，绝不覆盖。

```sh
(
# TARGET：确认工具与权限后创建临时 FIFO；此路径已存在则停止
if [ -e /tmp/myfifo ] || [ -L /tmp/myfifo ]; then
  printf '%s\n' 'temporary FIFO path already exists; choose an approved unused path' >&2
  exit 2
fi
if ! mkfifo /tmp/myfifo; then
  printf '%s\n' 'could not create temporary FIFO' >&2
  exit 2
fi
ls -l /tmp/myfifo
)
```

在两个 TARGET 终端并发执行；每端最多等待 10 秒。缺少 `timeout` 或实现不兼容时不执行，记录工具限制。

```sh
# TARGET terminal A：reader
timeout 10s cat /tmp/myfifo
```

```sh
# TARGET terminal B：writer，在 terminal A 等待期间执行
timeout 10s sh -c 'printf "hello\n" > /tmp/myfifo'
```

FIFO 端点打开时可能等待对端；有限的管道缓冲区写满后写操作会阻塞；所有写端关闭后读端才会收到 EOF。Linux FIFO 的 `O_RDWR` 打开方式可能让写端一直保持打开，因此收不到 EOF；紧密循环重试 `EAGAIN` 可能占满一个 CPU 核。应用应按读写角色选择打开方式，使用 `poll`/`epoll` 或截止时间，处理 `EINTR`、`EAGAIN` 和 EOF，并提供取消机制。故障现场中观察到阻塞在 FIFO `read` 只说明当前没有可读数据，不推断对端此前是否读过；阻塞在 `write` 还要结合缓冲区和对端消费情况。

| 手段 | 特点 | 常见用途 |
|---|---|---|
| `pipe()` | 匿名 fd，常由 `fork()` 继承，也可通过 fd 传递 | 本地进程通信 |
| FIFO | 有名端点，可供无关进程使用 | 单向流或简单进程间通信 |
| `socketpair()` | 本地双向全双工 | 父子进程双向通信 |
| Unix domain socket | 本地套接字，可按协议复用 | 本地服务和多客户端 |
| 消息队列 | 内核管理消息 | 少量有界消息 |
| 共享内存 | 适合大块数据，默认没有同步 | 需另配信号量/互斥锁及生命周期管理 |

```c
// 示意：Unix domain stream socket 的地址与监听接口
int fd = socket(AF_UNIX, SOCK_STREAM, 0);
struct sockaddr_un addr = {.sun_family = AF_UNIX};
strcpy(addr.sun_path, "/tmp/my.sock");
if (bind(fd, (struct sockaddr *)&addr, sizeof(addr)) == 0)
    listen(fd, 5);
```

这段代码只展示接口形状，不是可直接部署的完整服务：实际实现还须检查返回值、清理路径、地址长度、权限、并发、超时和 fd 生命周期。共享内存必须配同步机制，否则存在数据竞争和可见性问题。

## HOST / TARGET 与部署验证

HOST 负责使用实际 SDK/BSP 构建和检查产物；TARGET 提供板卡身份、运行版本、功能行为及相关日志。只有在目标 ABI、部署文件路径、访问通道、授权范围、备份和恢复方法都已确认后，才按项目已有的部署流程操作。缺少目标或某一前提时，报告已完成的 HOST 检查及具体 unavailable 项；不要用猜测的 SSH 主机、文件路径或服务名代替目标信息。

## 常见误判与边界

- RSS 增长不单独证明泄漏；查明增长类别、归属和时间趋势。
- `TracerPid` 非零不表示任务已停；结合 `State` 和线程状态。
- `CLOSE_WAIT` 表示对端 FIN 已到而本端尚未关闭 socket；再查进程、持续时间和清理逻辑。
- 编译成功不证明目标 ABI、依赖、部署版本或板上功能正确。
- 主机、静态或离线检查只能证明其实际覆盖范围；不得描述成板上验证。

## 参考资料

- [`/proc/<pid>/status` state and TracerPid fields](https://man7.org/linux/man-pages/man5/proc_pid_status.5.html)
- [Linux FIFO behavior](https://man7.org/linux/man-pages/man7/fifo.7.html)
