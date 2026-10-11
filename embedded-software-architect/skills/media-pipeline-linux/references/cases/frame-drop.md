# 教学案例：合成媒体管线中的帧丢失

> **资料类型：教学案例 / 合成夹具。** 下文所有场景、计数、时间戳和延迟值均为人工构造的演示输入，不是设备日志、硬件测量、SDK 结果或修复后的实测提升。未执行目标构建或板测；目标 build 和 board 均未验证。示例使用通用 Linux/V4L2/GStreamer 概念，平台适用性以目标实际暴露的接口为准。

## 输入

问题：实时摄像头预览/录制的目标是 30 fps，播放器偶尔卡顿。应用由 Qt 承载，但当前唯一可靠症状是输出视频有帧间隔；SoC、BSP、Qt/GStreamer 构建和目标硬件编解码能力未知。可获取源码及同一 10 秒负载下的应用探针日志；板卡是否可用未知。

首轮先不选 Qt 或厂商 codec：应用使用 Qt 不证明掉帧发生在 Qt；按 [媒体链路流程](../pipeline-workflow.md) 对账 capture、queue、conversion 和 encoder 边界。若编码时间戳/数量完整但只在实际显示时卡顿，再转到 Qt/display present 证据。

## 合成夹具

期望输入：1280×720、30 fps、10 s，共 300 帧。所有序号连续，时间只用于教学演算。

| 阶段/观察 | 输入/输出计数 | 序号/时间证据 | 延迟/资源证据 |
|---|---:|---|---|
| V4L2 dequeue | 300 / 300 | `sequence=1200..1499`，无缺口；buffer timestamp flags 表示 `CLOCK_MONOTONIC`；相邻 timestamp 约 33.3 ms | `DQBUF error=0` |
| queue sink/src probes | 300 / 270 | 入队覆盖 1200..1499；出队序号对账发现 30 个旧帧被配置的 leaky policy 丢弃 | 配置 `max-size-buffers=4`, `leaky=downstream`；采样最高达到 4 |
| 格式转换 | 270 / 270 | 合成 negotiated caps 中 source output、converter input/output 与 encoder sink 均为 `NV12 1280x720 30/1`；每个出队序号一进一出 | 合成 service-time 样本 p50 36.8 ms、p95 42.2 ms；stride/memory feature 未记录 |
| encoder | 270 / 270 | packet PTS 与入参 buffer 可配对；EOS drain 后计数相等 | 合成 service-time 样本 p50 18.4 ms、p95 21.5 ms；encoder error=0 |

以下是两个保留帧的**合成记录行**。这些 CPU-side 时间均用同一 `CLOCK_MONOTONIC`，展示 capture→queue→convert→encoder 的观测边界；真实目标要保留自己的精度/clock domain 和 buffer identity：

| sequence | V4L2 capture ts | queue sink / src | convert start / complete | encoder submit / complete |
|---:|---:|---:|---:|---:|
| 1200 | 0.000 ms | 0.600 / 0.900 ms | 1.100 / 37.900 ms | 38.200 / 56.600 ms |
| 1201 | 33.333 ms | 33.950 / 38.200 ms | 38.400 / 75.200 ms | 75.500 / 93.900 ms |

这两行仅展示被处理 buffer 的边界时间；300→270 的总 drop 数来自整个窗口 counters 和 sequence set 对账，不可从这两行外推。PTS 保存在 trace 中做媒体时间对齐，但不是上述 monotonic CPU-side 时间。

转换阶段的合成 p50 已超过每帧 33.3 ms 的预算，且 queue 在上游累计至限额；显式 leaky policy 因此在 queue 边界丢弃旧帧。queue level/overrun 通知只用于判断限额状态，30 帧的差额来自同一复现窗内的 sequence 对账，不把通知数当精确 drop count。

时间戳比较需保持时钟语义：示例 capture buffer 的 `CLOCK_MONOTONIC` 时间可以与用同域测得的 dequeue/阶段 service time 对齐；GStreamer PTS 是媒体运行时间，不直接减去系统 monotonic timestamp。实际采样需记录 timestamp flags、管线时钟映射和 EOS drain 状态。[V4L2 buffer timestamp 与 sequence](https://docs.kernel.org/userspace-api/media/v4l/buffer.html)、[GStreamer queue 行为](https://gstreamer.freedesktop.org/documentation/coreelements/queue.html)。

## 候选原因与区分测量

| 候选原因 | 预期证据 | 最小区分测量 |
|---|---|---|
| Sensor/CSI/V4L2 capture 丢失 | 缺口首先出现在 capture sequence，或 DQBUF/驱动错误；下游保持同一缺口 | 在应用 dequeue 处记录 V4L2 sequence、timestamp flags 与 DQBUF 错误，检查实际 media topology 和目标驱动日志 |
| 队列丢旧帧/背压 | capture 连续；queue sink/src sequence 第一次不相等；队列限额/策略符合该行为 | 同时记录两个 queue pad 的 buffer identity/sequence 和 queue level；对照 leaky/block 配置 |
| conversion/scale 长尾 | queue 输出仍连续；转换输入/输出 caps 相符但每帧 service-time 超预算，queue 随之达到上限 | 分别记录 conversion pad 计数、monotonic 进入/完成时间、线程调度和 CPU 使用；核实 stride/plane/allocator |
| encoder 变慢或异步结果未 drain | conversion 输出连续；encoder submit 到完成的差额首先出现，或 EOS 后仍有在途 frame | 分开记录提交、完成、packet PTS/序号、错误和 drain 完成状态 |
| Qt/QPA 或显示呈现延迟 | encoder packet 数/时间戳连续，差额只出现在应用呈现、scene graph 或 DRM present | 量取 Qt 帧计时与 display present；按证据使用 Qt 或显示技能 |
| 时钟域比较错误 | PTS 看似跳变，但 buffer sequence/阶段计数相符；将 timestamps 直接相减时单位/基准不一致 | 记录 V4L2 timestamp flags、GStreamer running-time clock 和统一 monotonic probe；先映射再比较 |
| DMA buffer 生命周期/同步 | 重复、旧帧或花屏与异步消费者持有期重叠，完成 fence/归还次序异常 | 按 buffer identity 追踪提交、完成/fence、所有消费者归还和复用；查目标 API 对 cache coherence 的约定 |

在这组合成输入下，首个确定的计数差额发生在 queue，转换阶段时间超过帧预算，编码阶段没有新增差额。证据支持的判断是“慢转换使 bounded queue 填满，当前 leaky-downstream 策略丢旧帧”；它不证明某块板上的传感器、CPU、DMA 或硬件引擎行为。

## 最小修改假设

不要先单纯增加 queue 深度：这会延长延迟窗口，不能提高持续 conversion service rate，也不会消除稳态帧率缺口。一个可审查的最小候选是移除已被源码定位到、且能力协商证实冗余的软件格式转换，并让上游直接协商 encoder 已接受的格式。

这个改动有前置条件：目标 capture 与 encoder 必须协商相同格式/plane/stride，并确认 allocator/buffer feature 与 buffer 所有权路径可互通。若只看到 caps 字符串相同而未证实 memory feature、layout 和异步同步，则不要移除转换；先补齐目标 SDK 和运行时证据。选择“保留全部帧”还是“追踪最新帧”也必须由产品语义决定；改变 leaky policy 是行为变化，不是透明优化。

## 同负载回归与产物

修改前后使用相同输入/相机条件、分辨率、30 fps、10 s 时长、encoder 参数、下游客户端和系统负载。收集：修改前后的 negotiated caps、插件/SDK 版本、源码/构建身份、队列配置、每阶段序号与计数、同域时间戳/延迟分布、EOS drain、输出文件/画质检查和资源使用情况。

回归验收按产品目标确定：若要求 30 fps 且保留每帧，则 capture、queue、converter、encoder 的序号差额应为 0，输出计数应与预期相符；若允许丢旧帧，则记录最大丢弃率/端到端延迟目标并证明超限策略符合约定。相同负载下转换阶段应满足可接受的帧预算，queue 不应无界增长，资源与画质不回退。以下前后值留给实际执行时填写，不在合成案例中预填：

| 指标 | 修改前 | 修改后 | 验收目标/来源 |
|---|---|---|---|
| capture / queue / conversion / encoder 计数 | 合成值见上表 | 未执行 | 依产品保帧/丢旧策略填写 |
| 各阶段 p50/p95 延迟 | 合成值见上表 | 未执行 | 从目标同负载采样填写 |
| EOS 后在途 buffer / queue 峰值 | 合成值见上表 | 未执行 | 确认 drain 完成与有界队列 |
| CPU/内存/输出质量 | 未采集 | 未执行 | 保持同负载，检查不退化 |

## 验证限制

本案例本身没有设备构建、目标构建或板测数据。合成计数仅检验推理路径的示例结构；不能作为目标吞吐、延迟、驱动能力或“修复已提升帧率”的证据。真实验证层次和资料记录按[共享验证政策](../../../embedded-debug-workflow/references/validation-policy.md)执行。
