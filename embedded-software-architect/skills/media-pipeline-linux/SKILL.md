---
name: media-pipeline-linux
description: |
  Video/audio pipeline on Linux embedded: V4L2 capture, DRM/KMS output, UVC gadget, FFmpeg, GStreamer, ALSA, hardware codec (RKMPP/MDP/TDE/VPU), 2D acceleration (RGA2).
  TRIGGER when: 视频采集、V4L2、v4l2-ctl、media-ctl、UVC、摄像头、CSI、DRM、KMS、plane、CRTC、modetest、显示输出、硬编解码、RKMPP、MDP、RGA2、RGA、FFmpeg、ffmpeg、GStreamer、gst-launch、ALSA、音频、音量、采样率、alsa、arecord、aplay、amixer、录像、回放、转码、缩放、格式转换、画面卡、视频卡、播放卡、预览卡、采集卡住、不出图、不出画面、黑屏、花屏、没信号、掉帧、丢帧、录像损坏、录不进、录像打不开、音频没声、没声音、声音小、啸叫、画面倒过来、旋转不对、字幕不动、字幕叠加、不同步、音画不同步、播放卡、预览卡、录像卡住、录不进、录像损坏、画面不动、画面没变化、采集卡住、相机不出图、摄像头不工作、没图像、黑了,
  DO NOT TRIGGER when: Qt/QML 界面与渲染性能（用 qt-embedded-rendering）；显示合成器 Weston/X11 配置（用 display-compositor-gpu）；内核 Oops/性能瓶颈（用 embedded-perf-debug）,
---

# media-pipeline-linux

> 平台无关的视频/音频/显示全链路方法论。**动手前先确认目标 SoC，再加载 `references/` 下对应平台文档。**

## 适用范围

Linux 嵌入式设备上的多媒体链路开发与排障：

- 视频采集：V4L2、UVC gadget、CSI
- 视频输出：DRM/KMS、fbdev
- 编解码：FFmpeg、平台硬件编解码引擎
- 音频：ALSA
- 管线：GStreamer
- 图形加速：2D 缩放/格式转换引擎

**不适用**：MCU 裸机音视频。

---

## 平台适配（动手前必做）

**先确认目标 SoC，再加载对应 references 文档。禁止把某平台的命令硬套到另一平台。**

| SoC | 适配文档 | 硬件加速路径 |
|---|---|---|
| Rockchip RK3588 | `references/rockchip-rk3588.md` | RKMPP 硬编解码 · RGA2 缩放/格式转换 |
| 联发科 MTK | `references/mediatek-mtk.md` | MTK MDP 硬件流水线 |
| 全志 Allwinner | `references/allwinner-tde.md` | TDE 2D 加速 · VE 视频引擎 |
| NXP i.MX | `references/nxp-imx-vpu.md` | VPU 硬编解码 · GStreamer plugin |
| 海思 Hi3516 | `references/hisilicon-hi3516.md` | HiSilicon VDEC/VENC |
| 国科微 Goke | `references/goke-micro-g300.md` | Goke 硬解 · GStreamer plugin |
| 通用 Linux | `references/generic-linux.md` | 软解 + 通用 DRM/GStreamer |

---

## V4L2 视频采集

### 核心 ioctl 语义

理解 ioctl 的语义比背代码重要：

| ioctl | 作用 | 关键点 |
|---|---|---|
| `VIDIOC_QUERYCAP` | 查询设备能力 | 先做这个，确认 driver/card 能力 |
| `VIDIOC_ENUM_FMT` | 枚举支持格式 | 驱动实际支持的分辨率列表 |
| `VIDIOC_S_FMT` | **设置**格式（驱动） | 必须先 `TRY` 再 `SET`，实际生效值可能回退 |
| `VIDIOC_G_FMT` | 读取**实际生效**格式 | **重要**：S_FMT 后一定要 G 确认，驱动可能调整了参数 |
| `VIDIOC_S_CROP` | 设置裁剪窗口 | 缩放/裁剪通常在这里 |
| `VIDIOC_REQBUFS` | 请求缓冲区 | 数量 `count` 是**上限**，驱动可能给更少 |
| `VIDIOC_QUERYBUF` | 查询各 buffer 的物理地址 | mmap 前必做 |
| `VIDIOC_QBUF` | 缓冲区入队 | 提交给驱动消费 |
| `VIDIOC_DQBUF` | 缓冲区出队 | 取处理好的帧 |
| `VIDIOC_STREAMON` | 开始流式传输 | 必须先配好全部格式和 buffer |

### 标准流程

```bash
# 1. 查能力
v4l2-ctl -d /dev/video0 --all

# 2. 查可用格式（不实际设置）
v4l2-ctl -d /dev/video0 --list-formats-ext

# 3. 设置格式
v4l2-ctl -d /dev/video0 --set-fmt-video=width=1920,height=1080,pixelformat=NV12
v4l2-ctl -d /dev/video0 --get-fmt-video   # 确认实际生效值

# 4. 试跑并抓帧
v4l2-ctl -d /dev/video0 --stream-all --stream-count=100 --stream-to=/tmp/out.raw

# 5. 看丢帧统计
v4l2-ctl -d /dev/video0 --log-status
```

### 常见坑

- **`S_FMT` 的实际值必须回读**：分辨率、像素格式可能被驱动调整，不回读会拿到错误预期
- **像素格式对齐**：NV12/I420 要求宽高为偶数，非偶数尺寸可能被拒
- **`--stream-all` 会打印丢帧**：抓帧同时关注 `Frasmere`/丢帧计数，丢帧往往是带宽或性能问题，不是采集问题
- 摄像头节点号不一定是 `video0`：多路设备时先 `--list-devices`

---

## DRM / KMS 显示输出

### 概念与分工

- **CRTC**：控制显示输出时序（扫描、刷新）
- **plane**：图层，可叠加。当前台地址、尺寸、格式、alpha
- **encoder**：把plane 连接到某个物理输出（HDMI/DSI/MIPI）
- **mode**：分辨率 + 刷新率

### atomic vs legacy

现代 DRM 推荐 **atomic mode**，属性变更需要一起 commit 才生效：

```bash
# 查当前显示状态
modetest -c -p

# 查 plane 属性
modetest -p

# 查看可用 connector / mode
xrandr --listproviders  # DRM 后端下可参考
```

程序侧关键路径：`drmModeGetResources` → `drmModeGetConnector` → `drmModeSetCrtc`（或 atomic 的 `drmModeAtomicReq`）。

### 为什么改了属性不生效（高频问题）

1. **未走 atomic commit**：只改了属性没commit，或用 legacy API 但驱动要求 atomic
2. **plane 越界/遮挡**：新 plane 与已有 plane 重叠且z-order 靠后，被盖住了
3. **CRTC 绑定冲突**：一个 CRTC 只能绑一个 primary plane，换CRTC 时旧的没解绑
4. **权限不足**：`/dev/dri/card*` 需要正确权限（video/render 组）
5. **framebuffer 格式不支持**：plane 不支持该 pixel format

### DRM vs fbdev

| | DRM/KMS | fbdev |
|---|---|---|
| 图层 | 多plane 叠加 | 单缓冲 |
| 撕裂 | 可用 page flip 消除 | 难避免 |
| 适用 | 多图层合成、需要无撕裂 | 简单全屏显示 |

多图层/需要无撕裂输出用 DRM；单缓冲简单显示 fbdev 更快。

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

### 板上性能关键点

```bash
# 硬件加速（RK3588 用 rkmpp）
ffmpeg -hwaccel rkmpp -hwaccel_output_format drm_prime \
  -afbc rga -i input.mp4 -c:v h264_rkmpp -b:v 8M output.mp4
```

```bash
# 软件解（通用平台兜底）
ffmpeg -i input.mp4 -c:v libx264 -preset ultrafast -tune zerolatency output.mp4
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
gst-launch-1.0 -v videotestsrc ! videoconvert ! autovideosink
gst-inspect-1.0 v4l2src# 查 plugin 属性
GST_DEBUG=2 gst-launch-1.0 ...   # 2=警告 3=错误
```

**多 queue 分级**：采集后、编码前、后处理后各插一个 `queue`，避免单线程瓶颈。

---

## ALSA 音频

### PCM 播放 / 录制

```bash
# 列设备
arecord -l
aplay -l

# 播放（指定格式）
aplay -D hw:0 -f S16_LE -r 48000 -c 2 test.wav

# 录制
arecord -D hw:0 -f S16_LE -r 48000 -c 2 -d 5 record.wav

# 查看当前 PCM 状态
cat /proc/asound/card0/pcm0p/sub0/status
```

### mixer 控制

```bash
amixer -c 0 scontents        # 列控件
amixer -c 0 set 'Speaker' 70% # 设置音量
```

### 常见坑

- **采样率不一致导致变调/杂音**：播放端与源文件采样率、声道数必须匹配
- **`Speaker` vs `Headphone`** 控件名因codec 而异，先 `amixer -c 0 scontents` 确认真实名称
- **ALSA 与 PulseAudio 抢占设备**：嵌入式上两者混用会导致独占失败，确认运行的是哪一个
- **音视频同步**：音频时钟是主时钟基准，视频延迟要对齐到音频

---

## 硬件加速：什么时候必须用

CPU 软解在多路高清场景会打满CPU，**优先用硬件引擎**。

判定规则：
- 单路 1080p 软件转码 → CPU 可能可撑，但实时性差，优先硬件
- 多路、4K、频繁缩放格式转换 → **必须硬件**
- 缩放比例特殊（如任意比例）→ 查芯片是否支持，不支持则走软件或改用其他方案

**代价**：硬件引擎有格式约束（对齐、stride、支持的格式组合），跨格式要先转。详见各平台 references。

---

## 性能排查顺序

多媒体性能问题按此顺序查，不要跳步：

1. **CPU 占用** — `top` 看是否单核打满
2. **带宽** — 内存带宽是常见瓶颈，尤其缩放/格式转换密集时
3. **丢帧** — `dmesg` 看 V4L2/GStreamer 丢帧记录
4. **管线阻塞** — GStreamer 缺 `queue` 会串行阻塞
5. **格式转换次数** — 链路上重复 `videoconvert` 是性能杀手

---

## 边界与注意

- **禁止**把某平台命令硬套另一平台（如在联发科上跑 RKMPP）
- **禁止**未经板上实测就下「性能没问题」的结论
- **禁止**只改设备侧不确认主机侧实际枚举结果（UVC 场景）
- 平台特有 API 必须查对应 references，不要凭记忆推断其他平台的接口