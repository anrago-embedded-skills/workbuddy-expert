# RK3588 数据存储适配

> 仅在目标确认为 RK3588 且板卡/SDK 型号已识别时读取。实际介质、接口、内核驱动和工具由板卡设计、BSP 与 rootfs 决定；SoC 名称不能确认这些能力。

## 存储介质

| 类型 | 常见用途 | 注意事项 |
|---|---|---|
| **eMMC** | 系统盘 + 数据盘 | 有**寿命**，需监控 |
| **SD 卡** | 可插拔存储 | 可移除性、控制器/卡规格和写入负载需核对 |
| **NVMe (PCIe)** | 按板级 PCIe 布线与供电配置 | 需实际 root port、链路和驱动支持 |
| **SATA** | 仅在板级设计接出并有对应控制器时 | 以原理图/BSP 和枚举结果核实 |

## eMMC 寿命监控（重点）

```bash
# TARGET / read-only. Attribute may not be exported by this kernel/driver.
cat /sys/block/mmcblk0/device/life_time

# TARGET / mmc-utils read-only query; confirm the eMMC device node first.
mmc extcsd read /dev/mmcblk0
```

若读取成功，使用 `mmc-utils` 实际版本和确切 eMMC datasheet 解读 Extended CSD life-time estimate 字段。字段是设备报告的粗粒度估计，不是剩余运行时间或坏块预测；属性/命令缺失表示接口不可用，不是健康证明。

## CMA 与 DMA 内存

```bash
# TARGET / read-only status checks; CMA visibility depends on kernel configuration.
grep -E "CmaTotal|CmaFree" /proc/meminfo
```

CMA 与数据持久化无关；若失败日志明确涉及 CMA，改从目标 kernel/BSP 与实际驱动分配记录调查。只有 `/proc/meminfo` 中存在对应字段才可比较值；字段缺失需查目标配置。

## 文件系统

```bash
# TARGET / read-only snapshots. Use `df` and `findmnt` if installed; `mount` output is authoritative for the active mount.
df -h
mount | grep -E "ext4|f2fs"

# Configuration candidates only. A mount-option change alters filesystem behavior.
# Compare actual kernel/filesystem docs and current options before changing.
# noatime may reduce atime updates; data=writeback changes ordering/durability tradeoffs.

# 检查文件系统错误
dmesg | grep -i "ext4\|error\|remount"
```

预期是当前剩余空间、活动挂载选项和 ring-buffer 中保留的文件系统消息；无匹配输出仅表示采样范围里未找到文本，不能证明无故障。`dmesg` 读取可能被权限策略限制。

## SQLite 部署注意

- 数据库放**持久化分区**，不要放 tmpfs
- SQLite WAL 的 `-shm` 是可重建的 wal-index；`-wal` 可能含未 checkpoint 的已提交事务，数据库运行中不要手动删除，并在复制/迁移打开的数据库时同时保留 `-wal`
- 高频写入攒批，不要每条都commit

```bash
# TARGET / read-only SQL against the confirmed database, subject to concurrent-use policy.
sqlite3 /data/app.db "PRAGMA journal_mode; PRAGMA integrity_check;"
```

预期返回实际 journal mode 和 `integrity_check` 的 `ok`；数据库锁/权限/路径问题会失败或返回其他输出。结构检查成功不证明最近提交已耐久；恢复期间不要删改 WAL/SHM。

## Redis 注意

- 通过运行时检查确认可用内存、cgroup 限额和 Redis 工作集；按部署配置设置 `maxmemory` 与淘汰策略，不要假设板卡没有 swap
- 持久化由 Redis 配置决定；检查实际 RDB/AOF 设置和同步策略，按掉电/重启后的数据恢复要求配置
- 监控 `used_memory_human`

## 边界

- eMMC life-time 字段越过设备规格类别上限时，按产品策略做健康评估，不据此预测精确失效时间
- 具体存储配置依板卡设计，确认实际介质类型
- 未验证的推断需标注
