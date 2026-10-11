# NXP i.MX BSP 适配

i.MX 的启动、内核、媒体和加速能力随具体 SoC、板卡、BSP 分支及发行版而变。先确认型号、当前 SDK 发布、运行内核和目标功能所需的驱动。

## 启动链

```
BootROM → [板卡实际使用的 loader 阶段] → kernel + DTB/boot image
```

从启动日志、boot 配置和对应 BSP release note 确认阶段、仓库/分支与镜像格式；不要仅凭 i.MX 名称选择上游或厂商构建树。

## SDK 结构

从当前 SDK/build environment 识别构建系统；以下是调查项，不表示目标一定使用其中之一：

| 方式 | 检查内容 |
|---|---|
| Yocto | 当前 build 是否包含 i.MX layer；实际 `MACHINE`、kernel provider、image recipe 与版本 |
| Buildroot | defconfig、package/source revision、toolchain ABI 及 SDK 维护者 |

如 SDK 使用 Yocto，可用标准 layer/recipe 查询查出其实际 provider：

```bash
# 在 Yocto Linux 构建主机、已初始化的 build environment 中运行；仅查询 layer/recipe。
bitbake-layers show-layers
bitbake-layers show-recipes | grep -i imx
```

只构建从当前 build 环境确认的 recipe；不要把某个示例 image 名称当作跨版本固定目标。

## 内核

某些功能可能需要 BSP 专有驱动或用户态组件；逐项对照目标 BSP、主线驱动、设备树 binding 和所需用户 ABI。不要混合不同内核构建的头文件、符号版本和模块产物。

```bash
# 在目标 Linux shell 确认运行内核来源线索。
uname -a
cat /proc/version
```

## 特色注意点

- 设备树、电源域、DMA 和媒体能力以该芯片文档、板级资料、binding 及实际配置为准；不从 `i.MX6/8/9` 系列名推断组件或功能。

## 边界与注意

- 对照该目标版本的 NXP Linux BSP Reference Manual、release note 和 SDK 内源码；资料需精确到产品/版本。
- 具体芯片（i.MX6/8/9）能力差异大，以该芯片 datasheet 为准
