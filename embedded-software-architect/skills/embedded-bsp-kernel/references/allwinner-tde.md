# 全志Allwinner BSP 适配

> 全志 BSP 常用 Buildroot，开源社区资料相对较多，部分老平台（如 V3s/V3d）有公开主线支持。

## 启动链

```
BootROM → U-Boot (sunxi SPL) → U-Boot → Kernel + dtb (sun8i-v3s.dts等)
```

全志使用 **sunxi** 命名传统（Allwinner 曾名 Sunxi）。

## SDK 结构

全志 BSP 多基于 Buildroot：

```
buildroot/
├── board/allwinner/        # 板级配置
├── device/sunxi/           # 板级配置（老方案）
├── configs/                # defconfig
└── output/images/          # 镜像输出
```

**传统结构**：`device/sunxi/<board>/` 下有 `sys_config.fex`（全志特有配置文件）。

```bash
# 全志特有 sys_config
sys_config.fex     # 板级配置（早期方案）
```

## 设备树

全志老方案用 `sys_config.fex`，新方案改用设备树（`.dts`），转换需 `sunxi-fel` 工具生态。

```bash
cat /proc/device-tree/model
```

## 特色注意点

- **`sys_config.fex` 是全志特有**，与设备树是两套体系，迁移时注意
- 早期方案（V3s/V3s/V831）资料多，新系列资料少
- 部分老平台内核版本较老（4.x），C 库与工具链兼容性要注意

## 边界与注意

- **不要把全志 `sys_config` 与设备树混用**，是不同配置体系
- 具体型号的 defconfig 与内核分支需查该板文档
- 老平台（sun8i-v3s 等）有主线支持，新平台多依赖厂商 BSP