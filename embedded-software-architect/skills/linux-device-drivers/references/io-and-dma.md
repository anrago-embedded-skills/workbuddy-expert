# IO、regmap 与 DMA 所有权

## MMIO 与寄存器映射

用平台资源 API 请求并映射 `reg` 资源，例如 `devm_platform_ioremap_resource()`；PCI、I2C、SPI 等总线应使用各自的资源 API。把返回值当作 `__iomem` token，只通过适当的 `readl()`/`writel()`、`ioread*()`/`iowrite*()` 或相应 subsystem API 访问。不要直接解引用 `__iomem` 指针，不要将物理地址强制转换成指针，也不要用 `volatile` 替代 accessor。

寄存器宽度、端序、读写副作用、写入排序、read-modify-write 是否安全，都必须来自目标芯片手册和目标架构。使用 relaxed/raw accessor、`ioremap_wc()` 或直接缓存映射前，必须证明目标硬件允许相应的排序和访问方式。寄存器具有字段、缓存、共享访问或多种总线前端时，先评估 regmap，避免手写不同总线的重复逻辑。

## DMA、IOMMU 与缓存

CPU 虚拟地址、CPU 物理地址和设备 DMA 地址是不同地址空间。把 buffer 交给设备前，用 Linux DMA API 建立映射；IOMMU 可以把 DMA 地址映射到物理页，但驱动不能自行假设二者相等。按设备能力设置 DMA mask，并分别判断 coherent allocation 与 streaming mapping 是否符合硬件协议。

- coherent buffer 可被 CPU 与设备并行观察，但仍可能需要内存屏障来发布 descriptor 字段和 valid bit。
- streaming buffer 在 CPU 与设备之间转换所有权。按 `dma_map_*`、`dma_unmap_*` 与 `dma_sync_*_for_cpu/device` 的方向和生命周期执行；非一致性缓存维护交给 DMA API。
- descriptor、payload 与 doorbell 的排序须依据目标硬件协议。DMA coherency 不代表 CPU 对普通内存、MMIO 或 descriptor 字段自动按所需顺序写入。
- 不能把栈、`vmalloc()` 返回地址或未通过 DMA API 准备的任意内存直接交给设备。检查映射返回值，并保证卸载前硬件不再 DMA 到 buffer。
- 不手动 flush/invalidate CPU cache 来“修复”DMA，除非该设备/架构 API 明确要求专用路径。错误的 cache 操作会破坏其他 CPU 或设备的数据。

跨驱动或跨子系统共享图像、视频或加速 buffer 时，先检查 DMA-BUF、DMA fence 与 reservation object；这套接口负责导入/导出、映射及异步访问同步。不要自行把物理地址放进 ioctl 当作通用共享 ABI。

## 调试原则

对 DMA fault 先收集设备的 DMA mask、IOMMU domain/map 日志、DMA API debug 信息、descriptor 内容和缓冲区生命周期。区分“映射失败”“设备使用了错误 DMA 地址”“设备越界写”“缓存/顺序错误”和“设备解绑后仍 DMA”；不要仅依据物理内存是否连续下结论。

长时间验证至少覆盖反复提交与完成、错误恢复、超时/复位、并发 CPU 访问、映射失败路径和解绑期间的 DMA 停止。对共享 buffer 检查 CPU 与设备所有权转换、fence 等待与 buffer 释放顺序。

## 主要资料

- [Linux device I/O 与 MMIO accessor](https://docs.kernel.org/driver-api/device-io.html)
- [Regmap header and implementation](https://github.com/torvalds/linux/blob/master/include/linux/regmap.h)；[regmap source directory](https://github.com/torvalds/linux/tree/master/drivers/base/regmap)
- [DMA API HOWTO](https://docs.kernel.org/core-api/dma-api-howto.html)；[DMA API](https://docs.kernel.org/core-api/dma-api.html)；[DMA attributes](https://docs.kernel.org/core-api/dma-attributes.html)
- [IOMMU API header](https://github.com/torvalds/linux/blob/master/include/linux/iommu.h)；[IOMMU device-tree binding](https://github.com/torvalds/linux/blob/master/Documentation/devicetree/bindings/iommu/iommu.txt)
- [DMA-BUF、fence 与共享 buffer](https://docs.kernel.org/driver-api/dma-buf.html)
- [内存屏障](https://docs.kernel.org/core-api/wrappers/memory-barriers.html)
