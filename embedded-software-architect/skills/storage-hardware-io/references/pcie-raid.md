# PCIe / SATA / NVMe / RAID 参考

> 仅在 PCIe 链路协商、SATA/NVMe 健康检查、RAID 状态或有界普通文件基准需要补充步骤时加载。以下均为 TARGET Linux；工具/字段依内核和 rootfs 而异。该页不覆盖 MIPI 或应用运行时。

## PCIe

```bash
# TARGET / read-only; requires pciutils and access to kernel logs.
# 枚举
lspci -nn
dmesg | grep -i pcie

# 链路状态与速率（关键）
: "${PCI_ADDRESS:?set PCI_ADDRESS from lspci -nn}"
lspci -vvv -s "$PCI_ADDRESS" | grep -E "LnkSta|LnkCap"
```

预期 `LnkSta` 给出当前协商速率和宽度，`LnkCap` 给出该 function 的能力。字段缺失或读取失败可能是设备未枚举、权限/工具/配置差异；须比较 endpoint 与 root port，并核对该 SKU/插槽/BSP 规格。低于能力值表示链路存在限制的候选，不能单独归因于信号完整性或供电。

| 字段 | 含义 |
|---|---|
| `Speed` | 当前协商速率 |
| `Width` | 当前协商宽度 |
| `LnkSta` | 实际状态 |
| `LnkCap` | 能力上限 |

对比实际值与双方能力可以确定协商低于能力，但具体原因仍需原理图、供电/复位、启动日志及板级规格证据。

## SATA / NVMe

```bash
# TARGET / read-only health queries; identify the node from `lsblk` first.
lsblk -d
```

```bash
# TARGET / read-only SATA/USB SMART query; set a device confirmed by `lsblk`.
: "${CONFIRMED_SATA_DEVICE:?set to the intended SATA device}"
smartctl -a "$CONFIRMED_SATA_DEVICE"
```

```bash
# TARGET / read-only NVMe query; requires nvme-cli and an enumerated controller.
: "${CONFIRMED_NVME_CONTROLLER:?set to an enumerated NVMe controller}"
nvme smart-log "$CONFIRMED_NVME_CONTROLLER"
```

### 有界文件性能测试（可选）

以下是可选 TARGET shell 模板。仅向明确指定的 scratch 文件系统中的普通文件写最多 512 MiB；`runtime=30` 限制 I/O 阶段为 30 秒或直到 workload 完成，先到即停止。没有 `time_based`，不会重复写来填满时长；结束同步可能使总用时超过 30 秒。运行前核对目标挂载、至少 1 GiB 可用空间和设备当前负载；不要将块设备节点、系统盘或 RAID 成员作为 fio 文件名。要求 fio 版本支持这些选项。

```bash
(
  SCRATCH_DIR=/mnt/bench-scratch  # set to a verified scratch filesystem mount
  test -d "$SCRATCH_DIR" && test -w "$SCRATCH_DIR" || exit 1
  df -h "$SCRATCH_DIR"           # verify mount and >= 1 GiB free
  free -h
  FIO_FILE="$(mktemp "${SCRATCH_DIR%/}/fio-seqwrite.XXXXXX")" || exit 1
  trap 'rm -f -- "$FIO_FILE"' EXIT HUP INT TERM
  fio --name=seqwrite --filename="$FIO_FILE" --direct=1 --bs=1M \
    --rw=write --size=512M --io_size=512M --runtime=30 --end_fsync=1
  FIO_STATUS=$?
  exit "$FIO_STATUS"
)
```

预期输出包含写入量、I/O 阶段时长与结束同步结果；非零退出或 I/O 错误表示该测试配置/目标失败，仍需结合内核/介质/文件系统证据定层。测试只在新建普通文件中写入最多 512 MiB，I/O 阶段最长 30 秒，`end_fsync`/初始化/清理另计。没有 `time_based`，因此不重复填满时长。仅主机 fio 结果不等于目标设备结果。

### AHCI 与 NVMe

| 特性 | SATA (AHCI) | NVMe (PCIe) |
|---|---|---|
| 协议 | SATA | PCIe + NVMe 协议 |
| 队列深度 | 有限 | 高（性能关键） |
| 驱动 | `ahci` | `nvme` |

**随机 IO 性能高度依赖队列深度**，NVMe 优势在此。

## RAID（mdadm）

```bash
# TARGET / read-only md status queries.
: "${CONFIRMED_MD_DEVICE:?set to the intended md device}"
cat /proc/mdstat
mdadm --detail "$CONFIRMED_MD_DEVICE"
```

`mdadm --stop` 会改变阵列状态，不能用于查看状态。只有当已授权的维护范围明确要求停止已确认的阵列时，才按设备文档操作；先确认阵列成员、挂载点、swap 和使用者。

`mdadm --monitor --scan --daemonise` 会启动后台监控进程；只有在部署范围需要持续监控时，才将其纳入服务配置。

### 阵列对比

| 级别 | 最少盘 | 容量利用 | 容错 | 写性能 |
|---|---|---|---|---|
| RAID 0 | 2 | 100% | ❌ | 最好 |
| RAID 1 | 2 | 50% | 1 盘 | 读好 |
| RAID 5 | 3 | (N-1)/N | 1 盘 | 有写惩罚 |
| RAID 10 | 4 | 50% | 1 盘 | 好 |

### 关键注意

- 提前规划兼容的替换盘或热备盘；替换设备可用容量需满足阵列成员要求，是否可在线重建取决于阵列级别和配置
- **RAID 5 写惩罚**：小写入触发 read-modify-write，大幅降速
- **重建期性能显著下降**，避免高峰期大量 IO
- 嵌入式需做**阵列健康上报**（SMART + /proc/mdstat 状态）

## 边界

- PCIe 降速、RAID 重建降速都是隐蔽性能问题
- SMART/寿命需定期监控，不能等到坏了

## 主要参考

- fio documentation, `filename` and `size`: https://fio.readthedocs.io/en/latest/fio_doc.html
- `mdadm(8)` manual: https://man7.org/linux/man-pages/man8/mdadm.8.html
