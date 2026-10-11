# 通用 Linux 数据存储适配

> 仅在目标介质/文件系统或临时分区需要补充调查时读取。以下为 TARGET Linux；实际工具和 sysfs 属性依 rootfs、内核及介质驱动而异。

## 存储介质识别

```bash
# TARGET / read-only snapshots; requires util-linux/e2fsprogs tools as listed.
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT
blkid                      # 文件系统类型
cat /etc/fstab
```

预期分别给出块设备/挂载、签名和配置文件信息；工具缺失、权限拒绝或无输出只说明当前接口不可读，不能推出介质不存在或健康。

## 存储健康监控

```bash
# TARGET / read-only health snapshots; first confirm the device node/type.
: "${CONFIRMED_DEVICE:?set to the intended SATA/USB device}"
smartctl -a "$CONFIRMED_DEVICE"

# eMMC: attribute is driver-dependent and may not exist.
: "${CONFIRMED_MMC_DEVICE:?set to the confirmed mmc block name, e.g. mmcblk0}"
cat "/sys/block/$CONFIRMED_MMC_DEVICE/device/life_time"

# NVMe / requires nvme-cli and a confirmed namespace/controller.
: "${CONFIRMED_NVME_CONTROLLER:?set to the enumerated NVMe controller}"
nvme smart-log "$CONFIRMED_NVME_CONTROLLER"
```

缺少 health interface、权限或 SMART passthrough 时记录原因；无字段不是健康证明。`life_time` 是设备/驱动提供的估计值，须按介质手册解释。

`smartctl -t short` 启动设备自测，会增加设备 I/O 活动；只有确认准确盘符并允许自测时运行，完成后另行读取 self-test log。启动成功不表示自测通过。

```bash
# TARGET / starts an asynchronous device self-test; this changes device activity.
: "${CONFIRMED_DEVICE:?set to the intended device}"
smartctl -t short "$CONFIRMED_DEVICE"
```

## 文件系统选择

| 文件系统 | 特点 | 适用 |
|---|---|---|
| **ext4** | 通用稳定 | 默认选择 |
| **f2fs** | 专为 flash 优化 | eMMC/SD 设备 |
| **btrfs** | CoW、快照 | 需要快照能力时 |

## 挂载选项（嵌入式）

```text
# Configuration candidates only, not commands to paste into a live target.
noatime          # may reduce atime updates; check current relatime/default behavior
discard          # device/filesystem-specific discard behavior
data=writeback   # ext4 mode with different ordering/durability tradeoffs
```

Mount-option changes modify live/persistent filesystem behavior and can require remount or boot configuration changes. Compare the current mount options and exact kernel/filesystem documentation first; `data=writeback` is not a generic performance recommendation.

## 持久化 vs 临时

```bash
# TARGET / read-only; reports currently mounted tmpfs filesystems.
mount | grep -E "tmpfs"
swapon --show
grep -E "^(SwapTotal|SwapFree):" /proc/meminfo
```

The output shows active mounts and swap state only. No matching mount can mean the grep pattern missed a mount or it is not mounted; inspect `mount`/`findmnt` output where available. No swap entry does not make tmpfs persistent.

- **tmpfs 掉电丢失**，不能放需要持久化的数据
- 若目标设备的 `SwapTotal` 为 0，tmpfs 使用的页由内存管理器承担；先用 `swapon --show` 和 `/proc/meminfo` 检查实际配置，再评估资源余量

## 边界

- 具体存储介质寿命特性查该介质手册
- 未确认介质类型前不要假设 SATA/M.2 等
- 数据一致性需实测验证，不能只看文档
