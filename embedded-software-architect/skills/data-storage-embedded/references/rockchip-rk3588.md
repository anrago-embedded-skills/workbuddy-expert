# RK3588 数据存储适配

> RK3588 板卡存储介质与平台特性。

## 存储介质

| 类型 | 常见用途 | 注意事项 |
|---|---|---|
| **eMMC** | 系统盘 + 数据盘 | 有**寿命**，需监控 |
| **SD卡** | 可插拔存储 | 掉电易损，写寿命较短 |
| **NVMe (PCIe)** | 高性能存储 | 需 PCIe 支持 + 驱动 |
| **SATA** | 大容量 | RK3588 部分型号支持 |

## eMMC 寿命监控（重点）

```bash
# 寿命百分比（剩余寿命）
cat /sys/block/mmcblk0/device/life_time
# 0x01=≥90%剩余，0x0b≈接近寿命末期

# 更详细
mmc extcsd read /dev/mmcblk0 | grep -i lifetime
```

**关键**：eMMC 接近寿命末期会出现**随机坏块**，导致数据静默损坏。长跑设备必须监控此指标。

## CMA 与 DMA 内存

```bash
grep -E "CmaTotal|CmaFree" /proc/meminfo
cat /proc/maps | grep -i cma
```

**RK3588 特有**：摄像头/GPU 需大块连续内存，CMA 不足时会出现「有内存却分配失败」。

## 文件系统

```bash
df -h
mount | grep -E "ext4|f2fs"

# 挂载选项建议（嵌入式）
# noatime    减少写放大，延长存储寿命
# data=writeback  提升写入性能（但断电风险）

# 检查文件系统错误
dmesg | grep -i "ext4\|error\|remount"
```

## SQLite 部署注意

- 数据库放**持久化分区**，不要放 tmpfs
- WAL 模式的 `-shm` 文件放非 tmpfs
- 高频写入攒批，不要每条都commit

```bash
sqlite3 /data/app.db "PRAGMA journal_mode; PRAGMA integrity_check;"
```

## Redis 注意

- 设 `maxmemory` 上限，**0 swap 设备上不设会触发 OOM 连锁**
- 必须开持久化（AOF/RDB），否则重启全丢
- 监控 `used_memory_human`

## 边界

- eMMC life_time 接近 0x0b 时应预警更换
- 具体存储配置依板卡设计，确认实际介质类型
- 未验证的推断需标注