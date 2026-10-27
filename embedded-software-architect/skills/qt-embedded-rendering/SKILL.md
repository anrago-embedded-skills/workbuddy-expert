---
name: qt-embedded-rendering
description: |
  主技能：排查 Qt/QML 嵌入式应用的渲染后端、离屏渲染生命周期和界面掉帧。上述渲染问题先从本技能开始；只有证据指向 compositor、EGL/GPU 或图形驱动时，才辅助读取显示技能。
---

# qt-embedded-rendering

> Qt/QML 在嵌入式 Linux 上的渲染后端、离屏渲染、性能排查。平台特有部分在 `references/`。

## 适用范围

- Qt/QML 应用的嵌入式部署（eglfs / linuxfb / xcb）
- 离屏渲染（offscreen）——无显示器环境渲染、生成缩略图、测试
- QML 掉帧、撕裂、渲染性能定位
- EGL / OpenGL ES 后端选择

## 主技能选择与分流

Qt/QML 的 QPA/platform plugin、scene graph、窗口刷新或界面帧计时问题，先选择本技能：确认 Qt 版本、platform plugin、scene graph 与实际帧耗时。Qt 应用里的媒体采集/编解码/音频问题仍由 [media-pipeline-linux](../media-pipeline-linux/SKILL.md) 主责；MQTT/TLS 应用协议语义由 [protocols-embedded](../protocols-embedded/SKILL.md) 主责；TCP/socket/传输层问题由 [embedded-networking](../embedded-networking/SKILL.md) 主责；SQLite、文件持久化或写满问题由 [data-storage-embedded](../data-storage-embedded/SKILL.md) 主责。若 Qt 渲染证据进一步指向 compositor、EGL/GLES、GPU 或图形驱动，再辅助读取 [display-compositor-gpu](../display-compositor-gpu/SKILL.md)；若证据指向 DRM/KMS plane/CRTC 媒体输出，则读取媒体技能。通用应用线程卡住用 [embedded-debug-workflow](../embedded-debug-workflow/SKILL.md)；内核 IRQ、workqueue 或驱动锁问题转到 [linux-device-drivers](../linux-device-drivers/SKILL.md)。

按需读取 [qt-cheatsheet.md](references/qt-cheatsheet.md)：当需要快速核对 Qt backend、QSG 计时、离屏 API 或 GPU 观测命令时加载；排查其他图形栈问题无需加载。

## 任务入口与完成契约

开始前记录用户看到的问题、目标帧率/延迟、复现窗口、Qt/QML 版本和 build ID、QPA plugin、Qt Quick scene graph adaptation、compositor/显示路径，以及问题发生在 UI 还是媒体输入/输出。平台未知时仍可从应用日志、Qt 能力和帧边界计时继续，不从设备系列推断 EGLFS integration 或 renderer。

| 首个证据差异 | 诊断分支 |
|---|---|
| QPA plugin 缺失、加载错误或 display connection 失败 | 核对目标 Qt 构建、已安装插件和启动环境；若只涉及 compositor 会话，再读 [display-compositor-gpu](../display-compositor-gpu/SKILL.md) |
| QPA/scene graph 可用，但 QML 帧时间或同步/渲染预算超出目标 | 用 QSG timing 与 QML Profiler 区分 polish/sync、JS、纹理上传和绘制成本；明确采样点只覆盖 Qt 还是 end-to-end |
| 输入媒体的 V4L2 sequence、queue 或 encoder 计数先异常 | 转到 [media-pipeline-linux](../media-pipeline-linux/SKILL.md)，Qt 只是承载应用 |
| EGL/GLES renderer、compositor 或 GPU driver 初始化/执行证据先异常 | 辅助读取 display skill，核对实际 vendor library、renderer 和目标 driver |
| DRM connector/mode/plane/CRTC 输出先异常 | 从媒体技能的 DRM/KMS 分支定位；不要把它推给 QML scene graph |
| 通用线程等待/事件循环阻塞是首个证据 | 转到 embedded debug workflow，按锁、线程和等待点取证 |

候选修改与产物围绕首个差异边界：Qt 版本/build identity、实际 plugin/backend 日志、QSG/QML profile、最小 QML/C++/启动参数 diff、前后同场景计时和屏幕验证。验收在相同目标 Qt/BSP、页面内容、尺寸、帧率目标和系统负载下比较 frame-time 分布、呈现结果、输入响应与 CPU/GPU/内存；离屏结果和上屏结果分开记录。没有匹配环境时标明目标构建/板测未执行。

多步骤任务按需参考[通用工程工作流](../embedded-debug-workflow/references/engineering-workflow.md)和[验证政策](../embedded-debug-workflow/references/validation-policy.md)；如共享参考未随集合提供，本技能的任务契约仍可直接使用。

---

## 渲染后端选择

| 后端 | 用途 | 适用场景 |
|---|---|---|
| **`eglfs`** | 直接使用设备图形栈，不依赖桌面窗口系统 | 设备 BSP 提供匹配的 EGLFS integration 时 |
| `linuxfb` | fbdev 软件绘制；较新 Qt 也可按条件使用 DRM dumb buffers | 无可用 EGL/GPU，或使用软件绘制 |
| `xcb` | X11 | 有 X 环境的开发板 |
| **`offscreen`** | 无窗口渲染 | 无显示环境/自动化测试 |
| `minimal` | 无渲染 | 纯逻辑测试 |

```bash
# TARGET · 只读查看当前 shell 的后端选择。空值表示应用可能使用 build default，不代表具体 integration。
echo "$QT_QPA_PLATFORM"
# TARGET · 启动应用并记录插件查找；成功日志标出已加载 platform plugin，缺失/依赖错误应在日志中出现。
QT_DEBUG_PLUGINS=1 ./myapp 2>&1 | grep -i "loaded.*platform"
```

**关键**：EGLFS 的实际后端由 Qt 构建、已安装 integration 插件和 BSP 图形驱动决定。DRM/KMS integration 可使用 page flip；atomic 多 plane 更新还要求驱动和显示硬件支持。LinuxFB 的传统 fbdev 路径是软件绘制；Qt 6.8 文档说明，若构建启用了 DRM 支持、系统支持 dumb buffers，并设置 `QT_QPA_FB_DRM=1`，它可通过 DRM 使用双缓冲与 page flip。不要推定所有设备都具备这些能力。

---

## Qt 平台插件配置

```bash
# TARGET/HOST · 仅设置后续进程环境。选择一个 QPA value；先查当前 Qt build 是否包含该 plugin。
export QT_QPA_PLATFORM=eglfs
# 示例：确认已构建并适用于目标后，才设置 QT_QPA_EGLFS_INTEGRATION=eglfs_kms
# 需要离屏任务时，改为下面的单独值，不要与 eglfs 设置连续执行：
# export QT_QPA_PLATFORM=offscreen
```

---

## 离屏渲染

### 为什么需要

- **无显示器的环境**：CI/服务器上验证 QML 渲染结果
- **生成图片/缩略图**：把 QML 场景渲染成PNG/JPEG
- **渲染前置测试**：改动 QML 后快速看效果，不占设备

### 简单截图：`QQuickWindow::grabWindow()`

```cpp
QQuickWindow* window = createQmlView();   // 已显示并完成场景图初始化的窗口
QImage img = window->grabWindow();       // 读取屏幕窗口的渲染结果
img.save("out.png");
```

`grabWindow()` 适合低频截图或测试，不是通用的无显示器渲染方式；它依赖有效的窗口/场景图，并可能发生 GPU 到 CPU 的读回。

### 应用驱动的离屏渲染：`QQuickRenderControl`

下面的生命周期适用于 Qt 6.0 及以上的图形后端。软件 scene graph adaptation 不调用 `initialize()`/`beginFrame()`/`endFrame()`；Qt 5 使用不同的初始化 API，按实际 Qt 版本官方文档和现有图形上下文实现。

```cpp
QQuickRenderControl rc;
QQuickWindow window(&rc);
// 用 QQmlEngine/QQmlComponent 创建内容，并将根 QQuickItem 设为
// window.contentItem() 的子项。此窗口不调用 show()。
// 在 initialize() 前创建/接入图形设备与上下文；连接 sceneGraphInitialized，
// 并在该信号后设置应用拥有的 render target。此处为生命周期片段，不是完整程序。
if (!rc.initialize()) {
    qFatal("QQuickRenderControl initialization failed");
}

// 每帧在合适的线程和图形上下文中驱动；sync() 与 render() 位于 frame 中：
rc.polishItems();
rc.beginFrame();
rc.sync();
rc.render();
rc.endFrame();
// 将应用拥有的 render target 交给后续显示、纹理合成或 readback。
```

**要点**：RenderControl 把场景图同步和绘制交给应用驱动，需要有效的图形设备/上下文、render target、线程同步和帧调度；不要把 `show()` 或 `grabWindow()` 当作它的初始化/渲染生命周期。对于纯软件 Qt Quick 场景图，使用 `QT_QUICK_BACKEND=software`；`QSG_RHI_BACKEND` 用于选择 RHI 图形 API（如 `opengl` 或 `vulkan`），不能用 `software` 替代软件 scene graph adaptation。Qt 6 的图形后端与 Qt 5 的初始化接口不同。只有创建 graphics API backend 时才按 Qt 6 帧生命周期调用 `beginFrame()`/`endFrame()`；render target 要在 scene graph initialization 之后设置，线程与资源释放遵循目标 Qt 版本文档。

---

## QML 性能排查

### 开启渲染计时

```bash
# TARGET/HOST · 仅影响下一次启动的 Qt app 并将 timing 写入其日志；保留 build/version 和复现负载。
export QSG_RENDER_TIMING=1     # 输出每帧耗时
export QSG_INFO=1              # 输出场景信息
# A/B diagnostic only · 只在问题与 render loop 相关时切换；此设置会改变运行路径。
# export QSG_RENDER_LOOP=basic  # basic / threaded
```

输出格式随 Qt 版本/backend 改变；以下只是解释性占位示例，不是设备实测值：
```
qt.scenegraph.renderloop.time: 16.7 ms
```

### 掉帧定位顺序

1. **是不是渲染慢** → 看 `QSG_RENDER_TIMING`；先由目标刷新率/产品帧率算预算，超预算说明可能错过刷新，不单独证明最终显示掉帧
2. **是不是 GPU 瓶颈** → 使用驱动提供的 GPU 利用率/频率计数器（若有）；`/sys/kernel/debug/dri/0/state` 显示 DRM/KMS plane 与 CRTC 状态，不是 GPU 利用率
3. **是不是场景过重** → 统计 QML item 数量，删除隐藏项、合并 layer
4. **是不是纹理上传太频繁** → 检查是否有 `ShaderEffect` / `Image` 重复加载
5. **是不是 JS 执行慢** → 用 QML Profiler

### 常见性能陷阱

| 陷阱 | 表现 | 对策 |
|---|---|---|
| 过多 layer/effect | GPU 带宽打满 | 合并 layer，减少 `ShaderEffect` |
| 频繁纹理上传 | GPU 占用高、帧率低 | 图片预加载，避免运行时创建纹理 |
| CPU-heavy 的独立 QML JavaScript 计算运行在主线程 | 帧率抖动 | 需要时移入 `WorkerScript`；通过消息传递数据，worker 无法直接访问 QML item 或 `QQmlContext` |
| 隐藏但仍工作的 item | 场景仍执行绑定/动画或保留资源 | 按需求用 `visible: false`，并单独暂停不需要的动画/数据工作 |
| 高分屏渲染 | 填充率瓶颈 | 降低窗口分辨率 |

**关键**：`opacity: 0` 的子树可能被场景图裁剪掉绘制，但绑定、动画、定时器和资源生命周期仍可能继续工作；如果需要停掉可见性相关处理，显式设置 `visible: false` 并按需暂停动画或数据更新。

QML `WorkerScript` 在独立线程和 JavaScript context 中运行脚本，通过 `sendMessage()` / `onMessage()` 与 QML 侧交换数据；它不能直接访问 QML item 的属性、方法或 `QQmlContext` 值。只把不依赖界面对象的计算移入 worker，并在 QML 线程应用返回结果。参见 [Qt WorkerScript 文档](https://doc.qt.io/qt-6/qml-qtqml-workerscript-workerscript.html)。

---

## 与硬件加速的配合

Qt Quick 使用 OpenGL ES 或其他 graphics API 依 Qt Quick backend 和目标构建而定。Rockchip datasheet 将 RK3588 GPU 列为 Mali-G610 MC4；用户态驱动、设备节点、所选 API 与计数器仍取决于 BSP。

```bash
# TARGET · 检查当前 eglinfo 暴露的 EGL vendor/version/extensions；需要目标工具与 EGL display。
eglinfo
# TARGET · 仅已有 X11 session 时，检查该 GLX context 的 renderer/vendor。
glxinfo -B
```

不要从 SoC 名称推断 `/dev/mali*` 或固定 sysfs 路径。使用目标 BSP/driver 文档发现该构建真实暴露的 GPU status 节点和计数器。

若 Qt Quick 使用软件 scene graph（`QT_QUICK_BACKEND=software`），性能与可用特性会不同于硬件图形后端；离屏测试结果不能代表真实上屏性能。

---

## 边界与注意

- **离屏渲染的性能数据不代表真实上屏性能**（可能走软件渲染）
- 先确认实际 EGLFS integration、LinuxFB 路径和 Qt 版本；多 plane/无撕裂能力取决于目标 DRM/KMS 驱动与显示硬件
- QML 掉帧不一定Qt 的问题，可能是上游数据源卡顿或下游显示带宽不足——**先分层定位**
- 平台 GPU 驱动差异大，见 `references/`；具体 GPU 驱动问题查该 GPU 手册

## 主要参考

- Qt for Embedded Linux (Qt 6.8), EGLFS integration selection and LinuxFB DRM dumb-buffer support: https://doc.qt.io/qt-6.8/embedded-linux.html
- QQuickRenderControl (Qt 6.12), offscreen target and frame lifecycle: https://doc.qt.io/qt-6.12/qquickrendercontrol.html
- Qt Quick scene graph adaptations, `QT_QUICK_BACKEND` versus `QSG_RHI_BACKEND`: https://doc.qt.io/qt-6/qtquick-visualcanvas-adaptations.html
- Qt `WorkerScript` type, thread, context and message restrictions: https://doc.qt.io/qt-6/qml-qtqml-workerscript-workerscript.html
- Rockchip RK3588 GPU specification (ARM64 platform fact only): https://www.rock-chips.com/uploads/pdf/2022.8.26/191/RK3588%20Brief%20Datasheet.pdf
