# WorkBuddy 专家包 · 嵌入式软件高级工程师

面向 **通用嵌入式 Linux** 工程的 WorkBuddy 专家包（Agent 型）。主干独立于厂商，架构、ABI 和硬件差异按目标 BSP/SDK 确认；ARM32/ARM64 示例不构成其他架构已验证的保证。

专家代号**磐石**，定位是嵌入式软件高级工程师——BSP / 内核 / 驱动 / 多媒体链路 / Qt 渲染 / 板级取证排障。

## 工程目标

本专家以**目标板功能及相关回归通过**为产品验收目标，分别报告代码检查、构建、部署和板测的实际状态。没有目标板时可继续完成离线工作，交付标记为“待板测”，不预填实测成功。

| 层次 | 内容 |
|---|---|
| 通用工程底座 | 任务契约、证据分支、命令前提、构建身份、验收和恢复 |
| 领域工作流 | BSP/驱动、设备树、诊断、媒体、通信与数据/块设备 |
| 平台适配 | 按实际型号、SDK 和能力补充厂商差异 |
| 验证记录 | 来源核对、静态/工具测试、目标构建、仿真与指定板卡结果分别标注 |

多步骤任务使用 [工程流程](embedded-software-architect/skills/embedded-debug-workflow/references/engineering-workflow.md) 与 [验证规范](embedded-software-architect/skills/embedded-debug-workflow/references/validation-policy.md)。案例中的合成输入用于学习与评测，不冒充实机记录。

## 内容结构

```
embedded-software-architect/
├── .codebuddy-plugin/plugin.json      # 元数据 + skill挂载
├── agents/embedded-software-architect.md   # 角色定义（核心）
├── avatars/expert.png
└── skills/                # 13 个内置 skill
    ├── media-pipeline-linux/        # V4L2 · DRM/KMS · UVC · MIPI · FFmpeg · ALSA
    ├── embedded-bsp-kernel/         # 启动/bring-up · binding · 内核构建 · Buildroot/Yocto
    ├── linux-device-drivers/        # 生命周期 · IRQ/锁 · MMIO/DMA · 电源管理 · ABI
    ├── qt-embedded-rendering/       # 离屏渲染 · EGL/GLES · QML 掉帧定位
    ├── embedded-perf-debug/         # 全局/cgroup OOM 取证 · Oops 解码 · 性能瓶颈
    ├── embedded-debug-workflow/     # 通用取证 · 进程/IPC · 可选应用运行环境参考
    ├── embedded-peripherals/        # GPIO · I2C · SPI · UART · regulator
    ├── embedded-networking/         # 网络负载 · socket 缓冲区 · fd 泄漏 · TCP 粘包
    ├── data-storage-embedded/       # SQLite · Redis · 掉电一致性 · 存储寿命
    ├── protocols-embedded/          # MQTT · SSL/TLS · 5G 模组 · NDI
    ├── wireless-connectivity/       # WiFi · BLE · Matter · Thread · 漫游性能
    ├── display-compositor-gpu/      # Weston · X11 · EGL/GPU · 可选视觉推理参考
    └── storage-hardware-io/         # RAID · PCIe · SATA/NVMe · 有界文件测速
```

## 技能选择与读取

每个领域任务按目标和证据选择主技能，通过宿主实际提供的机制取得正文后应用；名称、description 和目录链接不等于已加载。完整正文已经由宿主提供时可复用。跨领域证据出现后再补读辅助技能和条件参考，并在进度中简要记录已读取的来源。

MIPI 链路参考归媒体技能；Docker/nginx、应用线程和 epoll 参考归通用排障；OpenCV/NPU 保留为图形技能的视觉扩展。内核 IRQ/workqueue/锁仍归驱动技能，容器 OOM 归性能技能。保留 13 个技能名称和挂载，避免既有入口失效。

Agent 文件内的 Markdown 链接相对该 Agent 文件目录，技能内的参考链接相对各自 SKILL.md 目录。运行时能否发现和读取这些文件仍需在 WorkBuddy 中验证。

## 平台覆盖

平台特有内容沉底到各 skill 的 `references/`，主干保持平台无关：

| 平台参考 | 调查范围（以准确型号、SDK 与驱动为准） |
|---|---|
| **RK3588** | MPP/RGA · GPU/NPU · CMA · 板级依赖 |
| **MTK** | MDP 硬件流水线 |
| **全志 Allwinner** | 显示、2D 与视频引擎，核对具体芯片和 SDK 接口 |
| **NXP i.MX** | 核对具体型号/BSP 的 VPU 与可用 GStreamer 插件 |
| **海思 Hi3516** | 厂商媒体 SDK 与 BSP；核对具体型号及运行架构 |
| **国科微** | 厂商媒体 SDK 与 BSP；核对实际组件/API |
| **通用 Linux** | 软解兜底（明确标注性能上限） |

这些文件提供平台调查入口，不表示整个芯片系列具有相同能力，也不表示示例已通过板测。不同厂商的 MPP API 不能互相替代；准确型号可能使用 ARM32，不能套用 ARM64 工具链。

## 取证工具与教学案例

专家包内提供 [collect-evidence.sh](embedded-software-architect/skills/embedded-debug-workflow/scripts/collect-evidence.sh)，用于基础环境、内核日志或指定进程快照；细节见 [取证说明](embedded-software-architect/skills/embedded-debug-workflow/references/evidence-collection.md)。工具不自动 SSH、不改硬件/服务设置；只写入指定的新报告目录。

以下在包含 `embedded-software-architect/` 的目录中，用 **TARGET Linux shell** 执行；报告目录必须尚不存在，请选择本次独有的路径：

```sh
sh embedded-software-architect/skills/embedded-debug-workflow/scripts/collect-evidence.sh \
  --mode env --output /tmp/embedded-evidence-session-001
```

在 HOST 上检查已导出的文件快照时，使用 POSIX shell 并显式指定 `--source-root`；它不替代实时目标采集。报告的 `manifest.json` 和 `summary.txt` 记录来源、缺失/失败/截断项；退出成功不表示设备健康，`partial` 也不能忽略。

教学案例覆盖 DTB 生效、probe defer、卸载竞态、DMA 所有权、memcg OOM、媒体掉帧、网络恢复和持久化恢复。它们展示完整工程推理与验收计划，不是实机成功记录。[内容评测矩阵](tests/content-scenarios.md) 用于记录对照与技能组的实际行为，不能仅凭回答更长宣称效果提高。

## 本地校验

在仓库根目录执行：

```bash
python3 scripts/validate_expert.py embedded-software-architect
python3 -m unittest discover -s tests -p 'test_*.py'
```

校验工具检查 JSON 入口、技能挂载、必需 frontmatter、显式本地 Markdown/Shell helper 链接，以及参考文件是否能从所属技能入口经链接到达；工具测试使用临时文件夹具，不访问目标硬件。它们不替代 WorkBuddy 实际选择/读取、内核编译或目标板验证。路由用例见 [tests/expert-scenarios.md](tests/expert-scenarios.md)，内容评测见 [tests/content-scenarios.md](tests/content-scenarios.md)。

## 安装

将 `embedded-software-architect/` 目录复制到本地专家市场：

```bash
cp -r embedded-software-architect ~/.workbuddy/plugins/marketplaces/my-experts/plugins/
```

复制后按所用 WorkBuddy 版本进行导入/注册。若环境中已安装 `expert-manager`，可使用其注册脚本（本仓库不包含该工具）：

```bash
python3 <expert-manager>/scripts/register_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/embedded-software-architect
```

## 使用示例

- 我这边有块嵌入式板子出了点问题，想请你帮我排查。请先给我一个系统的排查思路，再动手。
- 帮我设计一个 Linux 多媒体采集管线：UVC 采集 + 硬编解码 + DRM 输出，要考虑性能瓶颈和延迟。
- 我的设备跑一段时间就崩了，内存占用看起来一直在涨。先帮我定位根因，不要急着改代码。
- 帮我评审这个平台驱动的 probe/remove、IRQ 和 DMA 生命周期；目标内核是厂商 6.1 分支，先检查接口与错误路径。

## 版本

当前版本：**0.2.0**

专家 ZIP 与 SHA-256 校验文件见 [v0.2.0 发布页](https://github.com/anrago-embedded-skills/workbuddy-expert/releases/tag/v0.2.0)。更新与验证范围见 [发布记录](docs/releases/0.2.0.md)。

## 许可

[Apache License 2.0](LICENSE)

其中引用的 Linux 内核、Buildroot/Yocto、Qt、FFmpeg、Rockchip MPP 等第三方组件遵循各自原有许可证。
