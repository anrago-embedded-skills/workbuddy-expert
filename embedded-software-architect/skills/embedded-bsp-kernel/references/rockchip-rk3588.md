# Rockchip RK3588 BSP 适配

RK3588 项目可能使用不同供应方、SDK 与内核/bootloader 分支。先从包内 manifest、源码 origin、板卡文档和运行版本确认，不按 SoC 名选择固定仓库或 branch。

## 启动链

```
BootROM → [TPL/SPL] → U-Boot/FIT → [TF-A / OP-TEE, if this board uses them] → Kernel + DTB
```

具体阶段和 FIT 内容由板卡、固件打包方式与 SDK 配置决定；串口日志和该板发行包才是实际启动顺序的依据。

```text
# 在 U-Boot 控制台查看当前环境；具体变量名与可用命令依目标配置而定。
printenv bootargs
printenv bootcmd
```

## SDK 与仓库

| 项目 | SDK 中要确认的事实 |
|---|---|
| U-Boot/kernel | 实际源码仓库、提交/分支、配置与补丁集 |
| Buildroot/Yocto | 是否使用、板级层/recipe 与实际构建输出 |
| 根文件系统 | 来源、启动方式、版本及其与 kernel/DTB 的配套关系 |

不同 SDK 可能采用不同的厂商内核分支；以设备正在运行的版本和实际构建树为准。

## 设备树组织

部分上游树的 DTS 查找路径示例（路径和架构均须对照实际目标树确认）：

```text
arch/arm64/boot/dts/rockchip/
├── rk3588.dtsi              # SoC 基础定义
├── rk3588s.dtsi             # RK3588S 变体
├── rk3588-evb.dtsi          # EVB 开发板
└── rk3588-<board>.dts       # 板级
```

SoC 级定义与板级 DTS 常分开组织；确认当前板卡 include 链后，只修改能表达板级差异的正确文件。

```sh
# 在目标 Linux shell 读取 runtime tree；输出文件写入当前目录。
tr '\0' '\n' < /proc/device-tree/model
dtc -I fs -O dts /proc/device-tree/ > running.dts
```

## 常用调试

```sh
# 内核版本与构建信息
uname -a
cat /proc/version

# 在目标板 Linux shell 上检查实际内存、CMA 和 swap 状态
grep -E "MemTotal|MemAvailable|CmaTotal|CmaFree|SwapTotal|SwapFree" /proc/meminfo
swapon --show
cat /proc/swaps

# 设备树生效确认
ls /proc/device-tree/
```

## 特色注意点

- **连续内存分配失败**：CMA 是 Contiguous Memory Allocator。摄像头/GPU 是否要求特定连续性取决于驱动、DMA API、IOMMU 和缓冲区分配路径。结合实际分配日志、`CmaTotal`/`CmaFree`、请求大小与约束判断；单次 CMA/DMA 分配失败不等于系统 OOM，也不能单独证明根因。见 [驱动 IO 与 DMA 诊断](../../linux-device-drivers/references/io-and-dma.md)。
- **swap 与 OOM**：按目标板运行时输出确认 swap，不根据 RK3588 型号推断。检查 `/proc/meminfo`、`swapon --show`、`/proc/swaps` 和内核 OOM 日志；若进程受 cgroup 限制，再按该进程的 `/proc/<pid>/cgroup` 检查对应 memory controller 的用量、限制和 OOM 计数器。区分全局内存压力与 memcg/其他分配约束后再判断。
- **电源依赖**：RK3588 的电源域与板级 PMIC/regulator 配置分别核对；具体 PMIC 数量、供电连接和时序以板卡原理图与目标 binding 为准

## 边界与注意

- U-Boot 分支与设备对应关系要确认，**跨分支移植补丁常失效**
- DTS 修改必须板上验证（运行时 `/proc/device-tree`），不能只看编译通过
- 具体寄存器/时钟配置查对应芯片 TRM，不要凭印象写
