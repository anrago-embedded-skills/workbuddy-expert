# PCIe / SATA / MIPI / RAID 参考

> 存储与硬件总线的通用排查方法。

## PCIe

```bash
# 枚举
lspci -nn
dmesg | grep -i pcie

# 链路状态与速率（关键）
lspci -vvv -s <dev> | grep -E "LnkSta|LnkCap"
```

**`LnkSta` 显示的实际速率**要与 `LnkCap` 对比——**降速运行是常见坑**（如 Gen3 设备跑在 Gen2 链路）。

| 字段 | 含义 |
|---|---|
| `Speed` | 当前协商速率 |
| `Width` | 当前协商宽度 |
| `LnkSta` | 实际状态 |
| `LnkCap` | 能力上限 |

**关键**：实际值低于能力值 = 链路协商受限（插槽、信号完整性、供电）。

## SATA / NVMe

```bash
lsblk -d
smartctl -a /dev/sda
nvme smart-log /dev/nvme0

# 性能实测（不要只看规格）
fio --name=seqwrite --filename=/dev/sdX --direct=1 --bs=1M --rw=write --size=1G
```

### AHCI 与 NVMe

| 特性 | SATA (AHCI) | NVMe (PCIe) |
|---|---|---|
| 协议 | SATA | PCIe + NVMe 协议 |
| 队列深度 | 有限 | 高（性能关键） |
| 驱动 | `ahci` | `nvme` |

**随机 IO 性能高度依赖队列深度**，NVMe 优势在此。

## RAID（mdadm）

```bash
cat /proc/mdstat
mdadm --detail /dev/md0
mdadm --stop /dev/md0

# 监控（写入 cron/看门狗）
mdadm --monitor --scan --daemonise
```

### 阵列对比

| 级别 | 最少盘 | 容量利用 | 容错 | 写性能 |
|---|---|---|---|---|
| RAID 0 | 2 | 100% | ❌ | 最好 |
| RAID 1 | 2 | 50% | 1 盘 | 读好 |
| RAID 5 | 3 | (N-1)/N | 1 盘 | 有写惩罚 |
| RAID 10 | 4 | 50% | 1 盘 | 好 |

### 关键注意

- **必须预留备盘**（rebuild 空间），否则重建失败
- **RAID 5 写惩罚**：小写入触发 read-modify-write，大幅降速
- **重建期性能显著下降**，避免高峰期大量 IO
- 嵌入式需做**阵列健康上报**（SMART + /proc/mdstat 状态）

## MIPI

### MIPI-CSI（摄像头）

```bash
media-ctl -p                # 看完整拓扑与 link
v4l2-ctl -d /dev/video0 --list-formats-ext
```

### MIPI-DSI（显示）

```bash
modetest -c                # 查 connector 与 mode
cat /sys/kernel/debug/dri/0/state
```

### 关键注意

- **lane 数与速率决定带宽**：计算 `lane × 速率` 是否够用
- **DSI 时序参数必须匹配面板**：错误会黑屏/花屏
- **CSI 多虚拟通道**：多摄像头时注意通道与带宽分配

## Docker 容器化

```bash
docker run -d --name app --restart always \
  -v /data/config:/app/config \
  --memory=512m --cpus=1.5 \
  myapp:latest

docker stats                # 实时资源
docker logs -f app
```

**关键**：嵌入式必须设 `--memory` / `--cpus`，否则容器吃光资源导致宿主 OOM。

## 边界

- PCIe 降速、RAID 重建降速都是隐蔽性能问题
- SMART/寿命需定期监控，不能等到坏了
- MIPI 时序错直接黑屏，先查面板参数
- Docker 资源限制必须设，这是嵌入式容器化的底线