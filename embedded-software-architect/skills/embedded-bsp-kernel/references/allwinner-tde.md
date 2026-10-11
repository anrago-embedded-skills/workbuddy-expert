# 全志Allwinner BSP 适配

Allwinner BSP 的构建系统、启动链和配置格式随型号、板卡与 SDK 变化。本页列出调查线索；先用手头 SDK 的文档、配置与启动日志确认适用性。

## 启动链

```
BootROM → [板卡实际使用的 loader 阶段] → Linux kernel + 设备树/其他固件
```

`sunxi` 常见于 Allwinner 命名和部分工具/源码路径；它不是启动阶段或工具可用性的保证。

## SDK 结构

下列目录名仅作 SDK 内搜索关键词，不代表固定布局：

```
buildroot/
├── board/allwinner/        # 板级配置
├── device/sunxi/           # 板级配置（老方案）
├── configs/                # defconfig
└── output/images/          # 镜像输出
```

部分 SDK/旧配置可能包含 `sys_config.fex`；是否仍为当前板卡的权威配置，须检查该 SDK 的构建入口和生成步骤。

```text
# SDK 目录中若存在此文件，先通过随包文档确认它是否参与当前板级构建。
sys_config.fex     # 板级配置（早期方案）
```

## 设备树

确认该板构建使用 DTS/DTB、FEX 或 SDK 生成的其他格式；不要假定两种配置能直接互换。若流程需要转换，先在对应 SDK 版本文档或构建脚本中找到确切工具、输入和输出；不要从恢复/传输工具推断配置转换能力。

```sh
# 在目标 Linux shell 查询；该属性是 NUL 结尾字符串。
tr '\0' '\n' < /proc/device-tree/model
```

## 特色注意点

- **`sys_config.fex` 是全志特有**，与设备树是两套体系，迁移时注意
- 型号系列名不能确定当前 SDK、主线支持、内核版本或用户态 ABI；从目标配置、manifest 和运行时版本确认。

## 边界与注意

- **不要把全志 `sys_config` 与设备树混用**，是不同配置体系
- 具体型号的 defconfig 与内核分支需查该板文档
- 如需评估主线或厂商 BSP，按目标 SoC、外设、内核分支和所需组件逐项确认；不以年代或命名推断支持状态。
