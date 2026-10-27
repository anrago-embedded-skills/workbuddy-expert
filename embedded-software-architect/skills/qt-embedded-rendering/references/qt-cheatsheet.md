# Qt 渲染速查表

> Qt/QML 嵌入式常用命令与排查。详细方法论见主 SKILL.md。

## 后端确认

```bash
# TARGET · 只读查看当前 shell override；空值不代表具体 build-default integration。
echo "$QT_QPA_PLATFORM"
# TARGET · 启动应用并记录 Qt plugin discovery 日志；不是只读查看既有进程。
QT_DEBUG_PLUGINS=1 ./app 2>&1 | grep -i platform
```

| 后端 | 用途 |
|---|---|
| `eglfs` | 无桌面窗口系统的设备图形栈；具体 integration 依构建/BSP 而定 |
| `linuxfb` | fbdev 软件绘制；满足条件的 Qt 6.8+ 可用 DRM dumb buffers |
| `offscreen` | 离屏/无显示环境 |
| `xcb` | X11 |

## 性能诊断

```bash
# TARGET/HOST · 设置只影响接下来启动的 Qt app；保存 Qt version、renderer 和目标刷新率。
export QSG_RENDER_TIMING=1     # 输出 Qt scene graph timing；阈值按实际 frame budget 判断
export QSG_INFO=1
export QT_QUICK_BACKEND=software  # Qt Quick 软件 scene graph adaptation
# QSG_RHI_BACKEND 选择 RHI 图形 API，例如 opengl 或 vulkan；不是软件 backend 开关。
```

## 离屏渲染

```bash
# TARGET/HOST · 仅对后续应用进程生效；offscreen plugin/module 必须在此 build 可用。
export QT_QPA_PLATFORM=offscreen
# Qt Quick 软件绘制可用 QT_QUICK_BACKEND=software；离屏环境/API 仍需按应用验证。
./app            # 启动应用；预期离屏 plugin 初始化，缺失 plugin 会在日志中报错
```

```cpp
// 抓取渲染结果
QImage img = window->grabWindow(); // 仅用于已初始化窗口的低频截图/readback
img.save("out.png");
```

## GPU 状态（按目标 driver 查询）

```bash
# TARGET · 只读枚举可能存在的 devfreq 项；不保证 GPU 节点或统一 metric 命名。
ls /sys/class/devfreq/
```

取得匹配 BSP/driver 文档后，再读取其明确列出的频率/利用率节点和单位。没有标准统一 GPU sysfs 路径；未知节点不能用通配命令代替。

## EGL 能力

```bash
# TARGET · 只读能力查询，依赖目标镜像安装 `eglinfo`；检查 EGL vendor/config/version。
eglinfo
# TARGET · 仅在已有 X11 display 时查看当前 GLX context 的 renderer/version。
glxinfo -B
```

实际 renderer 应从该应用/当前 context 的 GL renderer 信息确认；`eglinfo` 能力枚举不一定对应运行中应用。

## 掉帧排查顺序

1. `QSG_RENDER_TIMING` 看单帧耗时
2. 若目标驱动提供 GPU 利用率/频率计数器则查看；DRM state 是显示状态，不是 GPU 利用率
3. QML item 数量（场景是否过重）
4. 纹理上传是否频繁
5. JS 是否在主线程

## 常见陷阱

| 陷阱 | 正确做法 |
|---|---|
| `opacity: 0` 子树可能被裁剪，但绑定/动画/资源仍工作 | 需要时用 `visible: false` 并单独暂停工作 |
| layer/effect 过多 | 合并，GPU 带宽打满 |
| CPU-heavy 的独立 QML JavaScript 计算在主线程 | 需要时移入 QML `WorkerScript`，通过 `sendMessage()` / `onMessage()` 交换数据；它不能直接访问 QML item 或 `QQmlContext` |
| 离屏测试性能好 | **不代表上屏性能**（可能走软件渲染） |

`WorkerScript` 使用独立的 JavaScript context；只适用于可与 UI 分离的数据计算。worker 返回消息后，再由 QML 线程更新界面。详见 [Qt WorkerScript 文档](https://doc.qt.io/qt-6/qml-qtqml-workerscript-workerscript.html)。

## 边界

- 离屏渲染走软件渲染时，性能数据不代表真实表现
- Qt 掉帧不一定 Qt 的问题，先排除上游数据源与下游显示
- EGLFS KMS 的 page flip/atomic plane 能力依目标 integration 和 DRM 驱动；Qt 6.8 文档中的 LinuxFB DRM dumb-buffer 路径要求构建和设备支持，并设置 `QT_QPA_FB_DRM=1`

## 参考

- Qt 6.8 Embedded Linux platform plugins: https://doc.qt.io/qt-6.8/embedded-linux.html
- Qt Quick scene graph adaptations: https://doc.qt.io/qt-6/qtquick-visualcanvas-adaptations.html
- QQuickRenderControl frame lifecycle: https://doc.qt.io/qt-6.12/qquickrendercontrol.html
- Qt `WorkerScript` threading and message restrictions: https://doc.qt.io/qt-6/qml-qtqml-workerscript-workerscript.html
