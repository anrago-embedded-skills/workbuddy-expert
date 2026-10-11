# 国科微Goke BSP 适配

国科微相关 BSP 可能由芯片原厂或方案商提供。型号、发行包和 SDK 版本会决定其源码、工具链与可选组件；本页的标识仅作为检索候选，不保证目标包中存在。

## SDK 结构

先记录收到的包名、版本、来源和校验值，再按 README、manifest 与构建入口确认结构。以下目录是搜索线索，不是固定目录约定：

```
Gxxx_SDK/
├── kernel/
├── uboot/
├── gk_mpp/                 # 多媒体处理平台
├── gkai/                   # AI 推理引擎
├── buildroot/ 或 rootfs/
└── tools/
```

**要点**：具体目录名与组件随型号与SDK 版本变化，需以实际 SDK 为准。

## 特色组件

| 候选标识 | 需要从目标 SDK 核实 |
|---|---|
| GKMPP | 库、头文件、内核接口、目标型号和 ABI 是否匹配 |
| GKAI | 是否包含可执行运行库、模型工具与目标芯片支持 |
| IVE | 是否为该 SDK 的组件、其 API 及硬件能力 |

## 通用排查（不依赖具体 SDK）

只在目标机工具已安装且任务属于对应子系统时使用这些标准只读查询；它们不会证明厂商加速库可用：

```sh
# 在目标 Linux shell；运行时工具可能未安装。
uname -a
tr '\0' '\n' < /proc/device-tree/model
dmesg | head -100              # 确认驱动加载情况
media-ctl -p                   # 摄像头拓扑
v4l2-ctl --list-devices
ls /sys/class/video4linux/
```

```bash
# 在已确认的 SDK 根目录搜索候选文件，不遍历整台目标机。
find "$SDKROOT" -type f -iname '*mpp*' -print
find "$SDKROOT" -type f -name 'lib*.so' -print | grep -i gk
```

## 边界与注意

- 不根据组件缩写推断接口兼容性；比较实际头文件、库、ABI、内核接口和 SDK 文档。
- 不存在于目标 SDK/镜像的工具、库名或 plugin 名不能作为执行步骤。若资料不足，将其列为供应商/方案商需要提供的文件和能力说明。
- 具体型号能力与寄存器配置以该型号官方文档为准
- 未在具体型号验证的推断必须明确标注为待验证
