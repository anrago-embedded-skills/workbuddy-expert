# NXP i.MX 平台适配

> NXP i.MX 系列用 **VPU**（Video Processing Unit）做硬件编解码，GStreamer 集成完善，是 Linux 社区支持最好的嵌入式媒体平台之一。

## 硬件加速能力

| 引擎 | 用途 | 访问方式 |
|---|---|---|
| **VPU** | 硬件编解码（H.264/H.265/VP8/VP9） | VPU API / GStreamer plugin |
| **GPU** | Mali / PowerVR GC | EGL / GLES / OpenCL |
| **ISP** | 图像信号处理（i.MX8系列） | ISP 驱动 |

---

## GStreamer plugin（推荐路径）

i.MX 生态的最大优势是**官方提供成熟的 GStreamer 硬件插件**，无需直接调 VPU API：

```bash
# 查看可用的硬件插件
gst-inspect-1.0 | grep -i "omx\|vpu\|mfx\|ivf"

# 典型硬解管线
gst-launch-1.0 filesrc location=input.mp4 ! qtdemux \
  ! h264parse ! avdec_h264 ! videoconvert ! autovideosink
```

常见 plugin 家族（随芯片代数不同）：
- `v4l2slp`（slp）
- `imxv4l2`（i.MX V4L2）
- `omx*`（OpenMAX，Gen1/Gen2/Gen3/Gen4 分代）
- `nvv4l2decoder` / `nvv4l2encoder`（Gen6+ 统一命名）

**关键**：不同 i.MX 代数 plugin 名不同，**必须先 `gst-inspect-1.0` 确认实际可用插件名**，不要凭型号记忆写管线。

---

## VPU 直接编程

```bash
# 查询 VPU 能力
vpu_decoder --query
vpu_info
```

VPU API 直接调用需要处理缓冲区对齐、缓存同步（`dcache flush/invalidate`），跨驱动边界传 DMA buffer 时尤其要注意一致性。

---

## 优势与坑点

**优势**：
- GStreamer 插件成熟，社区文档和示例丰富
- 主线内核支持好，不需要 out-of-tree 驱动
- VPU 硬解性能在同代芯片中领先

**坑点**：
- **plugin 名随代数变化**，抄旧项目的管线在新芯片上会失败
- DMA 缓冲区跨进程/跨驱动传递时缓存同步问题导致画面撕裂或花屏
- 编码器支持的分辨率/profile 有约束，超出会失败

---

## 与其他平台对比

| 维度 | RK3588 | NXP i.MX |
|---|---|---|
| 硬解访问 | MPP API（需自己封） | GStreamer plugin 或 VPU API |
| 生态集成 | 需自行集成到管线 | **官方插件，开箱可用** |
| 文档 | 社区资料多 | 官方文档完善 |
| 编程模型 | 同步 API 清晰 | 插件化，异步管线 |

NXP 上如果只是做常规编解码，**优先用 GStreamer 官方 plugin，不必直接调 VPU**——除非有特殊 buffer 管理需求。

---

## 边界与注意

- **不要把 MPP/RGA 思路套到 i.MX**，API 与插件体系完全不同
- plugin 名必须实际查询确认，不能凭i.MX 代数推断
- 遇到花屏/撕裂先怀疑 DMA 缓存同步，而非编码器参数
- 具体芯片（i.MX6 / i.MX8 / i.MX9）能力差异大，查该芯片 datasheet