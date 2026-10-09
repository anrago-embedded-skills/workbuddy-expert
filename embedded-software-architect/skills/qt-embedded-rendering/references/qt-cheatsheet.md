# Qt 渲染速查表

> Qt/QML 嵌入式常用命令与排查。详细方法论见主 SKILL.md。

## 后端确认

```bash
echo $QT_QPA_PLATFORM              # 当前后端
QT_DEBUG_PLUGINS=1 ./app 2>&1 | grep -i platform
```

| 后端 | 用途 |
|---|---|
| `eglfs` | 直连 DRM/KMS，**嵌入式首选** |
| `linuxfb` | framebuffer，无 GPU |
| `offscreen` | 离屏/无显示环境 |
| `xcb` | X11 |

## 性能诊断

```bash
export QSG_RENDER_TIMING=1     # 每帧耗时（>16.7ms 即掉帧）
export QSG_INFO=1
export QSG_RHI_BACKEND=software  # 软件渲染兜底（性能极差）
```

## 离屏渲染

```bash
export QT_QPA_PLATFORM=offscreen
./app            # 无显示环境渲染
```

```cpp
// 抓取渲染结果
QImage img = window->grabWindow();
img.save("out.png");
```

## GPU 状态（性能问题先查降频）

```bash
cat /sys/class/devfreq/*.gpu/cur_freq
cat /sys/class/devfreq/*.gpu/available_frequencies
cat /sys/class/misc/mali0/device/gpuinfo
```

## EGL 能力

```bash
eglinfo
glxinfo -B        # 确认是否 llvmpipe/swrast（软件渲染）
```

## 掉帧排查顺序

1. `QSG_RENDER_TIMING` 看单帧耗时
2. GPU 利用率 / 频率（**是否降频**）
3. QML item 数量（场景是否过重）
4. 纹理上传是否频繁
5. JS 是否在主线程

## 常见陷阱

| 陷阱 | 正确做法 |
|---|---|
| `opacity: 0` 仍渲染 | 用 `visible: false` |
| layer/effect 过多 | 合并，GPU 带宽打满 |
| JS 在主线程 | 移到 `Worker` |
| 离屏测试性能好 | **不代表上屏性能**（可能走软件渲染） |

## 边界

- 离屏渲染走软件渲染时，性能数据不代表真实表现
- Qt 掉帧不一定 Qt 的问题，先排除上游数据源与下游显示
- 多图层/无撕裂必须用 `eglfs`，`linuxfb` 做不到