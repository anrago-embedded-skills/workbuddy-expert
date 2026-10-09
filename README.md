# WorkBuddy 专家包 · 嵌入式软件高级工程师

面向 **Linux ARM64** 嵌入式设备的 WorkBuddy 专家包（Agent 型）。

专家代号**磐石**，定位是嵌入式软件高级工程师——BSP / 内核 / 驱动 / 多媒体链路 / Qt 渲染 / 板级取证排障。

## 核心差异

与通用开发专家相比，本专家的交付标准是**目标板实测通过且无回归**，而非"编译+测试通过"。

| 维度 | 通用开发 | 本专家 |
|---|---|---|
| 工作流 | 写 → 验 → 报 | 需求 → **交叉编译** → 部署上板 → **板上验证（验收门）** → 回归 |
| 交付标准 | 编译 + 测试通过 | **板上实测通过 + 无回归** |
| 排障铁律 | — | **证据优先**（崩溃/OOM 先抓现场再动手） |
| 定位方法 | — | 分层定位法（应用→系统→驱动→硬件） |

## 内容结构

```
embedded-software-architect/
├── .codebuddy-plugin/plugin.json      # 元数据 + skill挂载
├── agents/embedded-software-architect.md   # 角色定义（核心）
├── avatars/expert.png
└── skills/                # 12 个内置 skill
    ├── media-pipeline-linux/        # V4L2 · DRM/KMS · UVC · FFmpeg · ALSA · MPP/RGA
    ├── embedded-bsp-kernel/         # U-Boot · 设备树 · 内核模块 · Buildroot/Yocto · systemd
    ├── qt-embedded-rendering/       # 离屏渲染 · EGL/GLES · QML 掉帧定位
    ├── embedded-perf-debug/         # OOM 四种根因定性 · Kernel Oops 符号化 · 性能瓶颈
    ├── embedded-debug-workflow/     # 分层定位法 · 取证驱动 · 进程模型与 IPC
    ├── embedded-peripherals/        # GPIO · I2C · SPI · UART · regulator
    ├── embedded-networking/         # 网络负载 · socket 缓冲区 · fd 泄漏 · TCP 粘包
    ├── data-storage-embedded/       # SQLite · Redis · 掉电一致性 · 存储寿命
    ├── protocols-embedded/          # MQTT · SSL/TLS · 5G 模组 · NDI
    ├── wireless-connectivity/       # WiFi · BLE · Matter · Thread · 漫游性能
    ├── display-compositor-gpu/      # Weston · X11 · OpenCV · RKNPU
    └── storage-hardware-io/         # RAID · PCIe · SATA/NVMe · MIPI · Docker · nginx
```

## 平台覆盖

平台特有内容沉底到各 skill 的 `references/`，主干保持平台无关：

| SoC | 硬件加速路径 |
|---|---|
| **RK3588** | RKMPP 硬编解码 · RGA2 缩放 · Mali-G610 · RKNPU |
| **MTK** | MDP 硬件流水线 |
| **全志 Allwinner** | TDE 2D 加速 / VE / DISP |
| **NXP i.MX** | VPU + GStreamer 官方 plugin |
| **海思 Hi3516** | HiVCodec |
| **国科微** | GKMPP |
| **通用 Linux** | 软解兜底（明确标注性能上限） |

> ⚠️ 注意：不同厂商的 MPP API 互不兼容（如海思 MPP ≠ Rockchip MPP），请查阅对应平台文档。

## 安装

将 `embedded-software-architect/` 目录复制到本地专家市场：

```bash
cp -r embedded-software-architect ~/.workbuddy/plugins/marketplaces/my-experts/plugins/
```

然后在 WorkBuddy 专家中心即可看到，或手动注册：

```bash
python3 <expert-manager>/scripts/register_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/embedded-software-architect
```

## 使用示例

- 我这边有块嵌入式板子出了点问题，想请你帮我排查。请先给我一个系统的排查思路，再动手。
- 帮我设计一个 Linux 多媒体采集管线：UVC 采集 + 硬编解码 + DRM 输出，要考虑性能瓶颈和延迟。
- 我的设备跑一段时间就崩了，内存占用看起来一直在涨。先帮我定位根因，不要急着改代码。

## 版本

当前版本：**0.1.0**

## 许可

[Apache License 2.0](LICENSE)

其中引用的 Linux 内核、Buildroot/Yocto、Qt、FFmpeg、Rockchip MPP 等第三方组件遵循各自原有许可证。