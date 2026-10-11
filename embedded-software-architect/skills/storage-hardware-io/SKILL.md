---
name: storage-hardware-io
description: |
  主技能：PCIe/SATA/NVMe/RAID 与块设备的枚举、链路协商、健康状态和有界文件基准。MIPI 媒体链路归媒体技能；Docker、线程或 nginx 应用运行时归通用调试技能。
---

# storage-hardware-io

> PCIe/SATA/NVMe/RAID 与块设备排查。平台适配和补充方法见按需读取的 `references/`。

## 适用范围

板级存储/PCIe 总线扩展、块设备发现与健康检查、RAID 管理和有界文件性能诊断。

## 主技能选择与分流

当任务需要枚举 PCIe/SATA/NVMe/块设备，检查链路协商、SMART/NVMe 健康或 RAID 状态，或执行经确认的有界普通文件基准时，选择本技能。SQLite/WAL 增长、文件持久化、卷接近写满或应用写入路径问题从 [data-storage-embedded](../data-storage-embedded/SKILL.md) 开始；只有证据显示块设备发现、健康或 I/O 故障时才用本技能。容器内存耗尽或 CPU/内存压力转到 [embedded-perf-debug](../embedded-perf-debug/SKILL.md)；Docker 部署、nginx、POSIX 线程或 epoll 应用问题从 [embedded-debug-workflow](../embedded-debug-workflow/SKILL.md) 开始；MIPI-CSI/DSI 媒体链路从 [media-pipeline-linux](../media-pipeline-linux/SKILL.md) 开始。内核 IRQ/workqueue/驱动锁证据转到 [linux-device-drivers](../linux-device-drivers/SKILL.md)。

## 任务输入、证据分支与交付

记录目标设备/内核、介质准确型号与总线、设备节点和分区、拓扑/阵列状态、运行时 I/O 错误、挂载点/文件系统、当前业务负载和采样窗口。PCIe 先取得两端能力与当前协商状态；SMART/NVMe 读数按介质型号解释；fio 只能从明确选定的 scratch 文件系统开始。

| 证据 | 主查分支 |
|---|---|
| 设备未枚举、链接 down 或协商低于预期 | 对齐 PCIe root port/endpoint 能力、`dmesg` 和 sysfs 设备关系；检查设备树/BSP/供电时再转驱动/BSP |
| 块设备可见但出现 EIO、超时或介质错误计数变化 | 按 SATA/NVMe/eMMC 驱动接口和介质手册查健康日志、错误计数、固件/温度/链路；文件持久化语义由 [data-storage-embedded](../data-storage-embedded/SKILL.md) 分析 |
| RAID 降级、重建或 md 设备 I/O 异常 | 采集 `/proc/mdstat` 与 `mdadm --detail`、成员状态和当前重建阶段；状态命令不自动启动/停止阵列 |
| 应用写入或数据库恢复异常但块层无错误 | 返回应用数据路径，不以一次 fio 吞吐测试诊断 SQLite/文件系统耐久性 |

交付拓扑、设备与内核版本、只读状态采样、证据支持的最小变更、如执行 fio 则记录完整配置/返回码/I/O 字节数/结束同步时间，以及重复负载下的验收。跨领域记录和验证层级按需引用 [工程工作流](../embedded-debug-workflow/references/engineering-workflow.md) 与 [验证策略](../embedded-debug-workflow/references/validation-policy.md)。

## 命令环境

下列设备命令默认在 **TARGET Linux**，并要求相应工具、设备节点权限和内核接口。`<...>` 是模板，先从实际枚举结果替换。`lspci`/`lsblk`/SMART 日志读取及 `mdadm --detail` 是状态检查；`smartctl -t short` 会启动设备自测；fio 会向普通 scratch 文件写数据。写测前核对挂载、空闲空间、当前负载和产品允许的写入量。

---

## PCIe

```bash
# TARGET / read-only; requires pciutils and permission to read kernel logs.
lspci -nn
dmesg | grep -i pcie

# 链路状态与速率
: "${PCI_ADDRESS:?set PCI_ADDRESS from lspci -nn}"
lspci -vvv -s "$PCI_ADDRESS" | grep -E "LnkSta|LnkCap"

# BAR 空间
cat /sys/bus/pci/devices/*/resource
```

Expected `LnkSta` gives negotiated speed/width and `LnkCap` the function's capabilities. Compare endpoint and root port plus board specifications; missing device/fields or permission errors mean current tooling/target does not expose the needed evidence. A lower negotiated value is a restriction candidate, not proof of a particular electrical cause.

### 要点

- **链路速度需协商一致**：Gen3 x4 设备插在 Gen2 插槽上会降速运行
- **BAR 未分配** → 设备无法访问
- **中断分配**：MSI-X 配置不当会性能下降

---

## SATA / NVMe

```bash
# TARGET / read-only inventory; identify actual device type and node.
lsblk
```

```bash
# TARGET / read-only SATA/USB SMART query; replace after `lsblk`.
: "${CONFIRMED_SATA_DEVICE:?set to a SATA device confirmed by lsblk}"
smartctl -a "$CONFIRMED_SATA_DEVICE"
```

```bash
# TARGET / read-only NVMe query; requires nvme-cli and an enumerated controller.
: "${CONFIRMED_NVME_CONTROLLER:?set to a confirmed NVMe controller}"
nvme smart-log "$CONFIRMED_NVME_CONTROLLER"
```

预期输出实际设备识别信息和可用健康字段；设备未识别、权限不足、工具不支持或 SMART 被桥接/固件屏蔽时记录限制，不能把没有 SMART 数据解释为健康。短测会在设备上启动异步自检并产生 I/O 活动，只能按准确设备手册在允许的维护时段运行；之后再读 self-test log，启动成功不等于测试通过。

```bash
# TARGET / starts a device self-test; stateful and may add I/O load.
: "${CONFIRMED_DEVICE:?set to the device confirmed from enumeration}"
smartctl -t short "$CONFIRMED_DEVICE"
```

### 可选的有界文件性能测试

以下是可选 **TARGET shell 脚本模板**：测试只向普通文件写入最多 512 MiB，并限制 I/O 阶段为 30 秒（fio 完成 workload 或 runtime 到期即停止）；没有 `time_based`，因此不会为填满 30 秒而重复写。结束 `fsync` 可能使总用时超过 30 秒。只在确认至少 1 GiB 空闲的 scratch 挂载点运行；不要把块设备节点、系统盘或 RAID 成员作为 `filename`。测试会消耗写入量并影响正在运行的服务。先检查 `fio --version` 和目标 fio `--help`，确认所装版本支持这些选项。

```bash
(
  SCRATCH_DIR=/mnt/bench-scratch  # set to an explicitly selected scratch mount
  test -d "$SCRATCH_DIR" && test -w "$SCRATCH_DIR" || exit 1
  df -h "$SCRATCH_DIR"           # confirm mount and >= 1 GiB free
  free -h                         # inspect current resource headroom
  FIO_FILE="$(mktemp "${SCRATCH_DIR%/}/fio-seqwrite.XXXXXX")" || exit 1
  trap 'rm -f -- "$FIO_FILE"' EXIT HUP INT TERM
  fio --name=seqwrite --filename="$FIO_FILE" --direct=1 --bs=1M \
    --rw=write --size=512M --io_size=512M --runtime=30 --end_fsync=1
  FIO_STATUS=$?
  exit "$FIO_STATUS"              # preserve fio status; test file is removed on exit
)
```

预期 fio 报告实际写入量、时长和结束同步；I/O 阶段最多 512 MiB 且 runtime 最长 30 秒，初始化/清理和结束同步另计。非零退出、`ENOSPC`、`EIO` 或 direct-I/O 不支持需原样记录；它们说明该配置/目标 workload 失败，不能单独定位为 PCIe、介质或文件系统根因。不要把运行主机的结果作为 TARGET 验证。

### 要点

- **AHCI 驱动**：`ahci` 模块，`libata` 栈
- **NCQ/队列深度**影响吞吐，随机 IO 更依赖队列深度
- **热插拔**需正确配置，嵌入式一般固定

---

## RAID

### 软 RAID（mdadm）

```bash
# TARGET / read-only. Confirm this is the intended md device from `/proc/mdstat`.
: "${CONFIRMED_MD_DEVICE:?set to the intended md device}"
cat /proc/mdstat                      # 状态
mdadm --detail "$CONFIRMED_MD_DEVICE" # 详细信息
```

预期输出包括成员、阵列状态和恢复/重同步进度；若状态与成员信息不一致，保留两份输出并先排查。命令失败表示工具/权限/设备不符，不应自动启动或停止阵列。

`mdadm --stop` 会停止阵列，是状态变更操作，不属于状态查询。只有当当前维护范围确实要求停止某个已确认的阵列时，才根据 `mdadm` 文档执行；先确认阵列成员、挂载点、swap 和实际使用者，再使用核实过的阵列设备名。

| 级别 | 最少盘数 | 特性 |
|---|---|---|
| RAID 0 | 2 | 条带，无冗余，性能优先 |
| RAID 1 | 2 | 镜像，可靠性优先 |
| RAID 5 | 3 | 单盘容错，写惩罚 |
| RAID 10 | 4 | 镜像+条带，性能与容错兼顾 |

### 要点

- 提前规划兼容的替换盘或热备盘；替换设备可用容量需满足阵列成员要求，是否可在线重建取决于阵列级别和配置
- **RAID 5 写惩罚**：每次小写入触发读改写，性能受损
- **监控**：阵列健康上报属于部署服务；`mdadm --monitor` 会启动持续监控（可能依配置后台运行），不是状态查询。仅在确认通知/服务配置和阵列范围后部署，并检查目标 `mdadm` 版本手册。
- **重建期性能显著下降**，避免大量 IO 叠加

---

## 边界与注意

- RAID 重建期性能下降明显，避免高峰期操作
- PCIe 链路降速是常见坑，要确认实际协商速率

## 主要参考

- [pcie-raid.md](references/pcie-raid.md) — PCIe 链路、SATA/NVMe 健康与 RAID 状态需要补充细节时读取；该文含可选的有界普通文件基准。
- fio documentation, `filename`, `size`, and bounded file I/O: https://fio.readthedocs.io/en/latest/fio_doc.html
- `mdadm(8)` manual, including the state-changing `--stop` operation: https://man7.org/linux/man-pages/man8/mdadm.8.html
