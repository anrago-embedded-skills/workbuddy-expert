# 多媒体链路诊断与实现流程

资料类型：领域工作流。适用于采集、图像处理、编解码、显示或音频链路中的多阶段问题；目标设备、BSP、SDK 或板卡暂时未知时仍可从通用 Linux 证据开始。

## 任务输入

先收集会改变当前判断的信息：

- 用户可观察到的故障、期望行为和成功标准；实时预览、无损录制、低延迟等目标之间可能存在不同取舍。
- 输入、输出、时间窗和同负载条件：分辨率、帧率、像素/采样格式、路数、编码参数、显示刷新率及稳定复现方法。
- 有源码时记录管线构造和配置；无源码时记录用户态工具、插件/codec 枚举结果、设备节点与日志。
- 目标身份和证据边界：HOST/TARGET、架构/ABI、内核/BSP/SDK/库版本、板卡与固件标识、是否能构建或上板。未知值保留为未知。

资料不全时可以继续：先用目标上的标准接口和只读工具映射已暴露的路径。只有平台专属判断或 SDK 实现会影响结论时，才需要匹配的 SoC/BSP/SDK 文档。缺少专有 runtime 不阻止通用层分析，也不能据此推断硬件不存在。

## 1. 映射实际能力和链路

以下是**TARGET 只读查询**示例；命令可能未安装，设备节点要替换为枚举所得值。输出是当前镜像/驱动暴露的能力，不代表所有硬件能力。

```bash
# TARGET · 列出可见 V4L2/media 节点与连接拓扑；预期显示驱动已注册的设备/链接。
v4l2-ctl --list-devices
media-ctl -p

# TARGET · 核实通用 GStreamer/FFmpeg 构建和元素/codec 能力。
gst-inspect-1.0 --version
gst-inspect-1.0 v4l2src
ffmpeg -version
ffmpeg -hwaccels
ffmpeg -encoders
```

若命令或节点缺失，记录“当前环境不可用”，不要把它解释成没有媒体硬件。运行时按实际协商的 caps/format、尺寸、帧率、stride/plane 布局、allocator/buffer memory feature、时钟域和队列策略建图。对厂商 runtime，把精确 SoC、BSP release、SDK 包/版本、手册章节、元素/API 名、支持格式、同步/内存约定和已知限制列入 SDK inventory；未找到对应证据前不写成可执行配方。

## 2. 在阶段边界建立相关证据

沿用一个固定复现窗口和负载，在应用或管线的已知边界记录：

| 边界 | 至少记录 |
|---|---|
| 采集完成/应用 dequeue | V4L2 sequence、timestamp、timestamp flags、DQBUF/error 数、重排/丢失计数 |
| 队列入/出 | buffer identity/sequence、输入/输出总数、队列最大/采样深度、超限策略、实际在两个 pad 之间缺失的帧 |
| 转换/缩放 | negotiated input/output caps、buffer identity、每帧 service time、错误/回退证据 |
| 编码提交/完成 | 输入/输出帧或 packet 数、PTS/DTS、提交/完成时间、延迟分布、编码错误/EOS drain |
| 显示/呈现（如适用） | 提交/完成/vblank 或应用 present 计数和时间；Qt 帧计时只覆盖 Qt 层时需标明 |

每阶段的 CPU 观测时间统一用同一种 monotonic 时钟，并保留原始 PTS 和硬件 timestamp。V4L2 timestamp 可为 monotonic 或 realtime；读取 buffer flags 后再对齐时钟，不直接相减不同 clock domain 的值。一个层的输入/输出差额比孤立日志更能定位首次差异；总帧数也要在结束时等待管线 drain/EOS，避免把仍在途 buffer 误算为丢失。[V4L2 buffer 文档](https://docs.kernel.org/userspace-api/media/v4l/buffer.html)说明 sequence/timestamp 语义；GStreamer [queue 文档](https://gstreamer.freedesktop.org/documentation/coreelements/queue.html)说明限额、当前队列级别与 block/leaky 行为。queue level 或 overrun signal 表明队列状态，不等于精确丢帧总数；按 buffer identity/sequence 对账。

DMA buffer 跨设备共享时，补充 producer/consumer 的 buffer 所有权、完成条件、fence/同步路径和 CPU cache 可见性契约。buffer 未完成或仍被消费者持有时不能回收或复用；具体等待/缓存操作按目标 API 和驱动契约实施，不假设所有路径都需手动 flush。[DMA-BUF 文档](https://docs.kernel.org/driver-api/dma-buf.html)说明共享 buffer 和异步硬件访问同步；板卡路径仍需 SDK/驱动核验。

## 3. 按首个差异处选择分支

| 证据 | 优先检查 | 不能仅据此下的结论 |
|---|---|---|
| Capture `sequence` 首先出现缺口、DQBUF 停顿或驱动错误 | 传感器/链路/驱动队列、实际协商格式/帧率、IRQ 与 buffer requeue；MIPI 拓扑问题读取 [MIPI bring-up](mipi-bringup.md) | 下游编码慢或 CPU 满载 |
| Capture 连续，队列输入正常但队列策略丢弃或深度增长 | queue 限额和 leaky/block policy、下游服务时间、在途 buffer 是否被持有 | 单纯把 queue 加大就提高持续吞吐 |
| 转换阶段耗时/差额先上升 | 输入输出 caps、stride/plane/allocator、是否重复转换、CPU/带宽；仅在 ABI 和 SDK 确认后切换硬件路径 | 仅凭 SoC 名称认定发生硬件加速或 CPU 回退 |
| 编码提交正常而完成/packet 计数滞后或报错 | encoder caps/profile/输入格式、服务时间、buffer pool、异步 drain 与资源错误 | queue 一定是根因 |
| 编码 packet 数与时间戳正常，问题只在屏幕可见 | DRM/KMS/Qt/compositor 的 present 和帧计时；按证据分别读取 Qt 或显示技能 | 把显示掉帧当作摄像头丢帧 |
| 计数相符但延迟/时间戳不连续 | 时钟域映射、buffer 排队/持有时间、队列策略、PTS 重写/丢帧策略 | 一定有硬件丢帧 |
| 共享 buffer 花屏、重复帧或偶发损坏 | 所有权、fence、DMA 映射/缓存可见性、format/stride 与 buffer 生命周期 | 通用地加 cache flush，或无证据换 codec 参数 |

若线程调度、通用应用阻塞、内存压力或设备驱动证据变成主因，按 [主技能分流](../SKILL.md) 加载对应工作流；不要把容器、Qt 或某 SoC 名称当作路由条件。

## 4. 实施最小完整修改

先说明要保持的契约：画质/帧率/端到端延迟、编码格式、audio/video sync、队列丢弃语义、buffer 所有权及资源预算。用证据支持一个改动，例如移除经能力协商证实冗余的转换、修正已经证明错误的格式/stride、修正 buffer 归还时机，或将队列 policy 改为符合“保留全部帧/追踪最新帧”要求的行为。

增加 queue 深度可吸收短 burst，却不能修复长期处理速率不足。把 block 改为 leaky 会改变内容保留语义；把 leaky 改为 block 可能将压力推回采集端。对异步提交保持完成/fence 和释放次序。专用 API、命令或 codec/plugin 名只在精确 SDK 文档与目标枚举同时支持时落入实现。

## 5. 交付与验收

产物根据任务大小选择：假设/区分证据表、caps 和链路图、最小 patch/配置差异、构建命令与目标身份、前后阶段计数/时间戳，以及回归结果。声明哪一项来自用户、源码、目标采样或教学夹具。

在相同输入、目标格式、帧率、路数、编码参数、运行时长和下游负载下比较修改前后；按用户目标检查丢帧/序号缺口、阶段延迟分布、queue 峰值、CPU/内存/buffer pool 和输出质量。若目标是保留每帧，应明确验证没有非预期 drop；若产品接受丢旧帧，应验收声明的低延迟与最大 drop 策略。工具/夹具测试、目标构建和板卡回归分别记录；没有环境就标为未执行。多步骤工作参考 [共享验证记录规范](../../embedded-debug-workflow/references/validation-policy.md)。
