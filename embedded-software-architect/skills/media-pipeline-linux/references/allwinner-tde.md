# 全志 Allwinner 平台适配清单（ARM 示例）

> 这是平台资料核对入口，不是对任一 Allwinner SoC/BSP 能力的保证。当前材料没有指定芯片完整料号、BSP release 或 SDK 文档；目标构建和板卡均未验证。不要按系列名推断引擎、库、插件、节点、格式支持或性能。

## 先收集通用证据

以下是 **TARGET 只读查询**，工具缺失、权限不足和功能不支持应分别记录：

```bash
v4l2-ctl --list-devices
media-ctl -p
gst-inspect-1.0 --version
ffmpeg -version
ffmpeg -hwaccels
ffmpeg -encoders
```

媒体拓扑和实际协商格式只能说明目标驱动当前暴露的路径。工具/节点缺失时先核对镜像包和内核配置，不据此断定设备没有加速能力。

## SDK inventory

在讨论 TDE/VE/DISP、codec 或其他专用功能前，请补齐：

- 精确 SoC 与板卡修订、BSP/内核 revision、镜像发行版和目标 ABI。
- 目标 SDK 包/版本、官方芯片手册与软件开发手册的具体章节或文件名。
- 该版本明确支持的输入/输出格式、宽高/stride/对齐约束、并发和异步完成规则。
- 可见的 kernel driver/device interface、实际安装的 runtime/library、正式支持的 GStreamer element 或 FFmpeg codec/filter 名称。
- buffer 分配/导入、DMA-BUF ownership、fence/cache visibility、错误返回及同步释放契约。

资料未覆盖的问题保留为待确认项，向目标 SDK/BSP 维护方索取对应版本文档或源码。只有在运行时枚举和匹配文档均确认后，才写平台 API 或使用其样例；不要虚构 `libtde`、提交函数、测试工具或固定设备路径。

## 修改与验收

逐阶段记录 capture、队列、转换、编码和输出的 format/caps、sequence/PTS、计数、延迟与错误。修改前先证明目标路径使用了所讨论的硬件/SDK 接口；修改后用相同输入、路数、运行时长和系统负载比较吞吐、延迟、画质、资源和丢帧。没有确切 SDK/设备时，结果标记为源码/通用工作流分析，板测未执行。

其他平台差异及 DMA/异步 buffer 一般原则见[媒体链路工作流](pipeline-workflow.md)；资料记录依[共享验证政策](../../embedded-debug-workflow/references/validation-policy.md)。
