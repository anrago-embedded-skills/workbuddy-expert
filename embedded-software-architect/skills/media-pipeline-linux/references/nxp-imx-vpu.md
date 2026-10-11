# NXP i.MX 媒体平台适配清单（ARM 示例）

> i.MX 媒体能力随精确 SoC、BSP release、内核驱动和镜像包变化。本页给出能力核对流程，不将旧项目 element、codec 或私有工具名当作通用接口。当前没有配套目标 SDK/板卡，目标构建和板测未验证。

## TARGET 运行时能力查询

以下命令只读取目标镜像暴露的信息；必须先确认节点，不从 `/dev/videoN` 编号推断 VPU 或摄像头功能：

```bash
v4l2-ctl --list-devices
media-ctl -p
gst-inspect-1.0 --version
gst-inspect-1.0
ffmpeg -version
ffmpeg -hwaccels
ffmpeg -encoders
```

对 `gst-inspect-1.0` 输出中确实存在的 element，再读取该 element 的属性、pad template 和 caps。元素枚举仅说明当前 GStreamer 安装中的插件；需要通过匹配 SDK 文档和负载实测证明它走目标硬件路径。命令不存在时检查镜像包清单和 Yocto image/package manifest。

## 精确 SDK 核对

1. 确认完整 i.MX 型号、板卡、BSP release、kernel/firmware revision 和目标 ABI。
2. 查该 release 的 [i.MX Linux User's Guide](https://community.nxp.com/pwmxy87654/attachments/pwmxy87654/imx-processors/244451/1/UG10163_i.MX_Linux_User%27s_Guide.pdf)、[i.MX Yocto Project User's Guide](https://docs.nxp.com/bundle/UG10164/page/topics/overview.html) 及对应 Release Notes/插件表。指南中的 host/target、镜像包和 element 条件需按其注明版本解释，不跨 SoC 复用示例。
3. 记录该版本实际提供的 V4L2/element/API 名、codec/profile、格式/caps、allocator/DMA buffer 路径和明确支持的分辨率/并发。
4. 核对异步提交/完成、错误和 drain 语义、buffer ownership/fence/cache visibility；不能把“支持 zero copy”泛化为无需同步。

缺少精确 release 手册或运行时枚举时，向 BSP/SDK 维护方补齐版本文件，不使用猜测的 `vpu_decoder`、`vpu_info` 等命令，也不根据旧 `imx*`/`omx*` element 名拼管线。

## 修改与验收

先按 [媒体链路工作流](pipeline-workflow.md) 对齐 capture、转换、encoder 的协商和逐阶段时间戳/计数。只有经过目标枚举和 SDK 手册确认的 element 才进入修改方案。相同目标镜像、输入/分辨率/路数/参数/时长和负载下检查帧差额、延迟、CPU/内存、buffer pool、画质和 EOS drain；没有目标环境时把构建及板测标为未执行。

资料依据：NXP [i.MX Linux User's Guide](https://community.nxp.com/pwmxy87654/attachments/pwmxy87654/imx-processors/244451/1/UG10163_i.MX_Linux_User%27s_Guide.pdf) 和 [i.MX Yocto Project User's Guide](https://docs.nxp.com/bundle/UG10164/page/topics/overview.html)。具体 multimedia plugin 表位于配套 release 文档，需精确到项目使用的版本。
