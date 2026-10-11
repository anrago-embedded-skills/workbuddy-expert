# 国科微 Goke 媒体平台适配清单（ARM 示例）

> 仅作为目标 SoC/SDK 确认后的资料收集入口。当前材料未提供精确型号、BSP release、官方媒体手册或 SDK 包；目标构建和板测均未验证。不要从 G300 或其他 Gx 系列名称推断 codec、API、设备节点或 GStreamer element。

## 标准运行时查询

以下为 **TARGET 只读查询**；节点按枚举结果确定，缺少工具时记录镜像包状态：

```bash
v4l2-ctl --list-devices
media-ctl -p
gst-inspect-1.0 --version
gst-inspect-1.0
ffmpeg -version
ffmpeg -hwaccels
ffmpeg -encoders
```

只把实际枚举到的 element/codec 纳入候选，再检查其 caps、配置、设备绑定及匹配 SDK 文档。`gst-inspect-1.0` 全量输出和标准 V4L2/media 查询不会自动证明某 element 使用了指定硬件。

## SDK inventory

实施前收集完整芯片料号、板卡修订、系统镜像/BSP/kernel/SDK 版本、ABI、官方芯片手册、媒体 SDK 文档和 package manifest。对每个相关组件记录：

- 目标包、库、header、driver/device interface 或 plugin 的正式名称与版本。
- codec/profile、input/output format/caps、alignment/stride、最大尺寸和并发限制。
- buffer allocation/import、owner、异步 completion/fence/cache 约定及错误码。
- 编译/链接/加载方式、日志接口及匹配该版本的 vendor example 来源。

如资料缺失，请向方案商/原厂索取该版本文档并标注未知项。未查到依据前不执行 `gk_mpp_test` 等猜测工具，不创建假的 `gk` element 名，也不将搜索字符串当作能力检查结果。

## 调查与验收

按[通用媒体链路工作流](pipeline-workflow.md)定位第一处 count/timestamp divergence。用同一输入、格式、时长和系统负载采集阶段计数、queue 深度、codec submit/complete 时间与资源趋势；只有精确 SDK 和目标枚举支持时才采用 vendor-specific path。没有匹配设备和工具链时只交付假设、证据要求与验收步骤，明确目标构建/板测未执行。

资料来源与验证状态按[共享政策](../../embedded-debug-workflow/references/validation-policy.md)记录；当前未有特定 Goke SDK 手册支持可执行厂商配方。
