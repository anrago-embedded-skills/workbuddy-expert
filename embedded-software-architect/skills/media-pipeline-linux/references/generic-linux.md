# 通用 Linux 多媒体能力调查

> 目标 SoC/BSP 未知、平台 SDK 未就绪或专用路径暂不可证实时，从本页继续。通用接口和用户态工具能展示当前镜像/驱动暴露的能力，但不能证明某个硬件加速器存在或不存在。

## 目标设备能力枚举

以下是 **TARGET 只读查询**；工具缺失、权限拒绝、命令选项不同和“设备不支持”要分开记录：

```bash
v4l2-ctl --list-devices
media-ctl -p
gst-inspect-1.0 --version
gst-inspect-1.0
ffmpeg -version
ffmpeg -hwaccels
ffmpeg -encoders
ffmpeg -filters
```

从结果核对当前 V4L2/media topology、实际 GStreamer element/caps、FFmpeg 构建和版本。设备节点必须来自枚举；某个工具没安装不表示硬件功能不可用。复杂问题沿用[媒体链路工作流](pipeline-workflow.md)记录 caps、stride/plane、sequence/PTS、队列、计数、时延和 buffer ownership。

## 软件处理验证模板

在 HOST 文件样本或 TARGET 文件样本上做软件处理时，先确认 `ffmpeg -encoders` 中存在所选软件 encoder。以下为**参数模板**，不可原样执行；替换已存在的输入和新输出路径及已枚举的 encoder。它会读输入、编码并创建输出文件，失败时保留 stderr/返回码；不要把 HOST 成功当目标性能数据。

```bash
# HOST/TARGET · 参数模板；仅在软件 encoder 已由 `ffmpeg -encoders` 确认后使用。
ffmpeg -i <INPUT_FILE> -c:v <CONFIRMED_SOFTWARE_ENCODER> <NEW_OUTPUT_FILE>
```

软件路径适合验证功能和建立一个基线；吞吐、CPU、功耗与多路能力必须在目标上按同负载测量，不能用“软解肯定慢”或 SoC 家族名代替数据。若能力、准确率和预算有正式要求，先确认目标构建和设备是否暴露兼容的硬件路径，再决定是否调整分辨率、帧率、色彩转换或平台。

## DRM/KMS 和 fbdev

```bash
# TARGET · 只读枚举，需要目标安装 libdrm 的 modetest 与 DRM driver。
modetest -c -p

# TARGET · 只读 debugfs 状态；需内核启用/挂载 debugfs 和适当权限，缺失不证明没有 DRM。
cat /sys/kernel/debug/dri/0/state
```

输出状态可显示 connector/CRTC/plane 等驱动信息；能力、权限、page flip、atomic update 和同步都依目标驱动验证。V4L2/ALSA/GStreamer 也是通用接口与具体驱动能力相分离。多媒体显示具体分支见[主技能 DRM/KMS](../SKILL.md)。

## 架构与构建

SIMD 和 toolchain 选项以目标架构/ABI 为准。**ARM32 例子**：当目标 CPU 确实支持 NEON 且所用 GCC toolchain 适用时才考虑 `-mfpu=neon`。**ARM64 例子**：不使用该 ARM32 选项；按目标 compiler/triple 的 `-mcpu`/`-march` 和部署 ABI 确认。主机 CPU 型号不能替代交叉工具链或实际 image 架构。

## 适用边界

- 平台未知时可用通用查询建立目标 capability inventory，不等待 SoC 门槛信息才开始排查。
- 确认平台专有 API/工具影响实现时，再加载匹配 SoC/BSP/SDK 文档并核实精确包、版本、format、alignment 和 buffer/sync 规则。
- 仅目标系统 build/板测能验证目标驱动与硬件；HOST 文件实验、工具输出和源码分析分别报告。

来源与未执行验证按[共享验证政策](../../embedded-debug-workflow/references/validation-policy.md)记录。
