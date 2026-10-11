---
name: display-compositor-gpu
description: |
  主技能：排查嵌入式 Linux compositor、EGL/GLES、GPU 驱动和软件渲染回退；嵌入式 OpenCV/NPU 视觉任务可从此入口直达按需参考。Qt/QML 渲染问题先选 Qt 技能。
---

# display-compositor-gpu

> 显示合成器（Weston/X11）、EGL/GLES 与 GPU 图形栈诊断。OpenCV/NPU 推理作为单独的可选视觉扩展。平台相关硬件、SDK、库、工具命令和 API 均需按目标设备及版本确认，示例不保证在所有镜像中存在或可执行。

## 适用范围

- 显示合成器配置（Weston / X11）
- 图形栈与硬件加速（EGL / OpenGL ES）

## 主技能选择与分流

当问题位于 Weston/X11 合成器、EGL/GLES 初始化、GPU 驱动或软件渲染回退时，选择本技能。Qt/QML 应用先从 [qt-embedded-rendering](../qt-embedded-rendering/SKILL.md) 开始，仅在 backend/driver 证据出现后再辅助读取本技能；DRM/KMS plane/CRTC 媒体输出从 [media-pipeline-linux](../media-pipeline-linux/SKILL.md) 开始。通用应用线程或事件循环问题从 [embedded-debug-workflow](../embedded-debug-workflow/SKILL.md) 开始，内核 IRQ/workqueue/驱动锁问题转到 [linux-device-drivers](../linux-device-drivers/SKILL.md)。

当任务内容或诊断证据涉及 OpenCV 图像处理、NPU 模型推理或视觉模型部署时，可从本技能进入并只加载 [vision-inference.md](references/vision-inference.md)，无需先走 compositor 流程；compositor、EGL/GLES 或 GPU 渲染诊断则无需加载该扩展。平台参考按已确认的目标 SoC 和问题证据加载，详见 [generic-linux.md](references/generic-linux.md) 与 [rockchip-rk3588.md](references/rockchip-rk3588.md)。

## 任务入口与完成契约

先记录可见行为（客户端未显示、黑屏、context 失败、软件 renderer、GPU 帧时间或掉频）、目标显示/渲染预算、复现负载、display/compositor session、目标 SoC/BSP/Qt/driver 版本和可获得的应用/系统日志。目标未知时仍可查询通用 Linux compositor/EGL 能力；把专有 runtime、设备节点和指标列为待盘点项，不设 SoC gate。

| 首个异常证据 | 诊断分支 |
|---|---|
| Wayland/X11 client 未连接或 compositor 未运行 | 检查当前 session、socket/环境变量、进程和 compositor 日志；启动 compositor 是有状态操作，不作为只读诊断默认步骤 |
| EGL/GLES context/config 初始化失败 | 记录实际 vendor library、EGL version/config/extensions、Qt QPA integration 和目标 BSP driver；按目标 SDK 检查 ABI/加载路径 |
| 应用 renderer 是软件路径或 llvmpipe/swrast | 查实际 renderer 字符串和装载的 GL implementation，再验证设备/driver 是否被选中；`eglinfo` 本身不一定给出应用当前 renderer |
| GPU-backed renderer 正常但帧耗时超预算 | 使用目标 driver 暴露的频率/利用率/thermal 指标和 app/GPU profile；记录不存在的指标为缺失，不猜 sysfs 路径 |
| DRM connector/mode/plane/vblank 首先异常 | 按 [media-pipeline-linux DRM/KMS](../media-pipeline-linux/SKILL.md) 分流 |
| Qt scene graph/QPA timing 首先异常 | 先用 [qt-embedded-rendering](../qt-embedded-rendering/SKILL.md) |
| 输入实际是 OpenCV/NPU 模型准确率或推理延迟 | 只加载 [vision-inference.md](references/vision-inference.md)，收集模型/runtime/输入身份和 profile |

实施只修改已证明的层，保存 renderer、compositor session、目标版本和变更前证据。交付配置/代码差异、启动日志、renderer/driver/build identity、同一 scene/model/分辨率/负载下的前后延迟/吞吐/准确率/资源和屏显回归；GPU rendering 与 display-present 结果分开。没有目标环境时注明未执行构建/板测。

多步骤任务按需参考[通用工程工作流](../embedded-debug-workflow/references/engineering-workflow.md)及[验证政策](../embedded-debug-workflow/references/validation-policy.md)；缺少共享参考时使用本页的契约继续。

---

## 显示合成器

### Weston / Wayland session

确认目标实际使用 Weston 和 Wayland，再按目标 systemd/session 管理器日志排查；不因“嵌入式”标签默认切换 compositor。

```bash
# TARGET · 只读版本查询；若命令缺失，记录当前镜像未提供该程序。
weston --version

# TARGET · 只读查看当前会话进程；输出用于关联日志与 session owner。
ps -ef | grep -E "weston|Xorg"
```

仅在任务需要启动新的 compositor 进行隔离复现，且已确认当前 display/session、installed backend 与有效且由当前用户拥有的 `XDG_RUNTIME_DIR` 时，使用实际版本手册构造启动参数。**参数模板**如下，不能原样执行；启动可能占用 DRM seat/显示输出、与现有 compositor 冲突并改变屏幕状态。成功观察是预期 compositor log/socket 建立；失败保留启动错误并恢复原 session。

```bash
# TARGET · 参数模板；先替换为此 build 安装并确认的 backend。
XDG_RUNTIME_DIR=<existing-user-owned-runtime-dir> WESTON_DEBUG=1 weston --backend=<confirmed-backend>
```

| Backend | 条件 |
|---|---|
| DRM backend | 目标 build 已安装且当前用户/session 可取得 DRM 输出 |
| Wayland backend | 目标 build 已安装且作为嵌套 Wayland client |
| X11 backend | 目标 build 已安装且存在可用 X server |

具体 backend 名称、配置项和 runtime 目录由目标 Weston 版本与 init/session 管理器决定；错误路径、权限错误与 backend 缺失需要分别记录。

### X11

```bash
# TARGET · 以下是已有 X11 session 的只读查询；`DISPLAY` 需指向实际可用 display。
echo "$DISPLAY"
xdpyinfo | head -20
glxinfo -B                  # 查询该 X session 的 GL renderer/version
```

单独启动 `Xorg :0` 会创建/占用新的图形 session，不能用作通用状态查询；仅在 task 明确要独立 X server 复现并已确认 seat、配置、权限和恢复办法时按目标 Xorg 文档启动。

---

## EGL / OpenGL ES 图形栈

### 查询能力

```bash
# TARGET · 只读查询 EGL vendor/version/config；需要目标镜像安装工具和可用的 EGL display。
eglinfo
# 仅已有 X11 display 时查询当前 GL renderer；无 X server 时此命令失败并不说明 EGL 不可用。
glxinfo -B
```

部分专有驱动会提供自己的环境变量来选择设备或驱动；先查目标驱动/BSP 文档，再使用其明确支持的变量。不要把占位写法当成可执行命令。

### 关键点

- **ES version 与 extension**：按目标 context 的实际 version/extensions 核对，不从应用请求值推断 driver 能力
- **纹理格式**：查询实际 GL/EGL format support 并在目标 context 验证
- **离屏渲染（FBO）**：不依赖窗口的渲染路径
- **软件渲染回退**：检查实际 renderer/backend 字符串；`llvmpipe`/`swrast` 属于软件 renderer 的线索，不推断所有系统用相同 fallback

---

## 图形渲染路径

优先确认应用实际连接的 compositor、EGL/GLES vendor library 和 GPU driver，再区分硬件渲染与软件回退。目标设备能力以驱动信息、安装包和匹配版本的 BSP 文档为准；不要从同系列 SoC 名称推断设备节点、扩展或性能。

OpenCV/NPU 推理、模型转换和量化属于按需加载的视觉扩展，见 [vision-inference.md](references/vision-inference.md)。媒体编解码、音频及 V4L2/DRM 输出链路见 [media-pipeline-linux](../media-pipeline-linux/SKILL.md)。

---

## 显示链路排查

仅在 compositor 启动、客户端连接或 EGL/GPU 渲染路径需要证据时检查这一层。Qt/QML backend 变量由 [qt-embedded-rendering](../qt-embedded-rendering/SKILL.md) 先行确认；connector/mode/plane/CRTC 状态与直接 DRM/KMS 输出问题从 [media-pipeline-linux](../media-pipeline-linux/SKILL.md) 开始。

```bash
# TARGET · 只读查看当前 compositor/X server 进程；可能没有进程或命令受 BusyBox 选项限制。
ps -ef | grep -E "weston|Xorg"

# TARGET · 只读查看当前进程环境；未设置时可能从 session manager 的配置继承其他连接方式。
echo "$WAYLAND_DISPLAY"
```

---

## 边界与注意

- 当前 session 与产品需求决定 compositor；不要仅因目标是嵌入式 Linux 就切换 Weston/X11
- 启动或切换 compositor 会影响 session/display，按目标版本和现有 init/session 配置验证
- **确认是否静默回退软件渲染**——回退后性能极差但功能正常，最容易被忽视
- GPU 图形渲染与显示合成器是不同层，按证据定位边界
