---
name: embedded-debug-workflow
description: |
  General embedded debugging methodology: layered localization (app/system/driver/hardware), evidence-driven triage, cross-compile-deploy-verify loop.
  TRIGGER when: 板子上出问题、需要排查、定位问题、复现不了、功能异常、行为不符预期、帮我调试、抓日志、系统没反应、帮我看看这个现象、怎么修、排查思路、分层定位、长跑验证、帮我看看、什么问题、怎么回事、为什么会这样、这是什么毛病、有问题、异常、不对劲、不对、错了、不生效、不起作用、没反应、帮我查、帮我分析、需要排查、管道、FIFO、命名管道、mkfifo、进程间通信、IPC、多进程、父子进程、fork、僵尸进程收不掉、子进程拖死主进程、管道阻塞、消息队列、管道阻塞、管道卡住、FIFO 阻塞、多进程问题、父子进程问题、子进程拖死主进程、僵尸进程收不掉、进程通信有问题,
  DO NOT TRIGGER when: 明确是内存/OOM/性能问题（用 embedded-perf-debug）；明确是网络问题（用 embedded-networking）；明确是编译/设备树问题（用 embedded-bsp-kernel）;明确是纯 socket/fd 泄漏（用 embedded-networking）,
---

# embedded-debug-workflow

> 嵌入式排障的通用方法论：**分层定位 + 取证驱动 + 回归验证**。平台无关。

## 核心原则

1. **分层定位，不跨层猜测** — 按「应用层 → 系统层 → 驱动层 → 硬件层」逐层排除
2. **证据优先** — 每个判断都要有实测数据支撑
3. **一次改一个变量** — 否则无法归因
4. **改后必回归** — 修复不等于结束，确认无副作用才算完

---

## 分层定位法

遇到功能异常，**从上往下**逐层排除，不要跳步：

```
应用层    ← 先看这里：业务逻辑、参数、时序
   ↓ 排除后
系统层    ← 资源、服务、权限、配置
   ↓ 排除后
驱动层    ← 内核模块、ioctl、设备树
   ↓ 排除后
硬件层    ← 供电、信号、芯片手册
```

### 各层的排查手段

| 层 | 排查手段 |
|---|---|
| **应用层** | 日志、`strace`、`gdb` 断点、代码走查 |
| **系统层** | `systemctl status`、`journalctl`、`dmesg`、资源占用 |
| **驱动层** | `dmesg` 驱动日志、`/sys/class/video4linux`、`media-ctl -p`、`/proc/interrupts` |
| **硬件层** | 万用表/示波器、寄存器读值、芯片手册 |

**关键**：**不要在上层没排除时就去动下层**。大量无效劳动都源于此。

---

## 标准排障流程

### Phase 1：澄清与现状固化

必须明确：
- 目标板型号 + SoC + 固件版本
- 现象描述：能复现吗？触发条件？频率？
- 已有尝试与已排除方向
- 最近有无变更（代码/配置/硬件）

```bash
# 固化现状
uname -a
cat /etc/os-release
cat /proc/device-tree/model
free -h
df -h
```

### Phase 2：取证（不是猜测）

```bash
dmesg -T | tail -200        # 内核侧
journalctl -b -p err        # 系统侧
```

关键是**抓到出问题的那一刻**，而不是事后回忆。

### Phase 3：假设与验证

每次只验证一个假设。例如：

> 假设：内存泄漏导致 OOM
> 验证：采样 10 分钟看RSS 是否单调上升

```bash
for i in $(seq 1 10); do
  date; ps -o rss= -p <pid>; sleep 60
done
```

**假设被推翻就换一个，不要在一个假设上打转。**

### Phase 4：修复与验证

修复后必须：
1. 板上验证目标功能
2. 检查日志无新增 error
3. 回归相关功能

### Phase 5：长跑验证

```bash
# 稳定性问题必须长跑
while true; do
  echo "$(date) rss=$(ps -o rss= -p <pid>)"
  sleep 300
done | tee /tmp/longrun.log
```

短时间正常不代表长时间稳定——**很多问题只在数小时后出现**。

---

## 「进程在但没反应」的排查

这类问题最耗时间，先用这三招：

```bash
cat /proc/<pid>/status | grep -E "^State|^TracerPid"
ps -ef | grep defunct          # 僵尸进程
cat /proc/<pid>/wchan          # 内核态阻塞在哪
```

- `TracerPid` 非 0 → 被 ptrace 冻结
- `State: T` → 被信号暂停
- `State: Z` → 僵尸，父进程没回收
- `wchan` 显示阻塞函数 → 内核态卡在某处

```bash
# 抓系统调用
strace -p <pid> -f
```

**不要一上来就重启服务**——重启会毁掉现场，先取证。

---

## 进程模型与 IPC

多进程架构下的问题常被误判为"程序崩了"，实际是**进程间通信阻塞**或**子进程没被回收**。

### 进程树与状态

```bash
ps -ef --forest# 进程树，看父子关系
ps -eo pid,ppid,stat,comm --sort=ppid # 按父进程排序
cat /proc/<pid>/status | grep -E "^State|^Threads|^FDSize"
ls /proc/<pid>/task                # 线程数
```

### 僵尸进程（子进程已退出，父进程未回收）

```bash
ps -ef | grep defunct              # 查僵尸
```

**根因**：父进程没有正确 `waitpid`。僵尸本身不占 CPU/内存，但**会占 PID**——大量僵尸会耗尽 PID 导致无法创建新进程。

```c
// 父进程必须回收子进程
while (waitpid(-1, &status, WNOHANG) > 0);   // 循环回收所有已退出子进程
```

### 管道与命名管道（FIFO）

```bash
# 创建命名管道
mkfifo /tmp/myfifo

# 写（注意：没有读端时 open 会阻塞）
echo "hello" > /tmp/myfifo

# 读
cat /tmp/myfifo

# 查看
ls -l /tmp/myfifo        # 'p' 类型即FIFO
```

**经典陷阱**：
- **FIFO 打开时阻塞**：写端 open 时若无读端，会一直阻塞 → 表现为"程序卡住不动"
- **数据不持久**：FIFO 缓冲有限，读端不读时写端会阻塞
- **EOF 处理**：读端读到写端全部关闭才算 EOF，否则会持续阻塞

```c
// 非阻塞打开，避免握手死锁
int fd = open("/tmp/myfifo", O_RDWR | O_NONBLOCK);   // O_RDWR 可避免单端打开阻塞

// 正确的 EOF 判定
ssize_t n = read(fd, buf, sizeof(buf));
if (n == 0) break;          // 真正的 EOF：所有写端都关了
if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK)) continue;
```

### 其他 IPC 手段

| 手段 | 特点 | 适用 |
|---|---|---|
| **pipe()** | 仅父子进程 | 父子通信 |
| **FIFO** | 有名，任意进程 | 无关进程间 |
| **socketpair** | 双向，全双工 | 父子双向通信 |
| **Unix Domain Socket** | 本地套接字 | 本地服务（最灵活） |
| **消息队列** | 内核管理 | 少量数据 |
| **共享内存** | 需配信号量 | 大块数据 |

```c
// Unix Domain Socket（推荐：支持双向、可多客户端）
int fd = socket(AF_UNIX, SOCK_STREAM, 0);
struct sockaddr_un addr = {.sun_family = AF_UNIX};
strcpy(addr.sun_path, "/tmp/my.sock");
bind(fd, (struct sockaddr*)&addr, sizeof(addr));
listen(fd, 5);
```

**共享内存的坑**：没有同步机制，**必须配信号量或互斥锁**，否则数据竞争难以复现。

### 进程卡死排查

```bash
# 进程在但不响应
cat /proc/<pid>/status | grep -E "^State|^TracerPid"
cat /proc/<pid>/wchan             # 内核态阻塞在哪
strace -p <pid>                   # 看系统调用卡在哪
ls -l /proc/<pid>/fd              # 有没有管道/fifo 卡住
```

**判断逻辑**：
- 阻塞在 `read` + fd 指向 FIFO → **对端没写或没读**，检查通信两端
- 阻塞在 `waitpid` → 子进程未回收
- 阻塞在 `write` + FIFO 缓冲满 → 对端消费慢

---

## 交叉编译与部署

```bash
make ARCH=arm64 CROSS_COMPILE=arm-linux-gnueabihf- -j$(nproc)
scp myapp root@<board>:/usr/bin/
ssh root@<board> "systemctl restart myapp"

# 确认版本生效
ssh root@<board> "myapp --version"
```

**要点**：部署后**确认固件版本确实更新**，避免调试的其实是旧版本——这是常见的假象来源。

---

## 长跑稳定性验证

```bash
# 采样关键指标到日志
while true; do
  echo "$(date) \
    rss=$(ps -o rss= -p <pid>) \
    cpu=$(top -bn1 -p <pid> | tail -1 | awk '{print $9}') \
    temp=$(cat /sys/class/thermal/thermal_zone0/temp) \
    load=$(cat /proc/loadavg)"
  sleep 300
done | tee /tmp/longrun.log
```

出问题时回看日志趋势，能定位**恶化起点**和**触发时刻**。

---

## 边界与注意

- **不要跳层排查**——上层没排除就动下层是无效劳动的主要来源
- **不要在没取证时重启服务**——会毁掉现场
- **假设一次一个**——同时改多个变量无法归因
- **短时间正常不等于稳定**——长跑才算数
- **修复后必须回归**——确认无副作用才算完成
- 实测数据用具体数字，不用「正常」「没问题」这类描述