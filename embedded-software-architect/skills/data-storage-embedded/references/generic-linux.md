# 通用 Linux 数据存储适配

> 不特定SoC 的通用存储实践。

## 存储介质识别

```bash
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT
blkid                      # 文件系统类型
cat /etc/fstab
```

## 存储健康监控

```bash
# SATA/USB
smartctl -a /dev/sda
smartctl -t short /dev/sda && smartctl -l selftest /dev/sda

# eMMC
cat /sys/block/mmcblk*/device/life_time

# NVMe
nvme smart-log /dev/nvme0
```

## 文件系统选择

| 文件系统 | 特点 | 适用 |
|---|---|---|
| **ext4** | 通用稳定 | 默认选择 |
| **f2fs** | 专为 flash 优化 | eMMC/SD 设备 |
| **btrfs** | CoW、快照 | 需要快照能力时 |

## 挂载选项（嵌入式）

```
noatime          # 减少写放大，延长 flash 寿命
discard          # SSD/eMMC 及时释放块
data=writeback   # 提升写入性能（断电风险增加）
```

## 持久化 vs 临时

```bash
mount | grep -E "tmpfs"
```

- **tmpfs 掉电丢失**，不能放需要持久化的数据
- 0 swap 设备上 tmpfs 会直接吃物理内存

## 边界

- 具体存储介质寿命特性查该介质手册
- 未确认介质类型前不要假设 SATA/M.2 等
- 数据一致性需实测验证，不能只看文档