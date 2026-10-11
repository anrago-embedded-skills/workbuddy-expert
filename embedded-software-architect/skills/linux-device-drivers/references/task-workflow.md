# Linux 驱动任务工作流

## 目标与最低输入

以目标内核、设备 binding 和硬件资料为依据，缩小到一项可审查的改动，并让验证能区分代码问题、目标配置问题与硬件问题。先收集：

- 预期设备行为、可重复的触发条件和实际症状；设备型号、总线与板卡版本（未知项明确标记）。
- 目标内核源码/版本/厂商补丁、`.config`、构建产物、工具链 ABI，以及该设备的 binding/DTS 和驱动源码。
- 目标 runtime tree、总线枚举、modalias、驱动绑定链接、有限范围的 `dmesg` 和可重现的错误路径。
- 用户接口、供电/时钟/reset/IRQ/DMA 依赖、调用者与异步执行者；现有构建和测试条件。

若硬件手册或完整 SDK 暂缺，仍可沿通用 driver-core/API 路径检查已存在源码、errno 传播和生命周期；具体寄存器、资源数值、时序、回调声明或 DMA 协议保持未确认。目标头文件和同树驱动优先于按版本号推测。不要为展示“完整流程”虚构可编译的内核模块。

## 按证据分支

| 观测 | 需要的区分证据 | 可能的处理边界 |
|---|---|---|
| 总线上没有设备 | runtime 节点及父控制器、控制器注册、目标总线 enumeration | BSP/设备树/板级配置，未到驱动 probe |
| 设备存在但未绑定 | `compatible`/modalias、目标匹配表、内核配置、模块 alias 与加载状态 | 修正匹配/配置；`MODULE_DEVICE_TABLE` 不代替 driver-core match |
| probe 返回错误 | 原始 errno、调用失败的资源 API、目标 binding、provider 状态 | 修复错误资源或真实失败；不要把任何 errno 改成 defer |
| probe 返回 `-EPROBE_DEFER` | deferred 状态、supplier 节点/驱动/provider 错误、重试前后日志 | 保留真实 defer，定位 supplier；读[案例](cases/probe-defer.md) |
| 已绑定但 I/O 异常 | 请求/完成边界、IRQ/work 状态、MMIO/DMA 映射和硬件协议 | 从最小操作路径取证；DMA 见[案例](cases/streaming-dma-ownership.md) |
| unbind/remove 卡住或释放后崩溃 | blocked task stack、锁依赖、重新排队者、open fd 和 IRQ/DMA 停止证据 | 拆解退出顺序与对象所有权；见[异步 teardown 案例](cases/async-teardown-deadlock.md) |

`dev_err_probe()` 会保留错误并为 `-EPROBE_DEFER` 设置 deferred reason；目标内核支持时读取 `devices_deferred`。先确认问题在哪个分支，再改代码，避免仅追加日志或改 compatible 猜测。

## 最小实现、构建与回归

1. 先检查现有同类驱动、binding、目标树头文件和子系统接口；优先延续已有 subsystem。列出 probe 中取得的资源、公开接口与所有异步 producer/consumer。
2. 仅改命中的假设：保留 provider errno；错误路径撤回已注册对象；remove 先阻止新工作并按硬件/回调依赖停止 producer、硬件和异步执行者，再释放被引用资源。注销 cdev 不会关闭已打开 fd。
3. 保持 patch 小且可 review。没有 target tree 和真实配置时，只给构建模板并指出还缺什么，不能声称它能编译。
4. 在**与目标内核同一次配置/构建的输出目录**下进行构建。参数模板：

```sh
# Linux 构建主机；KOUT 是匹配目标内核的已配置输出目录。
make -C "$KOUT" M="$PWD" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" modules
```

`KOUT` 必须指向目标 SDK 已配置的内核构建目录；`ARCH` 和交叉编译器描述目标而非 host。比较目标 `uname -r`、配置、`vermagic`、符号版本和签名策略。模块编译通过仍不能证明 runtime binding 或设备行为。

5. 按风险回归：probe 失败后重试、错误回滚、反复 bind/unbind、IRQ/work/timer 并发、用户 fd 横跨解绑、DMA 完成/超时/复位、runtime/system suspend。只在目标内核配置与环境具备时启用 lockdep、KASAN、DMA API debug、fault injection、KUnit/kselftest。
6. 交付目标内核与 SDK 身份、patch、精确构建命令、编译结果、绑定证据、已执行的错误/并发回归和限制。未提供板卡/内核或未运行目标验证时明确写出。

对于可部署产物，记录原模块/固件和如何恢复到上一版本；不要把卸载、重载或重启当作无风险回滚。目标节点、电源、硬件协议或恢复方法仍未知时，停在静态/构建证据层并列出待补资料。
