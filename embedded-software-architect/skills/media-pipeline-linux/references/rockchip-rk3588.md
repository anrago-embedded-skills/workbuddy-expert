# Rockchip RK3588 平台适配

> RK3588 八核（A55×4 + A76×4），Mali-G610 GPU。硬件加速生态完整，是 Rockchip 系主力平台。

## 硬件加速能力

| 引擎 | 用途 | 访问方式 |
|---|---|---|
| **RKMPP** | 硬编解码（H.264/H.265/VP9/AV1） | MPP API 或 `mpp_service` 系统服务 |
| **RGA2** | 2D 加速：缩放、格式转换、旋转、合成 | librga API 或 `rga` 命令行 |
| **VPU** | 编解码协处理器（与 MPP 同源） | MPP API |
| **Mali-G610** | GPU 图形 | EGL / OpenGL ES / Vulkan |

---

## V4L2 采集拓扑（rkisp / rkcif）

RK3588 摄像头链路典型是 **CSI2 → rkcif → rkisp → rkisp_mainpath**：

```bash
media-ctl -p                # 打印完整拓扑，看 entity 与 link 关系
v4l2-ctl -d /dev/video1 --list-formats-ext   # 查 rkisp 支持格式
```

典型节点：`/dev/media0`（media 控制器）、`/dev/video0`（rkcif 采集）、`/dev/video1`（rkisp mainpath 缩放输出）。

**关键点**：rkcif 出来的原始图要经过 rkisp 处理。需要 ISP 处理（降噪/白平衡/裁剪）就用 rkisp 输出的 node。节点编号**因板卡设计而异，必须先 `media-ctl -p` 确认，不要假设**。

---

## RKMPP 硬编解码

### V4L2 M2M 路径（推荐）

```bash
v4l2-ctl --list-devices                        # 先确认编码器节点编号
v4l2-ctl -d /dev/video30 --list-formats-ext    # 查支持格式

v4l2-ctl -d /dev/video30 \
  --set-fmt-video=width=1920,height=1080,pixelformat=NV12 \
  --stream-mmap=4 --stream-count=100 --stream-to=/tmp/enc.h264
```

### MPP 库 / mpp_service

```bash
systemctl start mpp_service
mpp_service_test        # 或 mpp_enc_test / mpp_dec_test
```

### FFmpeg 调用 RKMPP

```bash
ffmpeg -hwaccel rkmpp -hwaccel_output_format drm_prime \
  -afbc rga -i input.mp4 -c:v h264_rkmpp -b:v 8M -c:a copy output.mp4
```

`-afbc rga` 启用 RGA 做格式转换；不加则走 CPU，CPU 占用显著上升。

### RKMPP 约束（踩坑点）

- 输入必须是**对齐的 NV12/I420**（宽高对齐要求随 codec 不同，通常 16 或 64 对齐）
- 分辨率超出 codec 支持范围会静默失败或报错
- 码率控制（`bps_max`/`bps_min`）直接影响质量与延迟，实时场景设小
- **多实例并发有上限**（通常 4~8 路），超限 fail

---

## RGA2 缩放与格式转换

```bash
rga -i input.rgb -o output.nv12 -f 1-s 1920,1080     # 1=RGBA
rga -i input.nv12 -o output.nv12 -f 0 -r 90         # 旋转 90 度
```

### 性能关键点

- **格式对齐**：源和目标 buffer 的 width/height、**stride** 必须满足对齐要求（通常按 16/64 字节），否则报错或**静默回退 CPU**
- **stride 独立于 width**：即使 width 是 1920，实际 stride 可能更大，必须按真实 stride 传
- **不支持任意缩放比例**：部分芯片对缩放比有区间或最小尺寸限制（如 1920→32 可能走软解）
- **CPU fallback 陷阱**：配置不对会静默回退，排查性能问题时先确认是否走了硬件

1080p 缩放开销对比：RGA 硬件 < CPU+NEON SIMD < 纯 CPU。多路场景必须用RGA。

---

## 内存特性（OOM 排查必读）

RK3588 板子**通常 0 swap**，OOM 就是真 OOM，没有 swap buffer 兜底。

```bash
grep -E "MemTotal|MemAvailable|SwapTotal|CmaFree|Slab" /proc/meminfo
cat /proc/maps | grep -i cma
```

**CMA 是 RK3588 的常见坑位**：摄像头/GPU 需要的连续内存不足时，应用分配失败但总内存看起来还有——这是「有内存却 OOM」的典型原因。

---

## DRM/KMS 特有注意点

```bash
modetest -c -p
cat /sys/kernel/debug/dri/0/state      # 需root
```

RK3588 常见显示链路：HDMI（Type-C / HDMI2.1）、MIPI DSI、eDP。**多图层输出需用 DRM atomic**，fbdev 只能单缓冲。

---

## 调试工具

设备端常见 Rockchip 工具：`mpp_service` / `mpp_enc_test` / `mpp_dec_test`、`rga`、`drm_info`、`v4l2-ctl`、`media-ctl`。

---

## 边界与注意

- **MPP/RGA 是 Rockchip 专属**，联发科/全志/NXP 无等价 API，不要硬套
- RGA 性能问题优先怀疑**对齐/stride 配置错误导致回退 CPU**
- OOM 排查先确认是否 0 swap 板，CMA 占用是重点排查项
- 摄像头节点号和拓扑因板卡而异，**必须先 `media-ctl -p` 确认**