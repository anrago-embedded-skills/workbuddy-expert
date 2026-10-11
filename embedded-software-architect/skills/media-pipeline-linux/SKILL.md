---
name: media-pipeline-linux
description: |
  主技能：开发或排查 Linux 嵌入式多媒体链路，包括摄像头/MIPI-CSI 采集、编解码、音频和 DRM/KMS 输出。Qt/QML 渲染问题先选 Qt 技能；媒体链路即使由 Qt 应用承载，仍以本技能为主。
---

# media-pipeline-linux

> 平台无关的视频/音频/显示全链路方法论。平台未知时可先按通用流程收集证据；**只有形成平台特定判断或使用厂商 API/命令前，才需确认目标 SoC 并加载对应参考。**平台表中的厂商引擎、API 和工具名仅是调查线索；是否存在、支持哪些格式以及命令行选项都需按目标芯片、BSP、SDK 版本核实。

## 适用范围

Linux 嵌入式设备上的多媒体链路开发与排障：

- 视频采集：V4L2、UVC gadget、CSI
- 视频输出：DRM/KMS、fbdev
- 编解码：FFmpeg、平台硬件编解码引擎
- 音频：ALSA
- 管线：GStreamer
- 图形加速：2D 缩放/格式转换引擎

**不适用**：MCU 裸机音视频。

## 主技能选择与分流

摄像头采集、V4L2、编解码、GStreamer/FFmpeg、ALSA 音频、DRM/KMS 媒体输出及 MIPI-CSI/DSI 链路，选择本技能作为主技能，即使这些链路运行在 Qt 应用中。Qt/QML 的 QPA、scene graph、窗口刷新或界面计时问题，先用 [qt-embedded-rendering](../qt-embedded-rendering/SKILL.md)；仅当诊断证据指向 EGL、compositor、GPU 或图形驱动，再辅助读取 [display-compositor-gpu](../display-compositor-gpu/SKILL.md)。

若测量结果指向 CPU、内存带宽或 I/O 资源约束，再辅助读取 [embedded-perf-debug](../embedded-perf-debug/SKILL.md)；通用应用线程或事件循环卡住时，从 [embedded-debug-workflow](../embedded-debug-workflow/SKILL.md) 开始；证据指向内核 IRQ、workqueue 或驱动锁时，转到 [linux-device-drivers](../linux-device-drivers/SKILL.md)。

## 任务入口与完成契约

先记录要观察的行为、输入和目标负载，以及采集/处理/编码/显示各段的实际边界、格式、帧率和版本。目标型号、SDK 或板卡暂时未知时仍可做通用能力枚举和源码分析；把未知项记下来，不以 SoC 名称推断设备能力。

命令规则：`TARGET` 在目标执行，`HOST` 在开发主机执行；尖括号参数是模板，不能原样执行；只读查询、写文件、流式采集、播放或改变设备状态须分别标出。工具/权限/节点缺失不等于硬件缺失。

多阶段问题按 [媒体链路工作流](references/pipeline-workflow.md) 建立阶段计数和时间戳，分支到首个出现差异的环节。保持原有分流：Qt 应用中的媒体采集、编解码和传输仍以本技能为主；只有 QPA、scene graph、界面刷新证据才以 [qt-embedded-rendering](../qt-embedded-rendering/SKILL.md) 为主，EGL/compositor/GPU 再按证据辅助 [display-compositor-gpu](../display-compositor-gpu/SKILL.md)。掉帧练习见合成案例 [frame-drop.md](references/cases/frame-drop.md)。

交付包含目标和构建身份、证据及其来源、候选原因与区分测量、最小修改、实际产物、相同输入/负载下的回归结果和未覆盖项。可用时沿用通用 [工程工作流](../embedded-debug-workflow/references/engineering-workflow.md) 与[验证政策](../embedded-debug-workflow/references/validation-policy.md)；这两份共享参考未随集合提供时，本页的任务契约仍适用。

---

## 平台适配（平台特定结论前必做）

**可先读取通用流程并收集设备证据；平台未知或尚未确认时，按需读取 [generic-linux.md](references/generic-linux.md)。只有在平台专属 API、工具或硬件能力会影响结论时，才确认目标 SoC/BSP 并加载对应平台文档。平台条目描述调查范围，不保证目标镜像提供相应加速器、库、服务、插件或命令。用目标设备的设备节点、`gst-inspect-1.0`、FFmpeg 能力列表、已安装包和对应版本的官方 SDK/BSP 文档逐项确认后再使用示例。**

| SoC | 适配文档 | 调查范围（依目标 BSP/SDK 验证） |
|---|---|---|
| Rockchip RK3588（ARM64 示例） | [rockchip-rk3588.md](references/rockchip-rk3588.md) | 仅在确认目标 SoC 为 RK3588 后，核对其 V4L2、DRM、GStreamer 和 SDK 路径 |
| 联发科 MTK（ARM 示例） | [mediatek-mtk.md](references/mediatek-mtk.md) | 确认具体 MTK SoC/BSP 后，核对 media/MDP 接口 |
| 全志 Allwinner（ARM 示例） | [allwinner-tde.md](references/allwinner-tde.md) | 确认具体 Allwinner SoC/BSP 后，核对 media、2D 和视频接口 |
| NXP i.MX（ARM 示例） | [nxp-imx-vpu.md](references/nxp-imx-vpu.md) | 确认具体 i.MX 型号/BSP 后，核对 V4L2/GStreamer 插件和 SDK 接口 |
| 海思 Hi3516（ARM 示例） | [hisilicon-hi3516.md](references/hisilicon-hi3516.md) | 确认具体 Hi3516 型号/SDK 后，核对视频与图像接口 |
| 国科微 Goke（ARM 示例） | [goke-micro-g300.md](references/goke-micro-g300.md) | 确认具体 Goke 型号/SDK 后，核对编解码和 GStreamer 插件 |
| 通用 Linux | [generic-linux.md](references/generic-linux.md) | 未发现可用 SoC 专用媒体接口，或需要核对通用 V4L2、DRM/KMS、ALSA、GStreamer 行为时 |

MIPI-CSI/DSI 拓扑、lane、时序或 bring-up 问题另读 [mipi-bringup.md](references/mipi-bringup.md)；只在问题涉及 MIPI sensor/bridge/panel 链路时加载。

---

## V4L2 视频采集

### 核心 ioctl 语义

理解 ioctl 的语义比背代码重要：

| ioctl | 作用 | 关键点 |
|---|---|---|
| `VIDIOC_QUERYCAP` | 查询设备能力 | 先做这个，确认 driver/card 能力 |
| `VIDIOC_ENUM_FMT` | 枚举支持格式 | 驱动实际支持的分辨率列表 |
| `VIDIOC_S_FMT` | **设置**格式（驱动） | 可先用 `TRY_FMT` 试探；`S_FMT` 后用 `G_FMT` 确认实际生效值 |
| `VIDIOC_G_FMT` | 读取**实际生效**格式 | **重要**：S_FMT 后一定要 G 确认，驱动可能调整了参数 |
| `VIDIOC_S_CROP` | 设置裁剪窗口 | 缩放/裁剪通常在这里 |
| `VIDIOC_REQBUFS` | 请求缓冲区 | 数量 `count` 是**上限**，驱动可能给更少 |
| `VIDIOC_QUERYBUF` | 查询 buffer 的 offset、length 和 flags 等映射信息 | mmap 时按 API 使用返回的 offset；它不提供可跨设备使用的物理地址 |
| `VIDIOC_QBUF` | 缓冲区入队 | 提交给驱动消费 |
| `VIDIOC_DQBUF` | 缓冲区出队 | 取处理好的帧 |
| `VIDIOC_STREAMON` | 开始流式传输 | 必须先配好全部格式和 buffer |

### 标准流程

```bash
# TARGET · 只读能力查询；预期列出当前可见的 capture/output nodes 和 driver 信息。
v4l2-ctl --list-devices
# TARGET · 只读能力与格式信息；将模板替换为上一步枚举的节点。
v4l2-ctl -d <ENUMERATED_CAPTURE_NODE> --all

# TARGET · 只读格式枚举；缺少工具/节点只表明当前路径不可查询。
v4l2-ctl -d <ENUMERATED_CAPTURE_NODE> --list-formats-ext

# TARGET · 会改变此 capture 节点当前协商格式；先确认节点空闲并保存原格式。
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=NV12
v4l2-ctl -d /dev/video0 --get-fmt-video   # 确认实际生效值

# TARGET · 有状态的短时采集；将节点和新文件路径替换为实值。预期采集 100 个 buffer；失败/超时只定位到该路径，不能单独归因于传感器。
v4l2-ctl -d <CAPTURE_NODE> --stream-mmap=4 --stream-count=100 --stream-to=<NEW_OUTPUT_FILE>
```

### 常见坑

- **`S_FMT` 的实际值必须回读**：分辨率、像素格式可能被驱动调整，不回读会拿到错误预期
- **像素格式对齐**：NV12/I420 要求宽高为偶数，非偶数尺寸可能被拒
- buffer 的 `sequence` 和 `timestamp` 可辅助识别序号缺口与时序；先记录 timestamp flags/clock domain，再与应用和下游时间对齐。驱动没有提供通用的丢帧统计接口时，不从单条日志推断丢帧归属
- 摄像头节点号不一定是 `video0`：多路设备时先 `--list-devices`

---

## DRM / KMS 显示输出

### 概念与分工

- **CRTC**：控制显示输出时序（扫描、刷新）
- **plane**：图层，可叠加。当前台地址、尺寸、格式、alpha
- **encoder**：把 CRTC 的扫描输出转换为 connector 所需的信号；plane 向 CRTC 提供图层
- **mode**：分辨率 + 刷新率

### atomic vs legacy

Atomic KMS 允许把多个属性的变化作为一次状态更新提交；驱动是否支持及是否需要使用，按目标 DRM 驱动和用户态接口确认：

```bash
# TARGET · 只读查询；需要 modetest，输出 connector/CRTC/plane 能力；权限或驱动不支持时会失败。
modetest -c -p

# HOST/TARGET · 仅当已有 X server 时查询 X provider；它不是通用 DRM/KMS 枚举接口。
xrandr --listproviders
```

程序侧关键路径：`drmModeGetResources` → `drmModeGetConnector` → `drmModeSetCrtc`（或 atomic 的 `drmModeAtomicReq`）。

### 为什么改了属性不生效（高频问题）

1. **未走 atomic commit**：只改了属性没commit，或用 legacy API 但驱动要求 atomic
2. **plane 越界/遮挡**：新 plane 与已有 plane 重叠或 z-order 不符预期
3. **plane/CRTC 绑定冲突**：plane 不支持该 CRTC 或资源组合；核对当前 object properties/state
4. **权限不足**：`/dev/dri/card*` 需要正确权限（video/render 组）
5. **framebuffer 格式不支持**：plane 不支持该 pixel format

### DRM vs fbdev

| | DRM/KMS | fbdev |
|---|---|---|
| 图层 | 多plane 叠加 | 单缓冲 |
| 缓冲与更新 | 可用 page flip/atomic 更新，实际能力依驱动和路径 | 由驱动与应用实现决定 |
| 适用 | 需要枚举和协商 plane/CRTC/connector 的场景 | 需要兼容 fbdev 的简单显示场景 |

多 plane、page flip 与同步能力均须从目标驱动和实际帧呈现验证，不能仅凭接口名称保证无撕裂或性能优势。

---

## UVC Gadget

UVC gadget 让设备被主机识别为摄像头。**主机下拉框里的分辨率和帧率档位，由设备侧帧描述符决定**——改描述符才能改主机看到的效果。

### 帧描述符改造要点

- 帧率以**固定间隔（dwFrameInterval）** 声明，不是帧率值本身
- 每个分辨率档位必须配齐 Frame、FrameInterval（通常还要设 MaxVideoFrameSize）
- 增删档位后必须验证主机能正常枚举，帧率上限受 USB 带宽约束
- 描述符结构体常见字段：`bFrameIndex`、`wWidth`、`wHeight`、`dwMinFrameInterval`、`dwMaxFrameInterval`、`dwMaxVideoFrameSize`

### 调试要点

- 主机侧若下拉框没有某档位 → 描述符没改对或没部署
- 带宽不足会导致高分辨率高帧率掉帧，需降档位或改dwMaxVideoFrameSize
- 修改后必须**部署到设备 + 仓库脚本两处**，避免重刷固件丢失

---

## FFmpeg

### 设备端能力检查

```bash
# TARGET · 只读列出该 FFmpeg build 的能力；工具缺失、空 capability 或 build 未编入 codec 不证明目标硬件不存在。
ffmpeg -hwaccels
ffmpeg -encoders
ffmpeg -filters
```

`rkmpp`、`drm_prime` 和 `-afbc rga` 等厂商路径/选项仅可能出现在匹配的特定构建中，不能视为通用 FFmpeg 命令。先根据以上列表和目标 SDK 文档确认选项、输入输出格式与硬件支持，再构造并测试完整管线。

```bash
# HOST/TARGET · 参数模板；先确认输入、encoder 与新输出路径。读取输入并写编码产物。
ffmpeg -i <INPUT_FILE> -c:v <CONFIRMED_SOFTWARE_ENCODER> -preset ultrafast -tune zerolatency <NEW_OUTPUT_FILE>
```

### 常见坑

- **色彩空间转换是隐形大头**：`yuv420p`↔`nv12` 转换占大量 CPU，先统一格式再编码
- **`-preset ultrafast` 换 CPU vs 码率上升**：实时性优先时牺牲压缩率
- **多线程与实时性冲突**：`-threads` 过多导致单帧延迟抖动，实时场景限制线程数
- **ffprobe 先看流信息再动手**：`ffprobe input.mp4`，不要盲目转码

---

## GStreamer

### 通用 element 速查

- `v4l2src` / `v4l2sink`：V4L2 采集/输出
- `queue`：**关键** — 插入 queue 解耦线程，否则管线阻塞导致延迟累积
- `videoconvert`：格式转换（CPU 开销大，尽量避免在多次转换链中）
- `videorate`：帧率调整
- `capsfilter`：强制格式
- `encoder` / `decoder`：平台相关，需用对应平台的 plugin

### 调试

```bash
# HOST/TARGET · 有限软件合成管线；预期生成 30 个 test buffer 后 EOS，不验证目标摄像头/硬件编码；缺少对应 GStreamer elements 时会报 factory/link 错误。
gst-launch-1.0 -v videotestsrc num-buffers=30 ! videoconvert ! fakesink
# TARGET · 只读查询标准 V4L2 source element 的属性/caps；factory 缺失说明当前 GStreamer build 无此 element。
gst-inspect-1.0 v4l2src
# HOST/TARGET · 参数模板；替换为已枚举元素构成的真实管线。GST_DEBUG=2 增加日志，不改变硬件配置。
GST_DEBUG=2 gst-launch-1.0 <CONFIRMED_PIPELINE>
```

`queue` 会把 sink/src 侧工作放到不同 streaming thread；达到 buffer/byte/time 限额后默认会阻塞上游，leaky policy 可丢新/旧 buffer。是否需要 queue 及其丢帧语义依实际管线选择，不机械地在每一段都添加。

---

## ALSA 音频

### PCM 播放 / 录制

```bash
# TARGET · 只读列举 PCM 设备；失败需结合目标声卡/driver 日志。
arecord -l
aplay -l

# TARGET · 播放参数模板；先确认 PCM 设备和输入文件；会驱动目标音频输出。
aplay -D <CONFIRMED_PCM_DEVICE> -f S16_LE -r 48000 -c 2 <INPUT_WAV>

# TARGET · 有状态录音参数模板；确认设备及新文件路径；采集 5 秒并写入文件。
arecord -D <CONFIRMED_PCM_DEVICE> -f S16_LE -r 48000 -c 2 -d 5 <NEW_OUTPUT_WAV>

# TARGET · 参数模板；替换为 `/proc/asound` 中枚举的节点；只读当前 PCM runtime status。
cat /proc/asound/card<CARD_INDEX>/pcm<PCM_INDEX>p/sub<SUBSTREAM_INDEX>/status
```

### mixer 控制

```bash
amixer -c <CARD_INDEX> scontents  # TARGET · 只读列 mixer controls；索引以 `amixer -l`/声卡枚举为准。
amixer -c <CARD_INDEX> set '<CONFIRMED_CONTROL>' 70% # TARGET · 改变目标音量；先记录原值与恢复方式。
```

### 常见坑

- **采样率不一致导致变调/杂音**：播放端与源文件采样率、声道数必须匹配
- **`Speaker` vs `Headphone`** 控件名因codec 而异，先 `amixer -c 0 scontents` 确认真实名称
- **ALSA 与 PulseAudio 抢占设备**：嵌入式上两者混用会导致独占失败，确认运行的是哪一个
- **音视频同步**：音频时钟是主时钟基准，视频延迟要对齐到音频

---

## 硬件加速能力评估

软解、软件转换在高分辨率或多路负载下可能成为瓶颈；是否使用硬件路径，要以目标构建和设备实测为准。

先确认目标平台是否提供兼容路径，再测吞吐、延迟、画质、内存带宽、CPU 占用和功耗。缩放比例、色彩格式、stride、对齐和并发路数均可能受具体硬件与 SDK 限制。

硬件路径有格式约束（对齐、stride、支持的格式组合），跨格式可能还需转换。详见各平台 references；目标 SDK 未核实前，厂商路径仅是能力盘点项，不提供猜测的命令、API 名称或可复制调用样例。

传递 DMA buffer 时，记录每个生产者/消费者取得、提交、完成与归还 buffer 的时刻和所有权；只在实测格式/stride/同步契约支持时共享零拷贝。缓存可见性与异步完成同步依实际映射 API、DMA-BUF/fence 路径和驱动约定，不能通过随意添加 cache flush 或复用 buffer 修复。参考 [Linux DMA-BUF synchronization](https://docs.kernel.org/driver-api/dma-buf.html)。

---

## 性能排查入口

先按 [媒体链路工作流](references/pipeline-workflow.md) 对齐逐阶段计数与时钟；再依据首个差异处决定是否检查 CPU、内存带宽、格式转换、队列背压、编码服务时间或输出呈现。`dmesg` 可能提供驱动线索，但不能替代跨阶段计数，也不能证明某一级没有丢帧。

---

## 边界与注意

- **禁止**把某平台命令硬套另一平台（如在联发科上跑 RKMPP）
- **禁止**未经板上实测就下「性能没问题」的结论
- **禁止**只改设备侧不确认主机侧实际枚举结果（UVC 场景）
- 平台特有 API 必须查对应 references，不要凭记忆推断其他平台的接口

## 主要参考

- Linux V4L2 userspace API: https://docs.kernel.org/userspace-api/media/v4l/v4l2.html
- V4L2 buffer sequence and timestamp fields: https://docs.kernel.org/userspace-api/media/v4l/buffer.html
- Linux DRM/KMS documentation: https://docs.kernel.org/gpu/drm-kms.html
- GStreamer queue buffering, levels and leaky policy: https://gstreamer.freedesktop.org/documentation/coreelements/queue.html
- FFmpeg command-line documentation: https://ffmpeg.org/ffmpeg.html
