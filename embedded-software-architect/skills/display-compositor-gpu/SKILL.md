---
name: display-compositor-gpu
description: |
  Display compositor and graphics stack: Weston/X11 configuration, EGL/GLES capabilities, OpenCV optimization, NPU inference (RKNPU/RKNN).
  TRIGGER when: Weston、wayland、X11、Xorg、合成器、compositor、XDG_RUNTIME_DIR、显示服务、EGL、OpenGL ES、GLES、GPU、渲染后端、软件渲染、llvmpipe、swrast、OpenCV、opencv、图像算法、RKNPU、RKNN、rknn_toolkit、NPU、模型转换、量化、int8 推理、图形界面起不来、显示服务挂了、weston 启动失败、界面全黑、GPU 没工作、跑在软件渲染、图像识别太慢、模型推理慢、AI 推理慢、检测慢、算法太慢、界面起不来、图形界面起不来、weston起不来、weston 启动失败、GPU不工作、没走GPU、跑在软渲染、算法太慢、推理太慢、模型太慢,
  DO NOT TRIGGER when: Qt/QML 界面渲染（用 qt-embedded-rendering）；DRM plane/CRTC 显示输出（用 media-pipeline-linux）,
---

# display-compositor-gpu

> 显示合成器（Weston/X11）、图形栈（EGL/GLES/OpenCV）、NPU 推理（RKNPU/RKNN）。平台适配见 `references/`。

## 适用范围

- 显示合成器配置（Weston / X11）
- 图形栈与硬件加速（EGL / OpenGL ES）
- 图像处理（OpenCV）
- NPU AI 推理（RKNPU / RKNN）

---

## 显示合成器

### Weston（嵌入式首选）

Wayland 合成器，嵌入式场景主流选择。

```bash
# 启动
weston --backend=drm-backend.so --width=1920 --height=1080

# 调试
WESTON_DEBUG=1 weston --backend=drm-backend.so
export XDG_RUNTIME_DIR=/tmp/weston-runtime   # 必设，否则报错
```

| 后端 | 用途 |
|---|---|
| `drm-backend.so` | 直连 DRM/KMS（嵌入式首选） |
| `wayland-backend.so` | 作为 Wayland 客户端嵌套 |
| `x11-backend.so` | X11 兼容 |

**关键**：`XDG_RUNTIME_DIR` 必须设置，否则 Weston 无法启动。

### X11

```bash
Xorg :0
export DISPLAY=:0
xdpyinfo | head -20
glxinfo | head -20          # 确认 GL 能力
```

**问题**：X11 在嵌入式上性能开销大（多余的合成），无 GUI 需求时优先 Weston。

---

## EGL / OpenGL ES 图形栈

### 查询能力

```bash
# EGL/GLES 信息
eglinfo
glxinfo -B
```

```bash
# 确认 GPU 是否被使用（关键）
export __GL_...   # 部分平台需显式指定驱动
```

### 关键点

- **ES 2.0 vs 3.0**：能力差异大，按需求选
- **纹理格式**：嵌入式 GPU 对压缩纹理（ETC2）支持好，但不一定支持桌面格式
- **离屏渲染（FBO）**：不依赖窗口的渲染路径
- **软件渲染回退**：无GPU 时走 llvmpipe，性能极差，需确认是否回退

---

## OpenCV

### 嵌入式注意

- **不要用 OpenCV 做重计算**：arm64 上CPU 密集的 resize/filter 很慢
- **用 IPP 或 NEON 加速**（编译时启用）
- **颜色空间转换是隐形大头**：BGR↔RGB↔YUV 转换开销大
- **多线程注意**：OpenCV 默认用多线程，在 RK3588 上抢大核

```bash
# 确认 OpenCV 实际能力
python3 -c "import cv2; print(cv2.getBuildInformation())"
```

**关键**：OpenCV 的 `cv::setNumThreads` 需谨慎设置——多线程不一定是好事，可能和其他模块抢核。

---

## NPU 推理（RKNPU / RKNN）

### RKNN 工具链

```bash
# 模型转换（x86 主机上做）
rknn_toolkit --version

# 板端推理
rknn_demo model.rknn input.jpg
```

```python
# 使用 rknn-toolkit-lite
from rknnlite.api import RKNNLite
rknn = RKNNLite()
rknn.load_rknn('model.rknn')
rknn.init_runtime()# 初始化 NPU
outputs = rknn.inference(inputs)
```

### 要点

- **模型必须转换**，不能直接跑训练框架格式
- **输入尺寸固定**：转换时指定，与实际输入必须一致
- **量化影响精度**：INT8 量化可能掉点，必须实测
- **NPU 是专用引擎**：不是所有算子都支持，不支持的回退 CPU

---

## 加速路径选型

| 需求 | 路径 |
|---|---|
| 通用图形渲染 | GPU（EGL/GLES） |
| 图像处理算法 | **先考虑 NPU**，其次优化 CPU |
| AI 推理 | **NPU（RKNN）** |
| 大批量像素搬运 | **2D 引擎（RGA）** 或 GPU |
| 编解码 | **VPU/MPP** |

**设计原则**：**CPU 做兜底，专用引擎做主力**。不要指望 CPU 撑住 4K 处理。

---

## 显示链路排查

```bash
# 合成器状态
ps -ef | grep -E "weston|Xorg"

# DRM 状态
cat /sys/kernel/debug/dri/0/state
modetest -c -p

# 确认渲染后端
echo $QT_QPA_PLATFORM      # Qt
echo $WAYLAND_DISPLAY      # Wayland
```

---

## 边界与注意

- Weston 必须设 `XDG_RUNTIME_DIR`，否则无法启动
- 嵌入式优先 Weston，X11 性能开销大
- **确认是否静默回退软件渲染**——回退后性能极差但功能正常，最容易被忽视
- OpenCV 重计算走 NPU，纯CPU 优化有限
- NPU 模型必须转换，量化需实测精度
- GPU/2D/NPU 是不同引擎，任务分配要看瓶颈在哪