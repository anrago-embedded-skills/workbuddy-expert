# 案例：复用 streaming DMA buffer 时 CPU 读到旧数据

> **合成教学夹具**：错误现象、地址、日志和代码均为人工构造的教学材料，不是实机历史，也不代表目标 DMA/IOMMU 配置经过验证。

## 输入

```text
[SYNTHETIC REPORT] a persistent RX buffer is reused; CPU occasionally parses the previous packet
[SYNTHETIC CODE REVIEW] dma_map_single(..., DMA_FROM_DEVICE) happens once; hardware completes repeatedly; CPU reads after completion and reposts the same mapped range without dma_sync_* calls
[SYNTHETIC LOG] DMA API debug is unavailable in this target config
```

这条路径表示一种候选缺陷，需先确认实际 map/unmap 与 completion 生命周期。一次性 map 后完成并 unmap 的驱动，与持久映射反复交接的驱动需要的同步点不同。

## 竞争假设与区分证据

| 假设 | 需要的证据 | 如何区分 |
|---|---|---|
| streaming buffer 仍由设备拥有时 CPU 读取 | 为每个 buffer 记录 map、提交、完成、CPU 访问、重新提交、unmap 顺序；确认 mapping direction | 持久映射重复使用且缺所有权交接时，优先按 DMA API 检查 |
| map 错误或设备 DMA 地址错误 | `dma_mapping_error()` 检查、实际提交给硬件的 `dma_addr_t`、DMA mask/IOMMU map 信息 | 缓存同步不能修复错误地址或超出设备能力 |
| descriptor/doorbell 排序错误或设备覆盖越界 | 硬件协议、descriptor 字段、长度/边界、完成状态与 doorbell 顺序 | coherency 与 DMA memory barrier 是不同问题 |
| 设备/IRQ completion 过早或 buffer 生命周期已释放 | completion 来源、队列所有权、timeout/reset 和 unbind 时 DMA stop 证据 | completion 与真实设备静止不一致时不能仅补 sync |

DMA API debug、IOMMU 日志或硬件 trace 可帮助定位，但没有报告不等于没有问题。CPU physical address 与设备 DMA address 也不能互换。

## 最小修复片段和适用条件

若确认是一个**持久 streaming 映射**、硬件已完成 RX、CPU 需要读取且随后要把同一 buffer 交还设备，按映射方向调用 DMA API 做所有权转换：

```c
/* [SYNTHETIC FRAGMENT] 仅用于已映射且刚完成的 DMA_FROM_DEVICE buffer。 */
dma_sync_single_for_cpu(dev, dma_addr, len, DMA_FROM_DEVICE);
consume_rx_bytes(cpu_addr, len); /* 占位：CPU 访问只在 CPU 拥有期间 */
dma_sync_single_for_device(dev, dma_addr, len, DMA_FROM_DEVICE);
submit_rx_buffer_to_device(dma_addr, len); /* 占位：交回设备后 CPU 不得访问 */
```

这些 sync 必须与目标树 DMA API 的映射、方向、完成时序和 buffer 生命周期匹配。若每次传输都在完成后正确 unmap，不能机械地再加 sync；若 buffer 会被 CPU 修改或由设备双向修改，先重新评估方向和 API。DMA coherency 也不替代 descriptor/doorbell 所需的硬件协议顺序。

## 预期证据与回归

预期：每个 buffer 的 CPU 与设备访问区间不重叠；map/unmap 成对且只在硬件停止使用地址后 unmap；映射失败已检查；DMA direction 与实际数据流一致。回归覆盖重复 RX/TX、不同长度/对齐、queue 满和中断、map 失败、timeout/reset、unbind 和可用的非一致性/IOMMU 测试配置。用包序号/CRC 等端到端数据判据检查陈旧/损坏数据，并记录实际启用的目标调试配置。

本案例没有目标源码、工具链或硬件，因此没有模块编译、DMA 运行或板测结果。依据：[DMA API HOWTO 的 streaming mapping 与 sync 规则](https://docs.kernel.org/core-api/dma-api-howto.html)、[DMA API](https://docs.kernel.org/core-api/dma-api.html)、[DMA 与内存屏障](https://docs.kernel.org/core-api/wrappers/memory-barriers.html)。
