---
name: linux-device-drivers
description: |
  用于实现、移植或排查 Linux 内核设备驱动源码，包括设备匹配、probe/remove、资源清理、中断与异步生命周期、DMA 和电源管理。
---

# Linux device drivers

本技能用于 Linux 内核设备驱动开发、移植和故障排查。先确认目标内核源码与版本、厂商补丁、设备绑定文档、硬件接口和构建配置；内核内部 API 会变化，目标源码树和头文件是最终依据。

## 任务工作流

目标是以目标内核和 binding 为依据，交付最小驱动改动及其可重复验证方法。最低输入为预期设备行为、总线/硬件身份、运行时节点或枚举证据、目标内核源码/config、现有驱动与失败日志；缺少具体板卡或 SDK 时仍可审查已有源码和设计，但寄存器、资源和回调签名要保留为待目标资料确认项。区分未枚举、无匹配、驱动未加载、probe 失败/defer、已绑定后的运行故障和卸载竞态，再以针对性证据排除候选原因。任务结束给出最小 patch、目标 Kbuild 命令模板、构建/运行验证计划、结果与未验证范围。详见[驱动任务工作流](references/task-workflow.md)。

通用的任务输入、命令和交付约定见[通用工程工作流](../embedded-debug-workflow/references/engineering-workflow.md)；资料依据与验证记录见[验证策略](../embedded-debug-workflow/references/validation-policy.md)。

## 主用与配合

本技能主用于驱动源码、总线/设备匹配、probe/remove、错误回滚、并发和资源生命周期。目标机是否启动了对应内核、运行时设备节点是否存在，配合 [embedded-bsp-kernel](../embedded-bsp-kernel/SKILL.md) 核实；板级总线、引脚、供电及设备树资源配置，配合 [embedded-peripherals](../embedded-peripherals/SKILL.md) 核实。

## 先选择内核子系统

查找现有驱动、Device Tree binding 和子系统 API。硬件已有标准子系统接口时，沿用该接口；只有设备行为没有合适的子系统时，才设计自定义字符设备或 ioctl。

| 设备功能 | 优先评估 |
|---|---|
| 按键或开关 | input |
| LED 或背光 | LED / backlight |
| 传感器、ADC、测量值 | IIO |
| 温度、风扇、功耗遥测 | hwmon |
| 摄像头、视频采集 | V4L2 |
| 显示控制器 | DRM/KMS |
| 音频设备 | ALSA/ASoC |
| 串口设备 | TTY/serial |
| 其他符合现有接口的总线或设备 | 对应内核子系统 |

若确需新用户接口，先写清 ABI 的数据格式、错误码、并发规则、设备卸载后的行为和兼容策略。注销字符设备只阻止新的 open；已有 fd 可能继续调用回调，私有状态的生命周期必须覆盖这些回调。不要把 sysfs 当作任意 RPC 通道；只公开适合属性模型的简单状态或配置。

## 设计与实现

1. 从数据手册、板级原理图、设备树 binding 和目标源码确认资源、时钟、电源、复位、DMA 能力及中断触发方式。硬件未知时保留明确占位，不编造寄存器地址或位定义。
2. 确认总线和匹配方式。Device Tree 驱动需要 `.of_match_table`；可加载模块还需要 `MODULE_DEVICE_TABLE(of, ...)` 导出用户态自动加载所需的 modalias。二者解决不同问题。
3. 列出 probe 期间获得的每项资源、对外注册的接口、IRQ/work/timer/thread 等异步执行者，以及 remove 时如何停止和等待它们。
4. 每个错误路径都返回真实 errno，并释放已取得的资源。资源管理的 `devm_*` 只负责资源释放，不会自动停止任意硬件 DMA、用户回调或自建异步工作。
5. 依据调用上下文选择同步方式。硬 IRQ/持有 spinlock 的路径不能睡眠；可睡眠操作放在线程化 IRQ 或工作队列。共享状态使用合适的锁、原子、完成量或内存屏障，不用 `volatile` 代替同步。
6. 使用内核资源和子系统 API 访问硬件。实现或排查 MMIO、regmap、DMA/IOMMU、缓存所有权或 DMA-BUF 时，读取 [IO 与 DMA](references/io-and-dma.md)。
7. 实现时钟、复位、电源、pinctrl、runtime PM 或 system sleep 时，按设备依赖和子系统顺序处理；读取 [电源、子系统与验证](references/power-subsystems-validation.md)。

探测依赖尚未就绪时，尽早传播 provider 返回的 `-EPROBE_DEFER`；不要先注册子设备或对用户开放接口再 defer。先检查目标树 `include/linux/device.h` 是否声明 `dev_err_probe()`：存在时可用它记录 probe 上下文并保留 deferred reason；旧 BSP 若没有此 API，则使用目标树支持的日志函数并原样返回 errno，不能吞掉或改写 `-EPROBE_DEFER`。不要只按版本号推断 API 存在与否，因为厂商树可能回移植接口。实现或审查 probe/remove 回滚、IRQ/work/timer/thread 停止顺序和调用上下文时，读取 [生命周期与并发](references/lifecycle-and-context.md)。

需要区分预期 defer 与永久资源错误时，读[probe defer 案例](references/cases/probe-defer.md)；卸载等待异步工作时读[异步 teardown 死锁案例](references/cases/async-teardown-deadlock.md)；streaming buffer 数据不一致时读[DMA 所有权案例](references/cases/streaming-dma-ownership.md)。这些都是合成教学材料，不表示曾在某个目标板验证。

## API 版本与平台驱动 remove 回调

按目标内核头文件实现回调，不从另一版本复制声明。上游 Linux v6.10 的 `platform_driver` 提供返回 `int` 的 `.remove` 和返回 `void` 的 `.remove_new`；上游 v6.11 起 `.remove` 返回 `void`。厂商内核可能回移植 API，检查目标 `include/linux/platform_device.h` 和同树驱动。remove 用于停止新工作、停止设备活动并同步退出，不用返回值尝试撤销卸载。

## 验证并报告

| 检查 | 需要的证据 |
|---|---|
| 编译 | 目标内核版本、配置、编译器、Kbuild 命令和模块 `vermagic` |
| 绑定 | 运行设备的 `compatible`/modalias、驱动匹配表、`dmesg` 与 sysfs driver link |
| 错误路径 | probe 失败回滚、资源计数、IRQ/work/timer 同步退出；有条件时使用故障注入或 KASAN/lockdep |
| 长时间行为 | 重复打开/关闭或绑定/解绑、压力 I/O、错误恢复、运行时与系统休眠/恢复循环 |
| ABI | 子系统接口或自定义 ABI 的并发、权限、错误、卸载和版本兼容行为 |

把静态检查、目标内核编译、模拟/自动化测试和真实板卡结果分开说明；没有运行的检查不要写成已通过。
