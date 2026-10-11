# 生命周期与调用上下文

## 设备匹配、probe 与自动加载

先确认设备由哪个总线枚举，再确认驱动的匹配表。平台设备的 `.driver.name` 是驱动名称；Device Tree 设备通过 `.of_match_table` 中的 `compatible` 与驱动绑定。对于模块，`MODULE_DEVICE_TABLE(of, table)` 让构建工具从表生成设备 alias，供 udev/kmod 等用户态模块加载器匹配 modalias。该宏不代替 `.of_match_table`，静态编入内核的驱动也不依赖模块 alias。

无 probe 时逐项检查：运行树节点是否存在且启用、总线控制器是否已注册、设备是否被枚举、target compatible 是否匹配、驱动是否编入或加载、模块 alias 是否覆盖 modalias、probe 是否因资源未就绪而 defer。不要把所有问题归结为字符串不一致。

## 资源与失败路径

- 在 probe 中按需获取 MMIO、IRQ、时钟、复位、regulator、pinctrl、GPIO 和 DMA 资源；使用设备和子系统 API，保留 provider 的 errno。
- `devm_*` 将资源释放绑定到设备解绑和 probe 失败，可简化常规资源回收。它不替你验证返回值，也不会自动停止设备 DMA、取消任意工作、关闭已注册的上层接口或等待用户回调。
- 需要自定义清理时，根据目标内核 API 使用 `devm_add_action_or_reset()` 或显式错误标签。对于依赖顺序复杂的资源，明确注册/注销顺序，不依赖隐式 devres 栈顺序来完成硬件停机。
- probe 失败前应撤回已经注册的子设备、类设备或用户接口。若 provider 返回 `-EPROBE_DEFER`，尽早返回；在注册子设备后 defer 可能造成重复探测循环。
- 对资源依赖缺失使用 `dev_err_probe(dev, err, "...")`，避免把 defer 当普通错误重复打印，并保留可诊断的 defer reason。检查可用的 `devices_deferred` 调试信息。

## 解绑与异步执行者

remove 的核心是切断新的入口、停止硬件并等待已开始的执行完成。常见设计顺序是：

1. 注销新入口并停止所有 work/IRQ/DMA completion producer 的重新排队；用 removed/stopping 状态拒绝竞态中的新请求。
2. 禁止设备产生新的 IRQ/DMA 请求，并停止或复位硬件；按硬件手册确认 DMA 已停止或完成。
3. 同步 IRQ handler、线程化 IRQ、workqueue、timer、tasklet、kthread 或回调。使用对应的同步/取消 API；例如普通 work 使用 `cancel_work_sync()`，delayed work 使用 `cancel_delayed_work_sync()`。
4. 确认没有异步路径继续访问状态、MMIO、DMA buffer 或 subsystem 对象后，再让 managed 或手动资源释放。

具体设备可能需要不同顺序，例如先保留 IRQ 以接收 DMA 完成中断。根据硬件和回调依赖画出顺序，并在代码注释中说明关键竞态。同步等待 IRQ 或 work 前，不要持有这些回调获取的锁；否则可能死锁。先停掉会重新排队 work 的 producer，再调用同步取消。只调用 `devm_free_irq()`、释放 `devm_kzalloc()` 状态或返回 remove，不能替代异步路径同步。

注销字符设备或 cdev 只阻止新的 open；已有文件描述符仍可能调用 file operations。需要自定义字符设备时，为每个 open 对象设计引用计数或等效生命周期；解绑后让旧 fd 看到 removed 状态并拒绝硬件访问，且保证私有状态不会先于 fd 回调释放。不要让 remove 无限期等待所有进程关闭 fd。若设备对象使用 `devm_*`，不能让旧 fd 保留指向该对象的悬空指针。

## 锁、睡眠与共享状态

mutex、等待、可能睡眠的总线 I/O、用户态拷贝和 `GFP_KERNEL` 分配只能出现在可睡眠上下文。硬 IRQ 和持有 spinlock 的区域不能调用它们。硬中断中需要慢操作时，使用 threaded IRQ、workqueue 或 subsystem 提供的延后处理机制。

先确定共享状态的所有访问者，再选择 mutex、spinlock、原子、completion、RCU 或显式内存屏障。锁的中断禁用形式要与可能抢占该锁的上下文一致。锁应保护状态不变量和生命周期，而非仅抑制编译器优化。`volatile` 不是锁、原子或内存屏障；MMIO 也应通过 I/O accessor 访问。

启用 `CONFIG_PROVE_LOCKING`/lockdep 等目标可用检查，关注 IRQ 与进程上下文的锁顺序、remove 与异步回调的竞态，以及持锁进行可能睡眠的操作。

## API 版本

复制 callback 声明前先读目标树的头文件和相近驱动。上游 v6.10 的 `struct platform_driver` 中 `.remove` 返回 `int`，同时提供返回 `void` 的 `.remove_new`；上游 v6.11 起 `.remove` 返回 `void`。直接对照 [Linux v6.10 `platform_device.h`](https://github.com/torvalds/linux/blob/v6.10/include/linux/platform_device.h) 与 [Linux v6.11 `platform_device.h`](https://github.com/torvalds/linux/blob/v6.11/include/linux/platform_device.h)。厂商树可能回移植此改动，目标头文件优先于版本号。

## 主要资料

- [Driver binding 与 probe/remove](https://docs.kernel.org/driver-api/driver-model/driver.html)；[Platform devices and drivers](https://docs.kernel.org/driver-api/driver-model/platform.html)
- [模块设备表宏](https://github.com/torvalds/linux/blob/master/include/linux/module.h)；[OF 设备匹配结构](https://github.com/torvalds/linux/blob/master/include/linux/of.h)
- [Devres 管理资源](https://docs.kernel.org/driver-api/driver-model/devres.html)；[probe error helper](https://docs.kernel.org/driver-api/infrastructure.html)
- [Workqueue 与同步取消](https://docs.kernel.org/core-api/workqueue.html)；[通用 IRQ API](https://docs.kernel.org/core-api/genericirq.html)
- [锁类型及规则](https://docs.kernel.org/next/locking/locktypes.html)；[不要用 volatile 同步](https://docs.kernel.org/next/process/volatile-considered-harmful.html)
