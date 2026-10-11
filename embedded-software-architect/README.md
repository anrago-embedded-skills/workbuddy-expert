# 嵌入式软件高级工程师（磐石）

面向 **通用嵌入式 Linux** 的工程专家，覆盖 BSP、内核驱动、媒体、通信、存储与板级排障。主干不依赖某个厂商；ARM32/ARM64 等示例按目标 BSP/ABI 使用，不宣称未经验证的架构兼容。产品验收目标是**目标板功能与相关回归通过**；目标板不可用时继续完成离线工作，明确标记“待板测”。

## 类型

Agent 型（单个 AI 专家）

**定位边界**：聚焦 Linux 用户态 / BSP / 内核驱动 / 多媒体，**不涉及 MCU 裸机固件**（RTOS、寄存器级单片机编程）。平台系列中的 ARM32 型号需另核对架构与工具链。

## 工程结构

| 层次 | 工作方式 |
|---|---|
| 通用底座 | 明确目标/最少输入、保全证据、选择区分实验、记录构建身份和验收 |
| 领域工作流 | 按领域技能的输入、分支、产物和失败/回归条件推进 |
| 平台适配 | 核对目标型号、SDK/内核、运行能力，再采用对应接口和参数 |

复杂工程任务参考 [通用工程流程](skills/embedded-debug-workflow/references/engineering-workflow.md)；关键命令/代码/案例遵循 [资料与验证记录规范](skills/embedded-debug-workflow/references/validation-policy.md)。资料核对、工具/夹具测试、目标构建、仿真和板测是不同证据，不能互相替代。

## 内置 Skill（13 个）

| skill | 覆盖内容 |
|---|---|
| `media-pipeline-linux` | V4L2 · DRM/KMS · UVC · MIPI · FFmpeg/GStreamer · ALSA |
| `embedded-bsp-kernel` | 启动/板级 bring-up · 设备树 binding · 内核/模块构建 · Buildroot/Yocto · systemd |
| `linux-device-drivers` | probe/remove · 延迟探测 · 资源生命周期 · IRQ/锁 · MMIO/DMA · 电源管理 · 用户 ABI |
| `qt-embedded-rendering` |离屏渲染 · EGL/GLES 后端 · QML 掉帧定位 |
| `embedded-perf-debug` | 全局/cgroup OOM 取证 · Kernel Oops 解码 · 性能瓶颈 |
| `embedded-debug-workflow` | 未定位异常 · 进程/IPC · 可选运行环境参考（Docker/nginx/应用线程） |
| `embedded-peripherals` | GPIO · I2C · SPI · UART · regulator |
| `embedded-networking` | 网络负载 · socket 缓冲区 · fd 泄漏 · TCP 粘包 · 重连 |
| `data-storage-embedded` | SQLite · Redis · 掉电一致性 · fsync · 存储寿命 |
| `protocols-embedded` | MQTT · SSL/TLS · 5G 模组 · NDI · 协议转换 |
| `wireless-connectivity` | WiFi · BLE · Matter · Thread · 漫游性能 |
| `display-compositor-gpu` | Weston · X11 · EGL/GLES/GPU · 可选 OpenCV/NPU 视觉扩展 |
| `storage-hardware-io` | RAID · PCIe · SATA/NVMe · 块设备健康与有界文件测速 |

## 技能读取与跨领域协作

description 用于确定任务边界，不是关键词硬匹配保证。先依据当前子任务选择主技能，通过宿主实际支持的加载机制取得正文；已有完整正文可复用。需要跨领域知识时再补辅助技能，并按各入口给出的条件读取参考。加载失败必须说明，不能用通用知识回答后声称已调用技能。

Agent 中的 Markdown 链接相对 Agent 文件目录，各参考链接相对所属 SKILL.md 目录。13 个技能名称和挂载不变：MIPI 内容移到媒体参考，应用部署/线程内容移到通用排障参考，图像算法/NPU 内容放在图形技能的视觉扩展参考；这些不是新的独立技能。

静态挂载和引用可达不代表运行时已经调用。WorkBuddy 验证需记录主技能、辅助条件、实际读取路径/宿主正文来源和相应参考；回答正确只是其中一项。

## 平台覆盖

平台特有内容沉底到各 skill 的 `references/`，主干保持平台无关：

- **RK3588**：MPP/RGA · GPU/NPU · CMA；swap 和能力按部署实际检查
- **MTK**：MDP 硬件流水线
- **全志**：显示、2D 与视频引擎；核对具体芯片和 SDK 接口
- **NXP i.MX**：核对具体型号/BSP 的 VPU 能力、GStreamer 插件及实际元素名
- **海思 Hi3516**：厂商媒体 SDK 与 BSP，核对型号/架构（海思 MPP 与 Rockchip MPP 不能互换）
- **国科微**：厂商媒体 SDK 与 BSP，核对实际组件/API
- **通用 Linux**：软解兜底（明确标注性能上限）

参考文件提供调查线索；平台名称不是能力保证，示例不等于已板测。优先查目标内核源码、binding 和对应 SDK 文档。

## 内核能力与验证

- BSP：确认启动阶段、构建基线、内核配置、DTB 与实际运行版本；支持时用 schema 校验设备树。
- 驱动：检查匹配/自动加载、资源依赖与延迟探测、失败回滚、IRQ/work/timer/DMA teardown、锁与上下文、MMIO/DMA、PM 和用户 ABI。
- 验收：按驱动能力覆盖错误路径、并发压力、加载卸载、休眠唤醒和长跑。静态检查或主机测试不能替代这些板测。

仓库维护者可在仓库根目录运行 `python3 scripts/validate_expert.py embedded-software-architect` 和 `python3 -m unittest discover -s tests -p 'test_*.py'`。这些工具位于专家包外，检查静态结构和参考可达性，不验证 WorkBuddy 的实际加载；主技能选择与读取证据的行为场景见仓库的 `tests/expert-scenarios.md`。

## 使用示例

- 我这边有块嵌入式板子出了点问题，想请你帮我排查。请先给我一个系统的排查思路，再动手。
- 帮我设计一个 Linux 多媒体采集管线：UVC 采集 + 硬编解码 + DRM 输出，要考虑性能瓶颈和延迟。
- 我的设备跑一段时间就崩了，内存占用看起来一直在涨。先帮我定位根因，不要急着改代码。
- 评审这个驱动的 deferred probe、异步任务退出和 DMA 缓冲区生命周期，按目标内核接口给出修复与验证建议。

## 取证工具与教学案例

[取证说明](skills/embedded-debug-workflow/references/evidence-collection.md) 提供技能内 [collect-evidence.sh](skills/embedded-debug-workflow/scripts/collect-evidence.sh) 的输入、输出、限制与失败解释。工具在 TARGET Linux shell 采集 live 数据；HOST 如需检查文件快照，使用 POSIX shell 与显式 `--source-root`。它不自动连接设备或改变硬件/服务状态，只写用户指定的新报告目录。

```sh
# 在专家包根目录、TARGET Linux shell 执行；报告目录必须尚不存在。
sh skills/embedded-debug-workflow/scripts/collect-evidence.sh \
  --mode env --output /tmp/embedded-evidence-session-001
```

`manifest.json` 与 `summary.txt` 记录 source kind、采样范围、缺失/错误和截断。基础快照非原子、不自动判断根因；未收集到数据不能解释为目标正常。

案例在所属技能内按条件读取：DTB 未生效、probe defer、异步卸载、DMA 所有权、memcg OOM、媒体掉帧、网络恢复与持久化恢复。全部构造输入和示例数字明确标为教学夹具；未提供对应 SDK/板卡时，目标构建、仿真和板测不会预填通过。仓库的 `tests/content-scenarios.md` 规定内容对照评测；`tests/expert-scenarios.md` 规定路由与正文读取验证。

## 头像

头像在 `avatars/expert.png`。本版保留原有 1024×1024 PNG（588,228 字节，约 574 KiB）；WorkBuddy 生成说明允许 1024 原图供 512 展示，但基本规格同时要求 512×512、≤500KB。原头像体积超过该上限，是本版已知规格偏差；本次未重绘头像。官方包校验不检查图片尺寸/体积，实际导入与展示仍需在 WorkBuddy 验证。如需替换为自定义头像，规范要求：
- 格式：PNG（推荐）或 JPG
- 尺寸：512×512 px
- 大小：单张不超过 500KB

## 安装

将专家包目录放到本地专家市场目录下（默认 `~/.workbuddy/plugins/marketplaces/my-experts/plugins/`）：

```bash
# 1. 复制专家包到市场目录
cp -r embedded-software-architect ~/.workbuddy/plugins/marketplaces/my-experts/plugins/

# 2. 若已安装 expert-manager，可使用它提供的校验/注册工具
python3 <expert-manager>/scripts/validate_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/embedded-software-architect

# 3. 注册，使其在专家中心可见
python3 <expert-manager>/scripts/register_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/embedded-software-architect
```

导入和注册方式以当前 WorkBuddy 版本及本地 `expert-manager` 工具为准；本仓库不提供注册/打包脚本。复制目录本身不证明运行时已加载成功。

## 打包分享

```bash
python3 <expert-manager>/scripts/package_expert.py \
  ~/.workbuddy/plugins/marketplaces/my-experts/plugins/embedded-software-architect
```

## 版本

当前版本：**0.2.0**

语义化版本说明：
- `0.x.y` — 早期版本，内容持续调整
- `x.0.0` — 功能稳定
- `x.y.0` — 向后兼容的功能新增
- `x.y.z` — 向后兼容的缺陷修复

## 许可

本专家包采用 [Apache License 2.0](LICENSE) 授权。

其中引用的 Linux 内核、Buildroot/Yocto、Qt、FFmpeg、Rockchip MPP 等第三方组件遵循各自原有许可证，本项目不对其作任何声明或担保。
