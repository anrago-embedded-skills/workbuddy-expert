# BSP、启动与设备树任务工作流

## 目标与最小输入

将用户报告的启动或 BSP 现象定位到一个可复现的源码/配置差异，并追踪到目标实际选择的启动产物。开始前收集：

- 目标板名称和硬件修订、SoC；未知的字段标为未知，不从 CPU 架构或厂商系列推断板级能力。
- 目标 Linux 上的 `uname -a`、`/proc/version`、`/proc/cmdline`、设备树 `model`，以及对应启动阶段的串口/内核日志。
- 源码/SDK 的路径、提交或版本、工作区改动状态、构建系统与实际配置入口；Yocto 记录 `MACHINE`、kernel provider/recipe，Buildroot 记录输出目录与 `.config`。
- 预期行为、当前产物路径、bootloader 选择内核/DTB/overlay 的证据，以及现有恢复方法。

缺少板号、SDK 版本、完整启动链或加载分区时，仍可只读审查源码、构建配置和已有日志，列出下一步应从 SDK/bootloader 确认的问题。不要因此选择相邻型号的 defconfig、DTB、工具链或刷写工具；也不要把构建结果说成目标运行结果。

## 先按证据分支

| 观测 | 下一项区分证据 | 负责范围 |
|---|---|---|
| 目标设备/子节点不在 `/proc/device-tree` | 从目标树 `dtc -I fs -O dts /proc/device-tree` 导出运行视图；对照节点、父 bus、`status`、overlay 和 bootloader 实际选择 | DTB/overlay/启动链；见[DTB 未生效案例](cases/dtb-not-taking-effect.md) |
| 运行时节点存在，但没有总线设备 | 检查父控制器是否启用/注册、地址和总线枚举；再核对目标 binding 资源 | 设备树/板级外设，可能转 `embedded-peripherals` |
| 有设备但没有 driver 链接 | 比较实际 `compatible`/modalias、内核匹配表、驱动配置/加载状态 | 驱动匹配；转 `linux-device-drivers` |
| probe 返回错误 | 保留原始 errno、资源 provider 日志、节点状态、binding；`-EPROBE_DEFER` 单独追 supplier 和 deferred 状态 | 驱动 probe 和依赖 |
| 内核启动后 rootfs 或服务失败 | 先检查 `root=`、initramfs/根设备和根文件系统；systemd 场景检查目标 unit 的依赖及本次启动日志 | kernel/rootfs 或 service，不归因于外设驱动 |

单一 `dmesg` 文本、某个源码 DTB 或 U-Boot 环境变量都不能单独证明实际加载的 DTB。记录证据采自构建主机、U-Boot 还是目标 Linux。

## 构建与验证边界

1. 找到目标 SDK 的实际 kernel provider、defconfig/config fragment、DTS 输出路径和打包规则。先保存构建配置与工作区差异，优先使用独立输出目录；清理前确认目录归属和可重建性。
2. 用该树的 Kbuild 规则构建 DTS/DTB。`dtc` 单文件编译不能代替 SDK 中的预处理、overlay、签名或镜像打包步骤。修改 binding 时按同一树运行 `dt_binding_check`；DTS schema 用 `make O="$KOUT" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" dtbs_check`，参数须来自目标构建。
3. 追踪编译产物到最终镜像/分区/boot entry，记录文件名、校验和、构建配置及打包输入。核对 bootloader 启动日志/环境与目标 runtime tree；工具或分区名以当前 SDK 文档为准。
4. 分开记录 DTS 编译、schema、内核/镜像构建、bootloader 选择、目标运行时节点、驱动绑定和实际功能结果。没有运行对应步骤时写“未验证”。

HOST 命令模板仅在**目标 Linux 构建主机**上运行：

```sh
make -C "$KSRCTREE" O="$KOUT" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" dtbs_check
```

`KSRCTREE`、`KOUT`、`ARCH`、`CROSS_COMPILE` 是目标 SDK 的参数模板，不是可直接复制的板级配置。目标 Linux 的 runtime tree 只读查询示例：

```sh
tr '\0' '\n' < /proc/device-tree/model
dtc -I fs -O dts /proc/device-tree > running.dts
```

只有在任务明确进入目标部署或烧写阶段、并已从目标文档确认选择的分区/启动槽位和恢复手段后，才把构建产物交付给该步骤。先保留原启动产物和已知可用配置，定义失败时如何回到它；不能通过猜测 `bootcmd`、分区名或厂商下载工具来替代回滚方案。构建、设备树编译和 schema 检查本身不授权写入目标，也不证明硬件工作。

## 交付物

- 现象、目标身份和证据来源的简表；每个候选原因对应一条能区分它的观察。
- 最小的 DTS/config/启动配置差异，及其适用的板卡、SDK 和内核树。
- 可复现的目标构建入口、产物清单/校验和、已执行的 schema/build/boot 检查与结果。
- 预期的目标启动和 runtime-tree 证据、回退到原产物的步骤，以及仍未验证的 SDK/板卡事项。
