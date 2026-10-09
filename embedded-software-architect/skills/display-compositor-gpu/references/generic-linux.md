# 通用 Linux 显示与 GPU 适配

> 不特定 SoC 的通用图形栈实践。

## 合成器选择

| 合成器 | 场景 |
|---|---|
| **Weston (Wayland)** | 嵌入式首选，性能好 |
| **Xorg** | 有 X 环境的开发板 |
| **纯 DRM** | 无 GUI 需求，最简 |

## 确认渲染后端（关键）

```bash
# 必须确认是否回退软件渲染
glxinfo -B | grep -i "renderer"
eglinfo | grep -i renderer

# 若显示 llvmpipe / swrast → 软件渲染，性能极差
```

**静默回退软件渲染是最容易被忽视的性能问题**——功能正常但极慢。

## EGL / GLES 能力确认

```bash
eglinfo
# 关注：EGL 版本、GLES 版本、支持的扩展
```

## GPU 频率与降频

```bash
ls /sys/class/devfreq/
cat /sys/class/devfreq/*gpu/cur_freq
cat /sys/class/devfreq/*gpu/available_frequencies
```

**性能波动先查降频**，不要直接归因代码问题。

## OpenCV 注意

```bash
python3 -c "import cv2; print(cv2.getBuildInformation())"
```

- 重计算（resize/filter）在 arm64 上很慢
- 颜色空间转换是隐形开销
- `cv::setNumThreads` 谨慎设置，可能与其他模块抢核
- 编译时启用 NEON/IPP

## NPU 通用注意

不同平台 NPU SDK 完全不同（RKNN / MTK NNAPI / TFLite Delegate / SNPE），**不可移植**。

## 边界

- 平台 GPU 能力差异大，需实测确认
- 未确认渲染后端前不要给性能结论
- OpenCV 重计算应评估是否走 NPU
- NPU SDK 平台相关，不要类比