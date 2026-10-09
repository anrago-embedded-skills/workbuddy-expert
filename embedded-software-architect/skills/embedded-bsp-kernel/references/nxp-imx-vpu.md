# NXP i.MX BSP 适配

> NXP i.MX 是 Linux 主线内核支持最好的嵌入式平台之一，BSP 维护活跃，社区资料丰富。

## 启动链

```
BootROM → SPL → U-Boot (SPL + FIT) → Kernel + dtb
```

i.MX 平台主线支持完善，多数版本可直接用 NXP 官方 `imx-uboot` + `linux-imx` 仓库。

## SDK 结构

常见两种方式：

| 方式 | 说明 |
|---|---|
| **Yocto（推荐）** | `meta-imx` layer，NXP 官方推荐 |
| **Buildroot** | 社区/第三方维护 |

NXP 官方在Yocto上有 `meta-imx`，包含 imx-uboot、linux-imx 等 layer。

```bash
bitbake-layers show-layers | grep meta-imx
bitbake imx-image              # 构建
```

## 内核

NXP 会长期维护 out-of-tree kernel 分支（`linux-imx`），因为需要 NXP 专有驱动（MIPI CSI、ISP、VPU 等）。

**要点**：主线内核 + NXP BSP 二选一，**不要混用**。混用会因符号缺失导致模块加载失败。

```bash
# 确认内核来源
uname -a
cat /proc/version
```

## 特色注意点

- **BSP 与主线二选一**：out-of-tree 分支含 NXP 专有驱动，主线没有 MIPI/ISP/VPU 等
- **设备树与 BSP 强绑定**：从 BSP 迁移到主线时设备树需重写
- **i.MX8 以后多域（Domain）架构**：电源/资源需按 domain 配置
- SDMA（i.MX6）用于音视频搬运，有专有驱动

## 边界与注意

- **BSP 与主线内核不要混用**，这是最常见的踩坑点
- NXP 文档质量较好（i.MX Linux BSP Reference Manual），优先查官方文档
- 具体芯片（i.MX6/8/9）能力差异大，以该芯片 datasheet 为准