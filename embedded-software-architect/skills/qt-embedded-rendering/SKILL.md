---
name: qt-embedded-rendering
description: |
  Qt/QML on embedded Linux: rendering backend selection (eglfs/linuxfb/xcb/offscreen), EGL/OpenGL ES, offscreen rendering, QML frame-drop diagnosis.
  TRIGGER when: Qt、QML、Qt5、Qt6、QQuickWindow、QQuickItem、qmlscene、eglfs、QT_QPA_PLATFORM、离屏渲染、offscreen、渲染后端、QQuickRenderControl、EGL、OpenGL ES、GLES、掉帧、帧率不足、撕裂、QSG_RENDER_TIMING、grabWindow、界面卡、界面卡顿、界面不流畅、界面撕裂、滚动卡、动画卡、列表卡、界面冻住了、窗口不刷新、白屏（Qt）、控件不显示、字体糊了、渲染不出来、界面卡、界面卡顿、界面不流畅、界面撕裂、界面冻住、窗口不刷新、白屏,
  DO NOT TRIGGER when: 非 Qt 的图形渲染（OpenCV 图像算法、AI 推理走 display-compositor-gpu）；纯显示输出 plane/CRTC 配置（用 media-pipeline-linux）,
---

# qt-embedded-rendering

> Qt/QML 在嵌入式 Linux 上的渲染后端、离屏渲染、性能排查。平台特有部分在 `references/`。

## 适用范围

- Qt/QML 应用的嵌入式部署（eglfs / linuxfb / xcb）
- 离屏渲染（offscreen）——无显示器环境渲染、生成缩略图、测试
- QML 掉帧、撕裂、渲染性能定位
- EGL / OpenGL ES 后端选择

---

## 渲染后端选择

| 后端 | 用途 | 适用场景 |
|---|---|---|
| **`eglfs`** | 直连 DRM/KMS，绕过窗口系统 | **嵌入式首选** |
| `linuxfb` | 通过 framebuffer | 无GPU、老平台 |
| `xcb` | X11 | 有 X 环境的开发板 |
| **`offscreen`** | 无窗口渲染 | 无显示环境/自动化测试 |
| `minimal` | 无渲染 | 纯逻辑测试 |

```bash
# 确认当前使用的后端
echo $QT_QPA_PLATFORM
QT_DEBUG_PLUGINS=1 ./myapp 2>&1 | grep -i "loaded.*platform"
```

**关键**：`eglfs` 直连 DRM/KMS，能用多图层与 page flip（硬件无撕裂）；`linuxfb` 只能单缓冲。

---

## Qt 平台插件配置

```bash
# eglfs + 硬件渲染（RK3588 Mali）
export QT_QPA_PLATFORM=eglfs
export QT_QPA_EGLFS_INTEGRATION=xcb_eglfs   # 或eglfs_kms_egldevice
export QT_EGLFS_EGLDevice=1                  # 用 EGLDevice 路径

# 离屏
export QT_QPA_PLATFORM=offscreen
```

---

## 离屏渲染

### 为什么需要

- **无显示器的环境**：CI/服务器上验证 QML 渲染结果
- **生成图片/缩略图**：把 QML 场景渲染成PNG/JPEG
- **渲染前置测试**：改动 QML 后快速看效果，不占设备

### 方法一：QTemporaryFile + grabWindow

```cpp
QQuickWindow* window = createQmlView();   // 已show() 的QQuickWindow
QImage img = window->grabWindow();       // 抓取渲染结果
img.save("out.png");
```

### 方法二：QQuickRenderControl（不创建窗口）

```cpp
QQuickRenderControl rc;
QQuickWindow window(&rc);
window.setContent(...);
window.show();      // offscreen 平台下不真正显示
QImage img = window.grabWindow();
```

**要点**：离屏渲染时GPU 上下文仍需初始化。若环境无 GPU，需设置 `QSG_RHI_BACKEND=software` 走软件渲染（有性能上限，但能出图）。

---

## QML 性能排查

### 开启渲染计时

```bash
export QSG_RENDER_TIMING=1     # 输出每帧耗时
export QSG_INFO=1              # 输出场景信息
export QSG_RENDER_LOOP=basic   # basic / threaded
```

启动后输出类似：
```
qt.scenegraph.renderloop.time: 16.7 ms
```

### 掉帧定位顺序

1. **是不是渲染慢** → 看 `QSG_RENDER_TIMING`，若单帧 >16.7ms（60fps）即掉帧
2. **是不是 GPU 瓶颈** → 看 GPU 利用率（`cat /sys/kernel/debug/dri/0/state`）
3. **是不是场景过重** → 统计 QML item 数量，删除隐藏项、合并 layer
4. **是不是纹理上传太频繁** → 检查是否有 `ShaderEffect` / `Image` 重复加载
5. **是不是 JS 执行慢** → 用 QML Profiler

### 常见性能陷阱

| 陷阱 | 表现 | 对策 |
|---|---|---|
| 过多 layer/effect | GPU 带宽打满 | 合并 layer，减少 `ShaderEffect` |
| 频繁纹理上传 | GPU 占用高、帧率低 | 图片预加载，避免运行时创建纹理 |
| JS 逻辑在主线程 | 帧率抖动 | 移到 `Worker` |
| 未隐藏的 item | 无谓渲染 | `visible: false`（不是 `opacity: 0`） |
| 高分屏渲染 | 填充率瓶颈 | 降低窗口分辨率 |

**关键**：`visible: false` 才能真正跳过渲染；`opacity: 0` 仍参与渲染。

---

## 与硬件加速的配合

Qt 通过 OpenGL ES 调GPU。在 RK3588 上走 **Mali-G610**：

```bash
# 确认 GPU 驱动加载
ls /dev/mali*
cat /sys/class/misc/mali0/device/gpuinfo
```

若Qt 跑在软渲染（`QSG_RHI_BACKEND=software`），性能会显著下降——**离屏测试时注意这不代表真实性能**。

---

## 边界与注意

- **离屏渲染的性能数据不代表真实上屏性能**（可能走软件渲染）
- `eglfs` 与 `linuxfb` 能力差异大，多图层/无撕裂必须 `eglfs`
- QML 掉帧不一定Qt 的问题，可能是上游数据源卡顿或下游显示带宽不足——**先分层定位**
- 平台 GPU 驱动差异大，见 `references/`；具体 GPU 驱动问题查该 GPU 手册