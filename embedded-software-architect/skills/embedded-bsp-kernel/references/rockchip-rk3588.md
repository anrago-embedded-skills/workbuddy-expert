# Rockchip RK3588 BSP 适配

> RK3588 BSP 生态成熟，官方维护 u-boot、Linux kernel（rockchip 分支）、Buildroot/Yocto BSP。

## 启动链

```
BootROM → TPL/SPL(TB-RK3588) → U-Boot (u-boot.itb) → Kernel (Image + rk3588.dtb)
```

RK3588 使用 **U-Boot FIT（u-boot.itb）** 镜像，包含 U-Boot 主体 + 设备树 + 启动脚本。

```bash
# 查看启动日志（串口/console）
printenv bootargs
printenv bootcmd
```

## SDK 与仓库

| 项目 | 典型仓库/位置 |
|---|---|
| U-Boot | `u-boot-rockchip`（分支如 `next-dev`） |
| Kernel | `linux-rockchip`（`rk-5.10` / `RK6.1` 等分支） |
| Buildroot | `buildroot` + `device/rockchip` |
| Yocto | `meta-rockchip` |
| 根文件系统 | `buildroot` / Yocto 产出 |

RK3588 主流内核分支为 **5.10**（用户设备多为该版本，kernel 5.10.x）。

## 设备树组织

```
arch/arm64/boot/dts/rockchip/
├── rk3588.dtsi              # SoC 基础定义
├── rk3588s.dtsi             # RK3588S 变体
├── rk3588-evb.dtsi          # EVB 开发板
└── rk3588-<board>.dts       # 板级
```

**要点**：SoC 级定义（rk3588.dtsi）与板级（board.dts）分离，改板级配置不要动SoC 级文件。

```bash
# 运行时确认（可能含 overrides）
cat /proc/device-tree/model
dtc -I dtb -O dts /proc/device-tree/ 2>/dev/null
```

## 常用调试

```bash
# 内核版本与构建信息
uname -a
cat /proc/version

# 内存布局（RK3588 CMA 是重点排查项）
grep -E "MemTotal|MemAvailable|CmaFree|SwapTotal" /proc/meminfo

# 设备树生效确认
ls /proc/device-tree/
```

## 特色注意点

- **CMA（Contiguous Memory Arena）**：摄像头/GPU 需大块连续内存，CMA 不足会导致「有内存却分配失败」，是 RK3588 OOM 常见根因
- **0 swap 板卡常见**：很多 RK3588 板子没开 swap，OOM 即真OOM
- **多电源域**：RK3588 有多个 PMIC/电源域，设备树里 regulator 配置需完整

## 边界与注意

- U-Boot 分支与设备对应关系要确认，**跨分支移植补丁常失效**
- DTS 修改必须板上验证（运行时 `/proc/device-tree`），不能只看编译通过
- 具体寄存器/时钟配置查对应芯片 TRM，不要凭印象写