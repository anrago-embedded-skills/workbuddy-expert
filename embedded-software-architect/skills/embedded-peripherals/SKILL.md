---
name: embedded-peripherals
description: |
  用于依据板级资料，通过设备树和 Linux 现有子系统配置或诊断 GPIO、I2C、SPI、UART、pinctrl、regulator、LED、按键和传感器。
---

# embedded-peripherals

根据板卡原理图、控制器 binding 和目标内核树配置外设。修改 DTS 前先记录运行时节点和供应设备状态。

## 任务工作流

目标是让板级外设描述符合原理图、目标 binding 和运行中的内核，并把语法/schema 证据与实际枚举、电气证据分开。最低输入是外设症状、板卡/SoC（未知时注明）、信号或总线、目标内核树、相关 DTS 与运行时设备树/总线枚举；硬件修订或电气参数不明时可继续比较节点结构和采集只读证据，但不猜 GPIO、地址、电平、时钟或电源值。按节点缺失、总线未枚举、无匹配、probe 失败/defer、已绑定但无响应分支。交付最小 DTS/config patch、目标 binding/schema 结果、运行时节点与驱动状态证据，以及回退到原 DTB 的方法。详细流程见[外设任务工作流](references/task-workflow.md)；DTB 未进入运行时节点时参见[BSP 的 DTB 未生效案例](../embedded-bsp-kernel/references/cases/dtb-not-taking-effect.md)。

跨领域任务和交付约定见[通用工程工作流](../embedded-debug-workflow/references/engineering-workflow.md)；验证证据的边界见[验证策略](../embedded-debug-workflow/references/validation-policy.md)。

## 主用与配合

本技能主用于板级总线、引脚、电气资源和外设设备树属性，并沿用内核已有子系统。目标节点因实际加载的 DTB、overlay 或启动配置而缺失时，配合 [embedded-bsp-kernel](../embedded-bsp-kernel/SKILL.md)；节点已存在而问题落在驱动匹配、probe 代码、错误处理或生命周期时，配合 [linux-device-drivers](../linux-device-drivers/SKILL.md)。

## 设备树结构

优先使用内核已有的标准驱动和 binding。以下代码展示节点结构；compatible、GPIO 控制器参数、I2C 地址、按键映射和电气极性都要按板级资料和目标 binding 替换。

### GPIO LED 和按键

```dts
#include <dt-bindings/gpio/gpio.h>
#include <dt-bindings/input/input.h>

leds {
    compatible = "gpio-leds";

    status-led {
        gpios = <&gpio3 GPIO_LINE GPIO_ACTIVE_LOW>; /* 按原理图确认有效电平。 */
        linux,default-trigger = "heartbeat";
    };
};

gpio-keys {
    compatible = "gpio-keys";

    power-key {
        label = "Power";
        linux,code = <KEY_POWER>;
        gpios = <&gpio3 KEY_GPIO_LINE GPIO_ACTIVE_LOW>;
        wakeup-source; /* 只有该板卡支持此线路唤醒时才设置。 */
    };
};
```

每个 LED 或按键都应是父节点下的子节点，并在自己的子节点中使用 `gpios`。gpio-keys 子节点必须提供 `linux,code`。只有线路不能产生中断时，才使用 `gpio-keys-polled` binding。以目标树中的 [gpio-leds binding](https://github.com/torvalds/linux/blob/master/Documentation/devicetree/bindings/leds/leds-gpio.yaml) 和 [gpio-keys binding](https://github.com/torvalds/linux/blob/master/Documentation/devicetree/bindings/input/gpio-keys.yaml) 为准。

### I2C 设备和中断

```dts
#include <dt-bindings/interrupt-controller/irq.h>

&i2c2 {
    status = "okay";
    clock-frequency = <400000>; /* 选择所有设备和板级线路都支持的速率。 */

    sensor@36 {
        compatible = "vendor,sensor"; /* 换成 binding 中登记的值。 */
        reg = <0x36>; /* 仅作 7-bit 地址格式示例，实际值查器件和板级文档。 */
        interrupt-parent = <&gpio0>;
        interrupts = <GPIO_IRQ_LINE IRQ_TYPE_EDGE_FALLING>;
    };
};
```

`interrupts` 使用中断控制器要求的 specifier 和 `IRQ_TYPE_*` 触发标志，不使用 `GPIO_ACTIVE_*`。从该控制器 binding 和原理图确认 `#interrupt-cells`、电气极性、边沿/电平和开漏设置。如果设备 binding 使用 IRQ GPIO 属性，则采用它规定的写法。

I2C 子设备的 `reg` 是 binding 所定义的 7-bit 地址，不是 8-bit 读写地址。不要从示例或总线扫描推断实际地址。

### SPI 设备和固定稳压器

```dts
&spi1 {
    status = "okay";

    flash@0 {
        compatible = "jedec,spi-nor";
        reg = <0>;
        spi-max-frequency = <DEVICE_MAX_HZ>; /* 按目标 binding 和器件上限设置。 */
    };
};

regulator-3v3 {
    compatible = "regulator-fixed";
    regulator-name = "board-3v3";
    regulator-min-microvolt = <BOARD_RAIL_UV>;
    regulator-max-microvolt = <BOARD_RAIL_UV>;
    gpio = <&gpio1 REGULATOR_GPIO_LINE 0>;
    enable-active-high; /* 仅当 enable 信号为高有效时设置。 */
};
```

fixed-regulator binding 使用 `gpio` 或 `gpios`；其 GPIO 极性由 `enable-active-high` 控制，不能假定 phandle 标志控制极性。电压、enable 极性、启动延时和 SPI 频率都属于硬件参数，应按电路和 [fixed-regulator binding](https://github.com/torvalds/linux/blob/master/Documentation/devicetree/bindings/regulator/fixed-regulator.yaml) 确认。

## 检查运行时绑定

设备树属性文件是二进制数据。以下命令在目标板 Linux shell 读取 runtime tree，并把导出文件写入当前目录：

```sh
dtc -I fs -O dts /proc/device-tree > running.dts
tr '\0' '\n' < /proc/device-tree/model
```

对照目标 binding 检查设备的运行时 `compatible`、`status`、资源、父总线、pinctrl 状态、时钟、复位、电源和中断。使用目标内核树的 `make dtbs_check` 验证 schema；`dtc` 能解析语法并不代表通过 binding 验证。构建和 schema 检查见 `embedded-bsp-kernel`。

## 运行时工具

以下命令在目标板 Linux shell 运行，采用 libgpiod 2.x 语法；较旧 BSP 先查看 `--version` 和对应版本的 `--help`。`gpiodetect`、`gpioinfo` 和 `gpioget` 用于查询；只有确认线路未由内核/其他进程使用、且任务允许改变信号时才运行会驱动线路的 `gpioset`。参数格式见 [libgpiod 命令行工具文档](https://libgpiod.readthedocs.io/en/master/gpio_tools.html)。

```sh
gpiodetect
gpioinfo --chip gpiochip0
gpioget --chip gpiochip0 LINE_NAME
gpioset --chip gpiochip0 LINE_NAME=1
```

libgpiod 2.x 的 `0`/`1` 表示逻辑 inactive/active；物理高低电平还取决于线路极性。`gpioset` 会在进程存活期间持有线路，进程退出后线路值可能恢复。不要驱动已被内核 consumer 占用的线路。旧版 GPIO sysfs ABI 已弃用；使用 character-device 工具或所属子系统。

I2C 先在目标板检查 `i2cdetect -l`、运行时设备树和 `/sys/bus/i2c/devices/`。`i2cdetect -y BUS` 会主动探测地址，可能干扰设备；只在确认器件和总线允许扫描时使用。SPI 先检查 `/sys/bus/spi/devices/` 和驱动绑定状态，再决定是否测试用户态端点。

## 区分未探测和无响应

| 现象 | 检查内容 |
|---|---|
| 总线上没有设备 | 控制器是否启用并注册；运行时子节点、`status`、地址、pinmux、时钟、复位和供电 |
| 设备存在但没有驱动链接 | 驱动是否编译/加载，`compatible` 或总线 ID 匹配表，modalias 和模块自动加载设置 |
| probe 返回错误或 deferred | `dmesg`、目标 binding、供应设备状态、`-EPROBE_DEFER`，以及 debugfs 可用时的 `devices_deferred` |
| 驱动已绑定但无响应 | 板级连线、电源时序、线路极性、总线时序、中断触发和设备状态 |

使用目标文档规定的设备节点和子系统接口。LED、按键、传感器、稳压器或标准总线设备已有内核子系统接口时，不要另加通用字符驱动。

## 边界

- 从 SoC binding 和板级原理图确认 GPIO 编号及复用；不同板卡的 offset 不能互换。
- 不猜电压、寄存器地址、I2C 地址、中断触发方式或器件能力。
- 分别报告 DTS 编译、schema 验证、目标驱动绑定和电气/运行时验证结果。
