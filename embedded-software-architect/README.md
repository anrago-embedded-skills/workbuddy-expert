# 嵌入式软件高级工程师（磐石）

面向 **Linux ARM64** 设备的嵌入式软件高级工程师专家。BSP / 内核 / 驱动 / 多媒体链路 / Qt 渲染 / 板级取证排障，交付标准是**目标板实测通过且无回归**。

## 类型

Agent 型（单个 AI 专家）

**定位边界**：聚焦 Linux 用户态 / BSP / 多媒体，**不涉及 MCU 裸机固件**（RTOS、寄存器级单片机编程）。市场上`embedded-firmware-engineer` 覆盖的是 MCU 方向，两者互补。

## 核心特征

与通用开发专家的关键差异：

| 维度 | 通用开发 | 本专家 |
|---|---|---|
| 工作流 | 写 → 验 → 报 | 需求 → **交叉编译** → 部署上板 → **板上验证（验收门）** → 回归 |
| 交付标准 | 编译 + 测试通过 | **板上实测通过 + 无回归** |
| 排障铁律 | — | **证据优先**（崩溃/OOM 先抓现场再动手） |
| 定位方法 | — | 分层定位法（应用→系统→驱动→硬件） |

## 内置 Skill（12 个）

| skill | 覆盖内容 |
|---|---|
| `media-pipeline-linux` | V4L2 · DRM/KMS · UVC · FFmpeg · GStreamer · ALSA + RKMPP/RGA2 |
| `embedded-bsp-kernel` | U-Boot · 设备树 · 内核模块 · Buildroot/Yocto · systemd |
| `qt-embedded-rendering` |离屏渲染 · EGL/GLES 后端 · QML 掉帧定位 |
| `embedded-perf-debug` | OOM 四种根因定性 · Kernel Oops 符号化 · 性能瓶颈 |
| `embedded-debug-workflow` | 分层定位法 · 取证驱动 · 长跑验证 |
| `embedded-peripherals` | GPIO · I2C · SPI · UART · regulator |
| `embedded-networking` | 网络负载 · socket 缓冲区 · fd 泄漏 · TCP 粘包 · 重连 |
| `data-storage-embedded` | SQLite · Redis · 掉电一致性 · fsync · 存储寿命 |
| `protocols-embedded` | MQTT · SSL/TLS · 5G 模组 · NDI · 协议转换 |
| `wireless-connectivity` | WiFi · BLE · Matter · Thread · 漫游性能 |
| `display-compositor-gpu` | Weston · X11 · EGL/GLES · OpenCV · RKNPU |
| `storage-hardware-io` | RAID · PCIe · SATA/NVMe · MIPI · Docker · 多线程 · nginx |

## 平台覆盖

平台特有内容沉底到各 skill 的 `references/`，主干保持平台无关：

- **RK3588**：RKMPP 硬编解码 · RGA2 缩放 · Mali-G610 · RKNPU · CMA 与 0 swap 特性
- **MTK**：MDP 硬件流水线
- **全志**：TDE 2D 加速 / VE / DISP
- **NXP i.MX**：VPU + GStreamer 官方 plugin
- **海思 Hi3516**：HiVCodec（⚠️ 海思 MPP ≠ Rockchip MPP）
- **国科微**：GKMPP
- **通用 Linux**：软解兜底（明确标注性能上限）

## 使用示例

- 我这边有块嵌入式板子出了点问题，想请你帮我排查。请先给我一个系统的排查思路，再动手。
- 帮我设计一个 Linux 多媒体采集管线：UVC 采集 + 硬编解码 + DRM 输出，要考虑性能瓶颈和延迟。
- 我的设备跑一段时间就崩了，内存占用看起来一直在涨。先帮我定位根因，不要急着改代码。

## 头像

头像在 `avatars/expert.png`（512×512 PNG）。如需替换为自定义头像，要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到本地专家市场目录下（默认 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/`）：

```bash
# 1. 复制专家包到市场目录
cp -r embedded-software-architect ~/.workbuddy/plugins/marketplaces/my-experts/plugins/

# 2. 校验（可选）
python3 <expert-manager>/scripts/validate_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/embedded-software-architect

# 3. 注册，使其在专家中心可见
python3 <expert-manager>/scripts/register_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/embedded-software-architect
```

也可以直接编辑市场的 `marketplace.json` 手动登记，或在 WorkBuddy 专家中心手动导入。

## 打包分享

```bash
python3 <expert-manager>/scripts/package_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/embedded-software-architect
```

## 版本

当前版本：**0.1.0**

语义化版本说明：
- `0.x.y` — 早期版本，内容持续调整
- `x.0.0` — 功能稳定
- `x.y.0` — 向后兼容的功能新增
- `x.y.z` — 向后兼容的缺陷修复

## 许可

本专家包采用 [Apache License 2.0](../LICENSE) 授权。

其中引用的 Linux 内核、Buildroot/Yocto、Qt、FFmpeg、Rockchip MPP 等第三方组件遵循各自原有许可证，本项目不对其作任何声明或担保。