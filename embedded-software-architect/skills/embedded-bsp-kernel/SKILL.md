---
name: embedded-bsp-kernel
description: |
  用于排查嵌入式 Linux 启动链、内核与根文件系统构建配置、systemd 服务启动依赖，以及确认目标机实际启动的镜像和运行时设备树。
---

# embedded-bsp-kernel

Linux BSP 工作覆盖启动固件、内核、设备树、根文件系统和服务启动。修改前先确认板卡、SoC、正在运行的内核版本、构建系统，以及设备实际加载的产物。

## 任务工作流

目标是把启动链或 BSP 改动追溯到可复现的目标产物，并说明其构建与启动证据。最低输入是用户观察到的现象、目标板/SoC（未知时注明）、运行内核和启动日志、源码或 SDK 与构建入口；未知板卡细节时仍可检查源树和收集运行时证据，但不能推定要构建或启动哪个镜像。按设备未枚举、驱动未匹配、probe 错误/defer、设备树未进入运行时视图或服务启动失败分支；每个结论都要对应观测来源。交付最小 patch、复现的构建入口、schema/编译/启动各自的结果，以及可恢复到已知启动产物的办法。具体步骤见[任务工作流](references/task-workflow.md)；DTB 已构建但目标节点未生效时读[DTB 未生效案例](references/cases/dtb-not-taking-effect.md)。

跨领域任务、命令和交付约定见[通用工程工作流](../embedded-debug-workflow/references/engineering-workflow.md)；证据来源和验证边界见[验证策略](../embedded-debug-workflow/references/validation-policy.md)。

## 主用与配合

本技能主用于启动链、内核/根文件系统构建、systemd 服务启动顺序与依赖，以及确认引导实际使用的镜像、内核和运行时设备树。若目标设备节点没有出现在运行时设备树，先核实启动产物、overlay 和加载路径；服务未启动时核对目标机 unit、依赖顺序和启动日志。

- 板级总线、引脚、供电和外设节点属性：配合 [embedded-peripherals](../embedded-peripherals/SKILL.md)。
- 驱动源码、匹配表、probe/remove、错误路径和生命周期：配合 [linux-device-drivers](../linux-device-drivers/SKILL.md)。
- systemd 服务启动：使用本技能下方示例。

## 平台参考

按平台、SoC 和 SDK 选择对应参考，并先核对文档覆盖的型号与 BSP 是否适用于目标。未匹配的资料可作背景对照；确认适用性前不要沿用其中的参数或能力结论。

- [全志 Allwinner TDE](references/allwinner-tde.md)：调查 Allwinner TDE 平台时，核对目标型号与 SDK。
- [通用 Linux BSP](references/generic-linux.md)：目标没有下列专用平台文档时。
- [Goke Micro G300](references/goke-micro-g300.md)：目标为 Goke Micro G300 时。
- [HiSilicon Hi3516](references/hisilicon-hi3516.md)：目标为 Hi3516 系列时。
- [MediaTek MTK](references/mediatek-mtk.md)：目标 BSP 为 MediaTek MTK 时。
- [NXP i.MX BSP](references/nxp-imx-vpu.md)：调查 NXP i.MX 启动、构建或 VPU 时；按具体型号和 BSP 核实功能适用性。
- [Rockchip RK3588](references/rockchip-rk3588.md)：目标 SoC 为 RK3588 时。

## 确认运行系统

在**目标板 Linux shell**收集版本和启动参数：

```sh
uname -a
cat /proc/version
cat /proc/cmdline
tr '\0' '\n' < /proc/device-tree/model
```

启动链取决于板卡。根据该板厂商文档和串口日志建模；链路可能包含 ROM、SPL/TPL、U-Boot 或其他 loader、TF-A、OP-TEE、其他安全固件，以及内核，组合并不固定。不要假设每个阶段都存在，也不要假设内核使用的就是刚编辑的 DTB。在 **U-Boot 控制台**查看启动命令及目标实际使用的文件/地址，再检查已加载设备树：

```text
printenv bootcmd bootargs
# fdtfile/fdt_addr_r 是常见变量名，但目标配置可能使用其他名称或不定义它们。
printenv fdtfile fdt_addr_r
# 仅当已确认 fdt_addr_r 指向当前已加载的 FDT 时执行：
fdt addr ${fdt_addr_r}
fdt print /
```

`printenv` 与 `fdt print` 是只读观察；不要用 `saveenv` 或修改 FDT 的命令替代取证。变量名因 U-Boot 板级配置而异，参见 [U-Boot environment 文档](https://docs.u-boot.org/en/latest/usage/environment.html)。

## 按启动阶段定位

先找出启动日志中最早缺失证据的阶段；阶段是否存在、具体串口和日志内容都由板卡启动设计决定。

| 阶段与现象 | 优先检查 |
|---|---|
| 上电后没有早期串口输出 | 电源、复位、启动绑带、串口接线/波特率，以及板卡 ROM 恢复方式 |
| SPL/TPL 或 DDR 初始化失败 | 该板匹配的 DDR firmware/training 配置和训练日志；不要套用其他板的参数 |
| U-Boot、TF-A、OP-TEE 或其他 loader 阶段失败 | 仅检查此板实际使用的固件、镜像组合、加载地址和交接参数 |
| 内核没有串口日志 | kernel image 是否被加载、`console=`/`earlycon`、串口驱动配置，以及 image 与 DTB 的交接 |
| 内核启动但 rootfs 挂载失败 | `root=` 和启动参数、目标根设备驱动是否 built-in，或是否包含在 initramfs 中 |
| 根文件系统可用但外设未绑定 | 运行时 DT、节点状态、binding、时钟/复位/电源/pinctrl 等 probe 依赖 |
| 驱动已工作但应用或服务未启动 | rootfs 文件、init/systemd 选择、挂载依赖和 service 顺序 |

## 检查和验证设备树

目标板 Linux 上的 `/proc/device-tree` 包含 bootloader 修改和 overlay 的运行时视图。它是文件系统格式，使用 `dtc -I fs` 解码；保存的 DTB 才使用 `-I dtb`。

在**目标板 Linux shell**导出运行时设备树；命令只读取 `/proc/device-tree`，并将 DTS 写入当前目录：

```sh
dtc -I fs -O dts /proc/device-tree > running.dts
```

在**Linux 构建主机**检查完整导出的目标 runtime tree 时，将参数设为目标树副本路径；不能用主机 `/proc` 替代。保存的 DTB 也在主机按 `-I dtb` 解码：

```sh
RUNTIME_TREE_COPY=/path/to/exported-target-device-tree
dtc -I fs -O dts "$RUNTIME_TREE_COPY" > running.dts
dtc -I dtb -O dts board.dtb > board.dts
```

带 C 预处理 include、标签或 overlay 的源文件应通过目标内核或 BSP 的 Kbuild 规则构建，不要直接把裸 `dtc` 当完整编译流程。语法编译之后，再使用同一目标内核树和配置运行 schema 检查：

```sh
# 在 Linux 构建主机运行；KOUT、ARCH 和 CROSS_COMPILE 要指向目标内核构建。
make O="$KOUT" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" dtbs_check
```

必要时用 `DT_SCHEMA_FILES=<binding-path-or-pattern>` 缩小检查范围；修改 binding 时也运行 `dt_binding_check`。供应商树可能有旧版或私有 schema，要按目标树结果判断。参见 [Devicetree schema 文档](https://docs.kernel.org/devicetree/bindings/writing-schema.html)。

## 构建目标内核和外部模块

`ARCH` 和交叉编译器依据**目标内核**选择，不依据构建主机。AArch64 通常使用 `aarch64-linux-gnu-` 这类 AArch64 工具链；`arm-linux-gnueabihf-` 是 32-bit ARM hard-float 的常见前缀，只在目标内核为 32-bit ARM 时使用。优先使用该板 Yocto/Buildroot SDK 附带的实际编译器和环境。

下面在 **Linux 构建主机**示范 AArch64 内核 out-of-tree 构建。先将路径与配置名替换为目标 BSP 提供值；`KOUT` 是内核输出目录，`BOARD_DEFCONFIG` 是目标树中的 defconfig 名称：

```sh
KSRCTREE=/path/to/linux
KOUT=/path/to/linux-out
ARCH=arm64
CROSS_COMPILE=aarch64-linux-gnu-
BOARD_DEFCONFIG=vendor_board_defconfig

make -C "$KSRCTREE" O="$KOUT" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" "$BOARD_DEFCONFIG"
make -C "$KSRCTREE" O="$KOUT" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" olddefconfig
# AArch64 目标构建 Image；32-bit ARM 目标应将 Image 改为 zImage。
make -C "$KSRCTREE" O="$KOUT" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" -j"$(nproc)" Image modules dtbs
```

32-bit ARM 目标应改用 `ARCH=arm` 和该目标的 ARM 工具链。kernel source、输出目录、`.config`、编译器、生成头文件和 `Module.symvers` 应属于同一次目标构建。加载前比较目标板 `uname -r`、内核配置、模块 `vermagic` 和模块签名策略。外部模块通过 Kbuild 对已配置的目标内核输出目录构建：

```sh
# 在模块源码目录、Linux 构建主机执行；KOUT 必须是匹配的已配置内核构建目录。
make -C "$KOUT" M="$PWD" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" modules
```

目标内核必须启用模块支持。`modules_prepare` 准备头文件，但在 `CONFIG_MODVERSIONS=y` 时不会生成 `Module.symvers`；这种配置需要使用匹配的完整内核构建。外部模块细节见 [Kbuild 文档](https://docs.kernel.org/kbuild/modules.html)。

为保证干净重建可复现，将内核配置差异保存回维护中的 board defconfig/config fragment、Yocto layer/recipe 或 Buildroot 配置；不要只留在临时输出目录的 `.config` 或被构建系统重置的源码树里。驱动 patch 也应保存在受版本控制的 layer 或外置源码中，并记录对应的构建入口。

Buildroot 的命令和输出目录随配置而变，以生成的 `.config`、package target 和 `output/build/linux-*` 为依据。Yocto 中先确认 layer、实际 kernel provider 和 recipe，再构建该 provider 的 `virtual/kernel` 或完整 image。不要把别的 BSP 的 task 名称直接复制过来。

## platform driver 匹配与加载

Device Tree 匹配应将目标 binding 支持的 `compatible` 放入驱动 `.of_match_table`。`MODULE_DEVICE_TABLE(of, ...)` 为模块导出用户态加载工具使用的 alias；它本身不执行 driver-core 匹配。`.driver.name` 是另一个驱动标识。remove callback 按目标内核头文件选择：上游 v6.10 中 `.remove` 返回 `int`，新驱动可用 `.remove_new`；上游 v6.11 及之后 `.remove` 返回 `void`。厂商内核可能回移植接口，须以目标树 `include/linux/platform_device.h` 为准。

probe 没有执行时，分别检查运行节点及 `status`、父总线/控制器、内核配置、驱动注册、compatible、模块是否加载及 deferred-probe 状态。使用目标 binding 和 `dmesg` 区分“设备未枚举”“没有匹配”“模块未加载”“probe defer/失败”。compatible 匹配不代表硬件连线或资源描述正确。

probe 依赖的时钟、regulator、reset、pinctrl、GPIO、IRQ、firmware 或 supplier device 尚未就绪时，保留 provider 错误；收到 `-EPROBE_DEFER` 就按规则返回。仅当目标树 `include/linux/device.h` 声明 `dev_err_probe()` 时使用该 helper 记录 probe 上下文和 deferred reason；较旧或裁剪过的 BSP 若没有此 API，使用目标树支持的日志函数并原样返回 errno，尤其不要吞掉或改写 `-EPROBE_DEFER`。不要只按版本号假设该 helper 存在，因为厂商树可能回移植 API。尽早 defer，避免注册子设备或用户接口后再 defer。参考 [内核驱动模型文档](https://docs.kernel.org/driver-api/driver-model/driver.html) 与 [`dev_err_probe()` 文档](https://docs.kernel.org/driver-api/infrastructure.html)。

本节用于确认运行时节点、compatible、驱动注册和模块加载状态。节点已存在而问题落在驱动匹配表、probe 错误处理或生命周期时，转到 [linux-device-drivers](../linux-device-drivers/SKILL.md)；板级资源属性或总线配置不符时，转到 [embedded-peripherals](../embedded-peripherals/SKILL.md)。

## systemd 服务

```ini
# /etc/systemd/system/myapp.service
[Unit]
Description=My Application
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/myapp --flag
Restart=on-failure
RestartSec=5
WorkingDirectory=/opt/myapp
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```sh
# 在目标板 Linux shell 执行。
systemd-analyze verify /etc/systemd/system/myapp.service
systemctl daemon-reload
systemctl enable --now myapp
systemctl status myapp
journalctl -b -u myapp
```

`daemon-reload` 让目标 systemd 重新读取 unit；`enable --now` 会同时持久启用并立即启动该服务，只有任务需要这项状态变更时才执行。根据真实依赖选择 `After=`、`Requires=` 或 `Wants=`。`After=` 只排序启动，不会启动对应单元。应用不需要 root 时使用专用服务账户。

## 记录证据和验证范围

区分构建主机输出、bootloader 观测、目标日志和板卡运行结果。烧写前确认具体产物和可用恢复路径。分别说明是否做过 schema 验证、内核/模块编译、启动、驱动绑定和长时间运行验证；其中一种不能证明其余结果。
