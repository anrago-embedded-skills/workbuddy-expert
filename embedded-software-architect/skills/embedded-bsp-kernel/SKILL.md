---
name: embedded-bsp-kernel
description: |
  BSP and kernel work on Linux ARM64: U-Boot, Device Tree (DTS/DTSI), kernel modules, Buildroot/Yocto cross-compile, systemd services.
  TRIGGER when: BSP、U-Boot、uboot、设备树、device tree、DTS、DTSI、dtc、platform_driver、内核模块、insmod、probe、modprobe、交叉编译、buildroot、Yocto、bitbake、toolchain、systemd、开机自启、服务管理、journalctl、systemctl、defconfig、内核编译、编译不过、编译报错、交叉编译失败、找不到头文件、设备树不生效、驱动加载不了、服务起不来、开机就报错、启动失败、modprobe 失败、编译不过、编译报错、编译失败、交叉编译失败、交叉编译报错、设备树不生效、驱动加载不了、驱动装不上、服务起不来、开机就报错、启动失败,
  DO NOT TRIGGER when: 应用程序业务逻辑开发；应用崩溃的运行时排查（用 embedded-debug-workflow）,
---

# embedded-bsp-kernel

> BSP、内核、设备树、交叉编译、systemd 的通用方法论。平台特有部分在 `references/` 按需加载。

## 适用范围

Linux ARM64 嵌入式设备的 BSP 层开发：启动链、设备树、内核模块、构建系统、开机服务。

**不适用**：MCU 裸机固件。

---

## 平台适配

动手前先确认目标 SoC，加载对应文档：

| SoC | 适配文档 |
|---|---|
| RK3588 | `references/rockchip-rk3588.md` |
| MTK | `references/mediatek-mtk.md` |
| 全志 | `references/allwinner-tde.md` |
| NXP i.MX | `references/nxp-imx-vpu.md` |
| 海思 Hi3516 | `references/hisilicon-hi3516.md` |
| 国科微 | `references/goke-micro-g300.md` |
| 通用 | `references/generic-linux.md` |

---

## U-Boot 启动链

```
BootROM → SPL/TPL → U-Boot (uImage) → Kernel (Image + dtb + ramdisk)
```

```bash
# 确认启动参数与实际加载的设备树
printenv bootargs      # 内核命令行
printenv bootcmd
fdt addr${fdt_addr}; fdt print      # 运行时设备树内容

# 重启设备
reset
```

**关键**：设备树以 **dtb 形式单独加载**，改内核源码不等于改设备树——两者要分别确认。

---

## 设备树（DTS/DTSI）

### 结构层级

```
型号.dts        # 产品级定义（板子）
  include 厂商基础.dtsi
  / {
      model = "...";
      compatible = "vendor,soc-board";
      memory { ... };
      chosen { bootargs = "..."; };
  };
```

### 关键节点

| 节点 | 作用 |
|---|---|
| `/memory` | 内存布局（含 `reg` 与可能的 `linux,memreserve`） |
| `/chosen` | `bootargs`、`stdout-path` |
| `/aliases` | 设备路径别名（i2c0、serial0 等） |
| `/soc` | SoC 内部外设（挂在总线下，带 `reg` / `interrupts`） |
| 根节点的 `gpios` | 根GPIO |

### 调试设备树

```bash
# 运行时设备树（实际生效的，含 bootloader 修改）
ls /proc/device-tree/
cat /proc/device-tree/model

# 解压 dtb 查看
dtc -I dtb -O dts running.dtb > running.dts

# 编译
dtc -I dts -O dtb -o out.dtb board.dts
```

**要点**：设备树可能有 **overrides**（dtso），最终生效的要看运行时 `/proc/device-tree`，不能只看源文件。

---

## 内核模块

### 基础操作

```bash
make ARCH=arm64 CROSS_COMPILE=arm-linux-gnueabihf- modules
insmod xxx.ko
lsmod
dmesg | tail -50          # 加载日志必看
rmmod xxx
```

### platform_driver 结构

```c
static int probe(struct platform_device *pdev) { ... }
static int remove(struct platform_device *pdev) { ... }
static struct platform_driver my_drv = {
    .probe  = probe,
    .remove = remove,
    .driver = { .name = "my_drv", },
};
module_platform_driver(my_drv);
```

**要点**：`probe` 与设备树的 `compatible` 必须匹配，否则驱动不会绑定（`dmesg` 看不到绑定日志）。

### 关键调试

```bash
dmesg | grep -i "my_drv"        # 确认 probe 是否被调用
ls /sys/bus/platform/drivers/   # 确认驱动已注册
cat /sys/devices/platform/<node>/modalias   # 确认设备 modalias
```

`probe` 不被调用 → 先查 `compatible` 字符串是否完全一致（含 vendor 前缀）。

---

## 交叉编译

### Buildroot

```bash
make menuconfig         # Target options → 确认 target/arm64
make                    # 完整构建
make linux-rebuild      # 只重建内核
make app-rebuild        # 只重建 app
```

输出：`output/target/`（根文件系统）、`output/images/`（镜像）。

### Yocto

```bash
bitbake-layers show-layers      # 确认 layer
bitbake core-image-minimal      # 构建
bitbake -c compile fit-image     # 只编译内核
```

Yocto 的 `bbappend` 用于覆盖默认 recipe 配置，是定制 BSP 的标准方式。

### 独立工具链

```bash
export CROSS_COMPILE=arm-linux-gnueabihf-
export ARCH=arm64
make defconfig
make -j$(nproc)
```

**要点**：嵌入式改动必须交叉编译，桌面 gcc 通过**不代表**目标板可用（对齐、字节序、glibc 版本差异）。

---

## systemd 服务

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application
After=network.target
Requires=xxx.service       # 依赖

[Service]
Type=simple
ExecStart=/usr/bin/myapp --flag
Restart=always
RestartSec=5
WorkingDirectory=/opt/myapp
Environment="PATH=/usr/local/bin"
User=root                    # 嵌入式常用 root，需评估权限风险
StandardError=journal
LimitNOFILE=65536            # 长跑应用常需提高

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable myapp       # 开机自启
systemctl start myapp
systemctl status myapp
journalctl -u myapp -f       # 实时日志
journalctl -b                # 本次启动全部日志
```

### 与老式启动脚本互转

```bash
systemd-analyze verify myapp.service   # 校验 unit 文件
```

**要点**：嵌入式常见问题——`After=` 依赖声明不足导致启动顺序错乱，或对普通文件/设备做了依赖导致挂起。

---

## 边界与注意

- 设备树改完**必须确认运行时生效**（`/proc/device-tree`），不能只看源文件
- 交叉编译通过不代表板上可用，**必须板上验证**
- `probe` 不执行优先查 `compatible` 匹配，不要盲目加日志
- 烧写固件前**确认回滚方案**
- 平台特有的 U-Boot 补丁、DTS 差异，查对应平台 references