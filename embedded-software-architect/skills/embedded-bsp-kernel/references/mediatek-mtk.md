# 联发科 MTK BSP 适配

> MTK BSP 通常由芯片原厂或方案商提供，常见基于 Buildroot 或 Yocto，含MTK 私有组件。

## 启动链

```
BootROM → MTK U-Boot (preloader) → U-Boot → Kernel + dtb
```

MTK 有 **preloader / lk / bootloader** 多阶段结构，与 Rockchip 的简洁链路不同。

## SDK 结构

MTK BSP 通常来自 **BSP 包**（解压后含 kernel、u-boot、rootfs、preloader 等），而非直接 clone 开源仓库。

```
bsp/
├── kernel/          # MTK 内核分支
├── u-boot/          # MTK U-Boot
├── preloader/       # MTK 第一阶段（专有）
├── toolchain/       # MTK 工具链
└── rootfs/
```

## 特色注意点

- **preloader 是 MTK 专有的**，与通用 U-Boot 流程不同，升级固件时需完整包
- **内核 patch 体系是 MTK 私有格式**（`*.patch` 在特定目录），应用官方 patch 前确认基线
- **工具链可能非标准**（MTK 自带 toolchain），跨平台交叉编译时注意
- **DTBO / dtbo 分区**：部分平台设备树分区独立，运行时以 dtbo.img 为准

## 调试

```bash
uname -a
cat /proc/device-tree/model
getprop ro.build.fingerprint    # Android 平台常见
```

## 边界与注意

- MTK BSP **高度依赖原厂包**，公开资料有限，具体配置查该包文档
- 不要把RK/全志的 U-Boot/设备树结构假设套到 MTK
- 应用 MTK 官方 patch 前必须确认内核基线版本
- 具体寄存器/时钟配置以该芯片 TRM 为准