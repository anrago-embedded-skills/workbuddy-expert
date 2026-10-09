---
name: storage-hardware-io
description: |
  Storage buses and hardware IO: RAID(mdadm), PCIe link negotiation, SATA/NVMe, MIPI DSI/CSI, Docker deployment, thread/async runtime, nginx.
  TRIGGER when: RAID、mdadm、/proc/mdstat、软raid、PCIe、pcie、lspci、LnkSta、SATA、AHCI、NVMe、smartctl、MIPI、MIPI-DSI、MIPI-CSI、lane、Docker、docker、容器化、镜像、多线程、线程绑核、taskset、chrt、优先级、异步、epoll、nginx、反向代理、worker_connections、盘挂了、阵列坏了、RAID 坏了、硬盘掉线、PCIe 不通、SATA 不识别、插不上、识别不了硬盘、容器起不来、docker 挂了、线程假死、事件循环卡、nginx 起不来、磁盘满了、硬盘满了、盘挂了、阵列坏了、RAID 挂了、硬盘掉线、docker起不来、容器起不来、容器挂了、docker 崩了、nginx 起不来、进程假死、RAID挂了、阵列降级、RAID重建、盘没认到、,
  DO NOT TRIGGER when: 内存/性能瓶颈定位（用 embedded-perf-debug）；Qt 渲染后端（用 display-compositor-gpu）,
---

# storage-hardware-io

> 存储与硬件 IO：RAID、PCIe、SATA、MIPI、Docker 容器化部署。平台适配见 `references/`。

## 适用范围

板级存储/总线扩展、大容量存储管理、容器化应用部署。

---

## PCIe

```bash
# 枚举设备
lspci -nn
dmesg | grep -i pcie

# 链路状态与速率
lspci -vvv -s <dev> | grep -E "LnkSta|LnkCap"

# BAR 空间
cat /sys/bus/pci/devices/*/resource
```

### 要点

- **链路速度需协商一致**：Gen3 x4 设备插在 Gen2 插槽上会降速运行
- **BAR 未分配** → 设备无法访问
- **中断分配**：MSI-X 配置不当会性能下降

---

## SATA / NVMe

```bash
# 设备与健康
lsblk
smartctl -a /dev/sda
smartctl -t short /dev/sda && smartctl -l selftest /dev/sda   # 短测自检

# 实际性能
fio --name=seqwrite --filename=/dev/sdX --direct=1 --bs=1M --rw=write
```

### 要点

- **AHCI 驱动**：`ahci` 模块，`libata` 栈
- **NCQ/队列深度**影响吞吐，随机 IO 更依赖队列深度
- **热插拔**需正确配置，嵌入式一般固定

---

## RAID

### 软 RAID（mdadm）

```bash
cat /proc/mdstat                      # 状态
mdadm --detail /dev/md0              # 详细信息
mdadm --stop /dev/md0
```

| 级别 | 最少盘数 | 特性 |
|---|---|---|
| RAID 0 | 2 | 条带，无冗余，性能优先 |
| RAID 1 | 2 | 镜像，可靠性优先 |
| RAID 5 | 3 | 单盘容错，写惩罚 |
| RAID 10 | 4 | 镜像+条带，性能与容错兼顾 |

### 要点

- **嵌入式需预留备盘**（rebuild 空间），否则重建会失败
- **RAID 5 写惩罚**：每次小写入触发读改写，性能受损
- **监控**：需定期 `mdadm --monitor` 或自研心跳上报
- **重建期性能显著下降**，避免大量 IO 叠加

---

## MIPI

MIPI 是移动设备芯片间高速接口，嵌入式主要用于 **MIPI-CSI（摄像头）** 和 **MIPI-DSI（显示）**。

```bash
# CSI 摄像头
media-ctl -p                        # 看 topology
v4l2-ctl -d /dev/video0 --list-formats-ext

# DSI 显示
modetest -c                        # 查 connector
```

### 要点

- **lane 数与速率决定带宽**：DSI 2-lane 跑 1080p60 需注意带宽上限
- **初始化时序严格**：panel 的时序参数必须匹配（`drm_edid` 或 panel 节点）
- **CSI 多虚拟通道**：可接多摄像头，注意通道分配

---

## Docker 容器化

### 嵌入式可用性

```bash
docker run -d --name app --restart always \
  -v /data/config:/app/config \
  --memory=512m --cpus=1.5 \
  myapp:latest

# 资源限制（嵌入式关键：防止容器吃光资源）
docker stats
docker logs app
```

### 要点

- **必须设资源限制**（`--memory` / `--cpus`），否则容器会吃光设备资源
- **`--restart always`**：容器化应用需自恢复
- **存储驱动**：overlay2 有 layer，开销大；嵌入式可能用 `vfs`（慢但简单）
- **镜像瘦身**：嵌入式镜像要小，避免拉取慢与占空间
- **Docker 在 0 swap 设备上**，内存限制不能超物理内存太多

---

## 多线程与异步

### 嵌入式线程设计

- **CPU 亲和性**：绑核避免调度抖动（`taskset` / `sched_setaffinity`）
- **线程优先级**：实时线程 `SCHED_FIFO`（需 `CAP_SYS_NICE`）
- **避免过度订阅**：线程数 > 核数会引入切换开销
- **锁粒度**：粗锁串行化，细锁增加竞争，需平衡

```bash
taskset -c 2,3 ./app          # 绑到CPU 2-3
chrt -f 80./app               # 实时优先级
```

### 异步 IO

- **epoll**：多 fd 高并发标准方案
- **回调地狱**：嵌入式推荐事件驱动模型
- **注意**：异步 IO 与多线程混用容易出竞态，选一种为主

---

## nginx

### 嵌入式部署

```nginx
server {
    listen80;
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

### 要点

- **worker 数量**不要超过核数太多，嵌入式内存有限
- **`worker_connections`** 与文件描述符上限匹配（`ulimit -n`）
- **静态资源缓存**可减少磁盘 IO

```bash
nginx -t                # 配置检查
nginx -s reload         # 热加载
```

---

## 边界与注意

- **Docker 必须设资源限制**，否则容器吃光内存导致宿主OOM
- RAID 重建期性能下降明显，避免高峰期操作
- **MIPI 时序参数必须匹配面板**，错了可能黑屏或花屏
- PCIe 链路降速是常见坑，要确认实际协商速率
- 多线程绑核可降低抖动，但不等于提升吞吐
- 嵌入式用 nginx 要注意 worker 数与 fd 上限匹配