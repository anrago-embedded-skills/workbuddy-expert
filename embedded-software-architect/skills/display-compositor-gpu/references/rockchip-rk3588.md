# RK3588 显示与 GPU 适配

> RK3588 GPU 为 **Mali-G610**（双核），NPU 为 **RKNN**（3 核 NPU）。

## GPU（Mali-G610）

```bash
# GPU 设备
ls /dev/mali*
cat /sys/class/misc/mali0/device/gpuinfo

# 性能状态（降频是性能问题常见原因）
cat /sys/class/devfreq/*.gpu/cur_freq
cat /sys/class/devfreq/*.gpu/available_frequencies
```

### 驱动与 EGL

```bash
# Mali 用户态库路径（常见）
ls /usr/lib/mali/

# EGL 信息
eglinfo
```

**关键**：Mali 驱动版本与 OpenGL ES 能力需确认，不同版本能力差异大。

## RKNPU（RKNN）

```bash
# NPU 设备
ls /dev/rknpu*
cat /sys/kernel/debug/rknpu/version

# 模型转换（x86 主机）
rknn_toolkit_lite --version
```

```python
from rknnlite.api import RKNNLite
rknn = RKNNLite()
rknn.load_rknn('model.rknn')
rknn.init_runtime(core_mask=RKNNLite.NPU_CORE_0_1_2)   # 多核分配
outputs = rknn.inference(inputs)
```

### NPU 要点

- **模型必须转换**（.onnx/.tflite → .rknn）
- **输入尺寸固定**，与实际输入必须一致
- **INT8 量化掉点需实测**
- **多核分配**：`NPU_CORE_0_1_2` 可用三核，注意负载均衡
- 不支持的算子会**回退 CPU**，性能骤降

## DRM 显示输出

RK3588 常见输出：HDMI（Type-C / HDMI2.1）、MIPI DSI、eDP。

```bash
modetest -c -p
cat /sys/kernel/debug/dri/0/state
```

**多图层/无撕裂必须用 DRM atomic**。

## Weston 配置

```bash
export XDG_RUNTIME_DIR=/tmp/weston-runtime   # 必设
weston --backend=drm-backend.so --width=1920 --height=1080
```

```ini
# /etc/xdg/weston.ini（节选）
[core]
backend=drm-backend.so
shell=desktop-shell.so

[shell]
locking=false
```

## 加速引擎选型

| 任务 | 引擎 |
|---|---|
| 图形渲染 | GPU（Mali-G610） |
| AI 推理 | **NPU（RKNN）** |
| 缩放/格式转换 | **RGA2** |
| 编解码 | **RKMPP/VPU** |
| 图像算法（OpenCV） | 先试 NPU，不行再优化 CPU |

**CPU 只做兜底**。

## 边界

- Mali 驱动版本与 GLES 能力需实测确认
- NPU 量化精度必须实测，不能只看转换成功
- GPU 降频会导致性能波动，性能问题先查 devfreq
- 具体型号 GPU/NPU 版本差异，查芯片 TRM