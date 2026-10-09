# 海思 HiSilicon Hi3516 BSP 适配

> 海思 SDK 通常由原厂或方案商提供，包含 Linux kernel、u-boot、MPP、IVE、OAL 等私有组件。

## 启动链

```
BootROM → Hi-Boot → Kernel + dtb
```

海思使用 **Hi-Boot**（MPP 启动），传统上有 boot 阶段单独加载地址的流程。

## SDK 结构

```
Hi3516_SDK_Vx.y.z.zkk/
├── Hi3516_SDK_Vxxx/          # SDK 主目录
│   ├── Hi3516_Vxxx/         # 芯片目录
│   ├── MPP/                 # 多媒体平台（私有）
│   ├── IVE/                 # 智能视觉引擎
│   ├── OAL/                 # 操作系统抽象层
│   ├── kernel/              # 内核
│   └── tools/               # 工具
├── Hi3516_Vxxx/mpp_component/   # MPP 组件
├── Hi3516_Vxxx/mpp_sample/      # MPP 样例
└── Hi3516_Vxxx/vencdec_sample/
```

**Hi3516_SDK** 是关键概念——海思以 SDK 整包形式提供，不是在开源仓库上开发。

## 特色组件

| 组件 | 作用 |
|---|---|
| **MPP** | 海思多媒体处理平台（**与 Rockchip MPP 完全不同**） |
| **IVE** | 智能视觉引擎（图像算法加速） |
| **OAL** | OS 抽象层（osal_* API，MPP 内部用） |
| **VO** | 视频输出子系统 |

## 常用操作

```bash
# 烧写（海思有专用烧写工具 hi3516/HiTool）
# 编译
make ARCH=arm CROSS_COMPILE=arm-himix...linux-gnueabihf-
```

## 边界与注意

- **海思 MPP ≠ Rockchip MPP**，接口/类型/流程都不同，这是最易踩的坑
- 同系列不同型号（Hi3516C/D/E/CV300）**能力差异大**，SDK 不通用
- SDK 为整包交付，升级需整包替换，注意与已有改动合并
- 具体寄存器/时钟/引脚配置以该型号用户手册为准
- 社区公开资料集中在老型号（Hi3516C/E），新资料需原厂文档