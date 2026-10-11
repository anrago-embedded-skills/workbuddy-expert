# MediaTek 平台适配清单（ARM 示例）

> 这是平台资料核对入口，不是对任一 MediaTek SoC/BSP 能力的保证。当前材料没有指定精确 SoC、BSP release 或 SDK 文档；目标构建和板卡均未验证。不要把一个 MTK 系列、Android 实现或旧 SDK 的行为推广到其他目标。

## 先收集通用证据

以下是 **TARGET 只读查询**，前提是相应上游工具已在镜像安装：

```bash
v4l2-ctl --list-devices
media-ctl -p
gst-inspect-1.0 --version
ffmpeg -version
ffmpeg -hwaccels
ffmpeg -encoders
```

记录当前镜像实际可见的设备、media topology、用户态编解码能力和版本；查询输出不表示专用 MDP/codec 接口存在。工具缺失时把包/工具可用性作为待查项。

## SDK inventory

在提及 MDP、VENC/VDEC、DVIP、vendor API 或格式路径前，核对以下目标材料：

- 完整芯片型号、板卡修订、BSP/内核及 firmware revision、用户态 ABI。
- 精确版本的 MediaTek/方案商 SDK、官方数据手册与媒体开发文档。
- SDK 明确暴露的 V4L2 ioctl/capabilities、GStreamer elements 或其他接口/API；记录精确名称及版本。
- 输入输出格式、plane/stride/对齐、拓扑/时钟要求、async completion 和 buffer 生命周期。
- 每一阶段的错误码、可观测日志、最大并发与性能限制；只采用该目标文档有依据的值。

没有对应版本文档时先停在标准接口、源码和运行时证据层，向 SDK/BSP 维护方索取具体章节；不将猜测的工具名、MDP 编程模型或厂商命令作为可运行步骤。

## 修改与验收

按 [媒体链路工作流](pipeline-workflow.md) 在 capture、队列、像素处理、编码和输出边界记录协商格式、buffer ownership、sequence、计数、延迟与错误。确认某平台接口实际存在后再以最小改动验证；在相同目标、输入、路数、时长及系统负载下比较吞吐、端到端延迟、丢帧、画质、CPU/内存和资源。无匹配 SDK/板卡时注明未执行目标构建/板测。

依据和验证状态按[共享验证政策](../../embedded-debug-workflow/references/validation-policy.md)记录。
