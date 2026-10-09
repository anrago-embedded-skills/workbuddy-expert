---
name: embedded-peripherals
description: |
  Embedded peripheral (GPIO/I2C/SPI/UART/regulator/backlight/LED) device-tree configuration and driver binding debugging.
  TRIGGER when: GPIO、I2C、SPI、UART、串口、regulator、背光、按键、LED、蜂鸣器、传感器、外设、pinctrl、i2cdetect、gpioset、amixer controls、设备节点、probe 不执行、驱动不绑定、按键没反应、按键失灵、背光不亮、灯不亮、蜂鸣器不响、传感器读不到、读不到数据、I2C 不通、SPI 不通、串口没输出、设备节点没生成,
  DO NOT TRIGGER when: 摄像头/显示外设的媒体链路（用 media-pipeline-linux）；PCIe/SATA/存储硬件（用 storage-hardware-io）,
---

# embedded-peripherals

> 外设（GPIO / I2C / SPI / UART / regulator / 背光 / led）的设备树配置与调试方法论。平台适配见 `references/`。

## 适用范围

嵌入式外设的配置、设备树声明、驱动绑定与调试。

**不适用**： MCU 裸机寄存器级操作。

---

## 设备树声明外设

### GPIO

```dts
my_led: my-led {
    compatible = "gpio-leds";
    led-gpios = <&gpio3 RK_PC4 GPIO_ACTIVE_LOW>;
};

my_button: my-button {
    compatible = "gpio-keys";
    button-gpios = <&gpio3 RK_PB3 GPIO_ACTIVE_LOW>;
};
```

**注意**：`GPIO_ACTIVE_LOW` 一定要和实际硬件电路一致，否则逻辑反了。

### I2C 设备

```dts
&i2c2 {
    status = "okay";
    clock-frequency = <400000>;      # 常见 100k/400k

    sensor@36 {
        compatible = "vendor,sensor";
        reg = <0x36>;
        interrupt-parent = <&gpio0>;
        interrupts = <RK_PA3 GPIO_ACTIVE_HIGH>;
    };
};
```

**要点**：`reg` 必须是设备的 7-bit 从机地址（不是 8-bit 读写地址）。

### SPI 设备

```dts
&spi1 {
    status = "okay";
    num-cs = <1>;

    flash@0 {
        compatible = "jedec,spi-nor";
        reg = <0>;
        spi-max-frequency = <50000000>;   # 注意 Flash 通常有频率上限
    };
};
```

### regulator

```dts
vdd_3v3: vdd-3v3 {
    compatible = "regulator-fixed";
    regulator-name = "VDD_3V3";
    regulator-min-microvolt = <3300000>;
    regulator-max-microvolt = <3300000>;
    enable-gpios = <&gpio1 RK_PD2 GPIO_ACTIVE_HIGH>;
};
```

**注意**：电压必须和实际硬件一致，配置错误可能导致外设不工作甚至损坏。

---

## 调试手段

```bash
# 查看所有 I2C 总线与设备
i2cdetect -l
i2cdetect -y 2                  # 扫描总线（会挂起设备，风险，慎用）

ls /sys/bus/i2c/devices/
cat /sys/bus/i2c/devices/2-0036/name

# SPI
ls /dev/spidev*
cat /sys/bus/spi/devices/

# GPIO
cat /sys/class/gpio/
cat /sys/class/gpio/gpiochip*/label
```

### gpio 命令行工具

```bash
gpioset chip 3 4=1     # 置高
gpioget chip 3 4       # 读值
gpiotoggle chip 3 4    # 翻转
```

### 设备树生效确认

```bash
cat /proc/device-tree/...节点路径/reg
dtc -I dtb -O dts /proc/device-tree/ > running.dts
```

**要点**：设备树可能有 overrides，**运行时才是真相**。

---

## 常见问题

| 现象 | 可能原因 |
|---|---|
| I2C 设备不响应 | 地址错（8bit/7bit 混淆）、上拉缺失、电压不对、速率太高 |
| 驱动 probe 不执行 | `compatible` 不匹配（最常见）、节点 `status` 不是 okay |
| 外设偶发失效 | 信号完整性、时钟速率、上电时序 |
| 全部外设失效 | 电源域（regulator）未使能、pinctrl 未配置 |

---

## 边界与注意

- **不要凭猜测配置寄存器/电压**，查芯片手册确认
- `i2cdetect` 扫描会挂起总线上设备，有风险，优先读设备树和 `/sys` 确认地址
- 设备树改完**必须确认运行时生效**
- probe 不执行优先查 `compatible` 完整匹配（含 vendor 前缀）
- 具体 GPIO 编号因板卡而异，**必须先确认硬件原理图与 pinout**，不要假设