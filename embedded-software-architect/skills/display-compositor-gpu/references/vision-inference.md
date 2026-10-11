# 嵌入式视觉与 NPU 推理扩展

> 仅当任务输入或证据涉及 OpenCV 图像处理、模型部署/转换、量化或 NPU 推理时加载。compositor、EGL/GLES 或 GPU 图形渲染问题不需要此参考。该页是能力盘点和验证工作流，不保证目标 SDK/runtime 已安装；厂商示例必须对应精确 SoC、SDK 和版本。

## 任务输入

先确定模型/数据输入及格式、预处理/后处理、准确率或数值误差目标、batch/分辨率、延迟/吞吐/功耗预算，以及可运行位置（HOST 交叉开发环境或 TARGET）。记录精确 SoC、BSP/firmware、OS/ABI、runtime package/version、模型格式和模型转换工具版本；未知项目标为未知。

## OpenCV 构建信息

**HOST 或 TARGET · 只读诊断**，仅当该环境已安装 Python OpenCV binding 时运行：

```bash
python3 -c 'import cv2; print(cv2.getBuildInformation())'
```

预期输出包含该 OpenCV build 的编译选项、已启用模块与平台信息。`ModuleNotFoundError` 表示此 Python 环境没有该 binding，不说明 C++ library 或硬件不存在。CPU 优化（IPP、NEON 等）需从实际 build 信息与实际架构确认；ARM 例子不代表目标一定为 ARM。

对 resize/filter/color conversion 等操作，先记录同一模型/图像、像素布局和线程配置下的 CPU baseline。将输入/输出格式、stride 和重复转换计入端到端时延；只有测量支持时才调整线程数或选择加速路径。

## NPU / 厂商 runtime inventory

当前没有目标 SDK/BSP 和板卡输入，所以本参考不提供可直接运行的厂商命令、固定 device-node/debugfs 路径、通用 GStreamer element 或未定版本 Python/C API 调用样例。先建立以下清单：

| 项目 | 需要的证据 |
|---|---|
| 主机模型工具 | 精确 toolkit 版本、支持主机 OS/Python、模型输入格式/转换过程、目标平台选项、官方 quick-start/API 文档 |
| 目标 runtime | 镜像 package manifest、runtime/library/header 版本、目标 ABI/依赖、正式 sample 与启动方式 |
| 硬件路径 | 完整 SoC/板卡/BSP/firmware、设备和 driver 绑定、该版本支持的模型格式、operator/precision/layout、核心与内存限制 |
| 功能边界 | 不支持 operator 是失败、显式委托还是 CPU 执行；量化校准与准确率标准；异步完成/缓存/共享 buffer 约定 |
| 验证身份 | SDK/source revision、工具/模型校验值、target build ID、输入集、warm-up 数、batch 和测量时长 |

通用 `gst-inspect-1.0` / FFmpeg 枚举可以查询实际安装的通用媒体 plugin/codec，但不能枚举或证明任意 NPU runtime。按官方 SDK inventory 指引运行其明确版本的 capability/sample 工具，再用目标实际日志/profile 证明路径。

### RKNN 适配入口（ARM64 示例）

只有在确认使用 Rockchip 且模型与目标 SDK 兼容时，参考 [Rockchip AIrockchip RKNN-Toolkit2 源码与版本文档](https://github.com/airockchip/rknn-toolkit2)。该项目说明其工具链包含模型转换/评估与面向 Rockchip 平台的部署接口；这不证明任意 RK SoC、BSP 或镜像均支持当前 runtime/API。先选定 SDK release，再按其 release notes、API reference 和 examples 盘点精确 API、模型格式、operator、目标平台和依赖，不从 README 片段推断本地可执行文件名或路径。

RK3588 等平台仅在 SoC、BSP 与 toolkit/runtime 版本匹配时评估；ARM64 是目标架构例子，不是从 host CPU 或芯片系列可推断的构建配置。不要使用未经目标 SDK 文档证实的 `rknn_toolkit`、`rknn_demo`、`rknn_toolkit_lite` CLI 名、device path 或示例 API。

## 修改与验收

1. 固化转换前模型、数据预处理、量化参数和代表性评估样本。
2. 每次只更换一个受 SDK 支持的变量，保留 CPU baseline；记录模型准确率/误差、端到端 p50/p95 latency、吞吐、CPU/内存/功耗和 runtime fallback/error 日志。
3. 在同一 SoC/BSP/runtime、模型输入/batch/warm-up/负载条件下比较。分别记录 HOST 工具验证、TARGET 模型运行、目标构建和板卡测试；不能用主机 converter 成功代替目标 NPU 推理验证。
4. 交付使用的官方文档版本、SDK inventory、模型/工具/固件身份、输入集与实际输出；未执行的目标构建/板测明确列出。

与 compositor/GPU 渲染的路由和目标限制见 [display-compositor-gpu](../SKILL.md)、[通用 Linux 图形参考](generic-linux.md) 和 [RK 图形参考](rockchip-rk3588.md)。资料和验证范围遵循[共享验证政策](../../embedded-debug-workflow/references/validation-policy.md)。
