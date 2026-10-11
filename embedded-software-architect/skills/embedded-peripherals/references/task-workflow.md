# 板级外设任务工作流

## 目标与最低输入

让运行时外设节点准确描述实际板级连接，并能从 schema、枚举、driver binding 和电气行为中分别验证。最低输入：

- 用户可见的症状、设备预期行为、板卡型号/修订与 SoC（未知项标记）。
- 总线、器件型号/数据手册、原理图中的信号和供电，目标内核树/binding 与当前 DTS/DTSI。
- 目标 Linux runtime tree、父控制器状态、`/sys/bus/.../devices` 枚举和相关 driver/log 证据。

若器件准确料号、板卡修订或电气极性未知，可继续检查只读的运行时节点、binding 结构和软件枚举；不能猜 GPIO 编号、I2C 地址、IRQ 类型、电压、总线频率或 reset 延时，也不能把示例值带入板级配置。

## 分支和最小动作

| 观测 | 先取的证据 | 范围 |
|---|---|---|
| 节点未出现在 runtime tree | `dtc -I fs` 导出的 runtime DTS、bootloader/overlay 选择和 DTS 构建/打包输入 | 转 [BSP 工作流](../../embedded-bsp-kernel/references/task-workflow.md)；案例见[DTB 未生效](../../embedded-bsp-kernel/references/cases/dtb-not-taking-effect.md) |
| 节点存在、总线设备不存在 | `status`、父控制器节点/驱动、pinmux、时钟/reset/supply、地址和总线设备列表 | controller/DTS/binding；不要以主动扫描作为第一步 |
| 总线设备存在、无 driver 链接 | 实际 compatible、modalias、binding、驱动配置/模块状态 | 转 [Linux 驱动工作流](../../linux-device-drivers/references/task-workflow.md) |
| probe 出错或 deferred | 原始 errno、provider 节点和 driver 状态、目标 binding | 区分永久错误和 supplier 延迟；转[驱动 probe defer 案例](../../linux-device-drivers/references/cases/probe-defer.md) |
| driver 已绑定但无响应 | 实际电源/信号/IRQ、线路时序和电气参数证据 | 按数据手册、原理图和可用测量设备确认；软件匹配成功不足以证明线路正确 |

对 I2C/SPI 设备先读运行时描述和现有 sysfs/bus 状态。`i2cdetect` 会对总线发出探测事务，只在确认所有器件允许时才使用；GPIO 线路先确认未由 kernel consumer 占用。工具不在目标系统中时记为不可用，不在构建主机模拟目标结果。

## 验证和交付

1. 形成一份观测→假设→区分证据表；每个板级数值都标出来源（原理图、器件手册或目标 binding）。
2. 只修改最小 DTS 节点/binding-compatible/config 项；保留板卡专属 phandle 和控制器 specifier，不将其他型号示例照抄。
3. 在 Linux 构建主机的目标内核/BSP 树运行 DTS 构建与 `dtbs_check`，binding 有改动时按该树运行 `dt_binding_check`。分别报告语法、schema、产物打包、目标 runtime tree、bus enumeration、driver bind 和电气/功能验证。
4. 回归依赖设备而定：正常枚举、driver probe、接口状态、启动/重启后仍使用相同 runtime node、错误电平/掉电后的安全恢复。没有目标板或测量证据就列为未执行。
5. 交付最小 patch、资料来源、构建入口、各层验证结果和回退到原 DTS/DTB 的具体方法。写入 boot 分区前确认可用恢复路径；构建产物本身不验证电路。

任务命令、预期观察与副作用的通用约定见[工程工作流](../../embedded-debug-workflow/references/engineering-workflow.md)和[验证策略](../../embedded-debug-workflow/references/validation-policy.md)。
