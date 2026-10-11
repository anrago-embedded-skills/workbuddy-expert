# 电源、子系统与验证

## 时钟、复位、电源与 pinctrl

用框架的 consumer API 表达设备依赖；provider 未就绪时保留 framework 返回的 `-EPROBE_DEFER`。

- 时钟：使用 Common Clock Framework consumer API，平衡 prepare/enable 与 disable/unprepare；只有硬件数据证明需要时才修改频率或父时钟。
- 复位：依据线路共享情况申请 shared 或 exclusive reset；按芯片启动时序进行 assert、deassert 和 delay。不要假定 reset line 只服务一个设备。
- 电源：以 regulator consumer API 管理 supply；启停是引用计数操作，disable 不保证物理电压一定关闭。电压范围、startup delay 和供电顺序须来自原理图、PMIC binding 和芯片手册。
- pinctrl：设备的 `default` 状态通常由设备核心在 probe 前选择；休眠/空闲状态按 pinctrl 与 PM API 切换。确认复用功能、上下拉、驱动强度与电压域。

如果设备拥有电源、时钟、复位或共享资源的控制器本身，遵守相应 provider subsystem 的职责和同步规则；不要从消费者驱动直接写其他设备的寄存器。

## Runtime PM 与 system sleep

先定义设备的 active、runtime-suspended、system-suspended、wakeup 和 error 状态，再实现相应 PM 操作。Runtime PM 管理空闲设备；system sleep 还涉及设备层级、唤醒源和系统转换阶段，两组回调不能假设永远互不影响。

睡眠前停止新的 I/O，停止或完成 DMA，处理 IRQ/唤醒配置，保存恢复所需的硬件状态，再按设备依赖关闭时钟或电源。恢复时按硬件启动顺序重新供电、解除复位、初始化寄存器，并确认设备状态可供子设备使用。PM callback 通常处于可睡眠上下文；只有明确启用并满足约束的 `pm_runtime_irq_safe()` 才能假定其处于原子上下文。

循环验证 runtime suspend/resume 与 system suspend/resume，覆盖并发 I/O、唤醒事件、错误回滚以及设备原先已 runtime-suspended 的情况。查看 PM core 状态和 trace/debug 信息时，区分设备驱动问题、父设备/PM domain 问题与系统级策略。

## 用户空间接口与错误路径

优先复用 input、LED、IIO、hwmon、V4L2、DRM/KMS、ALSA/ASoC、TTY、网络、块设备或其他合适子系统。自定义字符设备只在缺少合适语义时采用，并定义最小、可长期维护的 ABI：

- 明确 ioctl/读写结构中的固定宽度字段、对齐、32/64-bit compat、版本和能力协商方式。
- 为无效参数、设备不存在、资源忙、设备掉电、取消和超时定义稳定错误行为。
- 处理多个进程、关闭文件描述符、设备解绑、权限检查和 `O_CLOEXEC`。
- 注销字符设备只阻止新的 open；已有 fd 仍可能触发 file operations。解绑后让旧 fd 看到 removed 状态、拒绝访问硬件，并用独立引用计数或等效所有权保证回调状态存活。不要让 remove 无限期等待进程关闭 fd，也不要让 fd 保存指向已释放 devm 私有状态的指针。
- 新 sysfs 属性遵循一个属性一个简单值的模型，并把 ABI 记录在目标内核 `Documentation/ABI/` 中。

按风险验证实现：至少覆盖 probe 失败后的重复尝试、接口注册/注销、快速打开关闭、读写错误、超时/中断竞争、反复 bind/unbind 和长时间负载；有相应内核配置和环境时再启用 KASAN、lockdep、DMA API debug、KUnit、kselftest 或 fault injection。记录每个未执行的硬件相关场景，不把仿真或静态阅读写成板上通过。

## 主要资料

- [Clock framework](https://docs.kernel.org/driver-api/clk.html)；[Reset controller API](https://docs.kernel.org/driver-api/reset.html)；[Regulator API](https://docs.kernel.org/driver-api/regulator.html)
- [Pinctrl subsystem](https://docs.kernel.org/driver-api/pin-control.html)
- [Runtime PM](https://docs.kernel.org/power/runtime_pm.html)；[设备 system PM](https://docs.kernel.org/driver-api/pm/devices.html)
- [Linux ABI 文档](https://docs.kernel.org/admin-guide/abi.html)；[sysfs 使用规则](https://docs.kernel.org/admin-guide/sysfs-rules.html)
- [ioctl UAPI 设计](https://docs.kernel.org/driver-api/ioctl.html)
- 子系统入口：[GPIO](https://docs.kernel.org/driver-api/gpio/index.html)、[IIO](https://docs.kernel.org/driver-api/iio/)、[hwmon](https://docs.kernel.org/hwmon/index.html)、[V4L2](https://docs.kernel.org/driver-api/media/v4l2-core.html)、[DRM/KMS](https://docs.kernel.org/gpu/index.html)
