# 国科微Goke BSP 适配

> 国科微 SDK 通常由芯片原厂/方案商提供，包含 kernel、uboot、GKMPP、GKAI 等组件。

## SDK 结构

国科微以 SDK 整包形式提供，典型内容：

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

| 组件 | 作用 |
|---|---|
| **GKMPP** | 国科微多媒体处理平台（编解码） |
| **GKAI** | AI 加速（部分型号） |
| **IVE** | 图像/视频处理（视型号而定） |

## 通用排查（不依赖具体 SDK）

在缺少详细文档时，用通用路径推进：

```bash
uname -a
cat /proc/device-tree/model
dmesg | head -100              # 确认驱动加载情况
media-ctl -p                   # 摄像头拓扑
v4l2-ctl --list-devices
ls /sys/class/video4linux/
```

```bash
# 确认 SDK 实际提供的接口
find / -name "*gk*mpp*" 2>/dev/null | head
find / -name "lib*.so" | grep -i gk
```

## 边界与注意

- **GKMPP 与其他平台 MPP 完全不同**，不可移植、不要类比
- 国科微**文档可得性是主要挑战**，优先确认手上 SDK 实际提供的接口
- 所有命令、库名、plugin 名**必须实际确认**，不要依赖通用印象
- 具体型号能力与寄存器配置以该型号官方文档为准
- 未在具体型号验证的推断必须明确标注为待验证