# 海思 Hi3516 媒体平台适配清单（ARM 示例）

> 这是平台差异调查入口，不是 Hi3516 系列能力表。Hi3516 子型号和 SDK/BSP 发布差异需要用确切型号手册验证；当前材料未指定 SDK 文档或目标板，目标构建和板测未验证。传统 MPP、MPI、VDEC/VENC、IVE、VO 等术语不表示任一当前镜像实际提供对应接口。

## 通用 TARGET 证据

以下为标准 Linux 能力查询；工具和节点可能因镜像而缺失：

```bash
v4l2-ctl --list-devices
media-ctl -p
gst-inspect-1.0 --version
gst-inspect-1.0
ffmpeg -version
ffmpeg -hwaccels
ffmpeg -encoders
```

将输出与目标镜像包清单、内核配置、运行时日志和确切 SDK 文档对照。`gst-inspect-1.0` 只列出已安装 plugin/element；需核对实际 caps、设备绑定和硬件路径，不能只凭 element 名认定加速。

## SDK inventory

实现或调试厂商媒体链路前，记录：

- 完整 Hi3516 型号、板卡修订、boot/kernel/BSP/SDK 版本、目标 ABI。
- 官方 SDK/芯片手册名称、版本和相关章节；缺失文档向 SDK 维护方索取。
- 该版本明确提供的 library/header/API 和运行时插件/工具名称及其包来源。
- codec/profile/分辨率/格式限制、buffer/pool/stride 约束、异步 completion/EOS drain 和错误语义。
- 多消费者 buffer 的所有权、fence/cache coherence 和资源释放路径。

在手册及 SDK 包核实函数和结构体之前，不提供 `MPI_*` 调用片段、编解码器命令或固定设备节点；名称近似 Rockchip MPP 也不能用于推断 API 兼容性。

## 修改与验收

按[媒体链路工作流](pipeline-workflow.md)固定负载并逐阶段记录 sequence/PTS、buffer ownership、输入/输出计数、时延和错误。只在对应 SDK 文档和目标枚举都支持时选取平台 API。用相同目标固件、输入、格式、分辨率、路数、编码参数和时间窗比较丢帧、延迟、输出质量和资源；当前资料无实机运行结果。

依据和目标验证状态按[共享验证政策](../../embedded-debug-workflow/references/validation-policy.md)记录。
