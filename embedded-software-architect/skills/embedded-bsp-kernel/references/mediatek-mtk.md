# 联发科 MTK BSP 适配

MediaTek BSP 的包、构建系统和专用组件因芯片系列、产品方案与版本而异。用目标发行包的文档、manifest 和构建环境确认适用内容。

## 启动链

```
BootROM → [该平台实际存在的 preloader/bootloader 阶段] → kernel + 设备树/启动镜像
```

preloader、LK、U-Boot、Android boot image 或其他阶段是否存在，以设备启动日志、分区表和 SDK 配置为准；不要按平台名称假定启动链或镜像格式。

## SDK 结构

如果使用供应商 BSP 包，先从其实际内容、manifest 和构建说明确认 kernel、bootloader、rootfs 和工具链的来源；目录示意不保证包中含有所有部件。

```
bsp/
├── kernel/          # MTK 内核分支
├── u-boot/          # MTK U-Boot
├── preloader/       # MTK 第一阶段（专有）
├── toolchain/       # MTK 工具链
└── rootfs/
```

## 特色注意点

- 若存在 preloader、厂商 patch、独立 DTBO 或专用工具，先由启动日志、分区布局和 SDK 文档确认具体角色与版本；不要据此要求全量镜像升级。
- 比较 patch 的基线提交、应用顺序和目标构建配置；以 SDK 指定的工具链 ABI 和前缀为准。

## 调试

```sh
# 在目标 Linux shell 查询。
uname -a
tr '\0' '\n' < /proc/device-tree/model
```

Android 目标可在 Android 用户空间查询 build fingerprint；该命令不适用于一般 Linux rootfs：

```sh
getprop ro.build.fingerprint
```

## 边界与注意

- 不要把其他厂商的 bootloader、设备树路径、工具或刷写流程套用到目标平台。
- 应用 MTK 官方 patch 前必须确认内核基线版本
- 具体寄存器/时钟配置以该芯片 TRM 为准
