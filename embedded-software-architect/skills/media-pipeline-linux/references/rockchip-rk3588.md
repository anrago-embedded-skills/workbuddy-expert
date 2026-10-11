# Rockchip RK3588 媒体适配清单（ARM64 示例）

> 仅在目标 SoC 已确认是 RK3588 时使用。本页是 SDK/BSP inventory 流程，不保证具体板卡、内核、镜像或 FFmpeg/GStreamer 构建暴露同一接口。当前没有指定 BSP release/SDK/板卡，目标构建和板测未验证。

## TARGET 通用接口盘点

以下命令查询目标当前可见能力；替换尖括号参数，工具缺失或权限错误要单独记录：

```bash
# TARGET · 只读枚举 V4L2/media 拓扑。
v4l2-ctl --list-devices
media-ctl -p
v4l2-ctl -d <ENUMERATED_VIDEO_NODE> --all

# TARGET · 查询当前用户态插件与 codec 构建。
gst-inspect-1.0 --version
gst-inspect-1.0
ffmpeg -version
ffmpeg -hwaccels
ffmpeg -encoders
ffmpeg -filters

# TARGET · 需要 libdrm 工具和 DRM 驱动；只读枚举 connector/CRTC/plane 能力。
modetest -c -p
```

节点/element/codec 枚举仅代表目标当前镜像和驱动暴露的路径。`ffmpeg -hwaccels`、`-encoders` 或 `-filters` 输出不能单独证明对目标 codec、输入格式或 buffer path 的支持。`modetest` 不存在、权限不足或驱动拒绝查询都不是“没有显示硬件”的证明。

## SDK/BSP inventory

Rockchip MPP 维护 [MPP Development Reference 与源码](https://github.com/rockchip-linux/mpp)；它能为对应版本的 MPP 接口提供依据，但不证明某目标镜像已安装该库、service、plugin 或驱动。对项目使用的确切 BSP/SDK 再记录：

- 板卡修订、RK3588 SoC、kernel/BSP/firmware revision、rootfs/ABI、工具链和用户态构建。
- 对应 release 的芯片/媒体手册、SDK 目录或 package manifest；记录 source revision 和相关章节。
- 目标设备当前提供的 V4L2 M2M 节点/format/control，或运行时列出的准确 GStreamer/FFmpeg 组件及版本。
- 输入输出 caps/codec/profile、宽高/stride/对齐、buffer import/allocator、同步/fence、错误和 EOS drain 契约。
- 有关 RGA/MPP 等平台接口时，记录目标 SDK 对支持格式、对齐、缩放范围、并发、fallback 和性能的正式说明，不从芯片名称推断。

未找到精确文档或运行时证据前，不使用猜测的 `mpp_service`、测试程序、`rga` 命令、FFmpeg `rkmpp` codec/filter 名称或固定 debugfs/device 路径。若工程确实需要它们，先从匹配 SDK inventory 取得正式名称和版本用法，再在目标验证。

## 按证据排查

按[通用媒体工作流](pipeline-workflow.md)记录 capture sequence/PTS、queue 前后 buffer identity、转换 service time、encoder submit/completion、输出计数和 DMA ownership/fence。仅当 sequence 首次在采集处分叉时追 MIPI/ISP/V4L2；只有转换或编码阶段计数/延迟异常时核对相应格式与 SDK path；输出 packet 完整而屏显异常时转到 DRM/KMS 或 Qt。

目标设备的 `MemAvailable`、swap、cgroup 事件和 OOM 日志按实际证据检查。仅当已证明路径使用 CMA 且具体 buffer allocation 失败时，再调查该内核暴露的 CMA 状态；设备型号本身不能说明 swap、OOM 或 CMA 原因。

## 修改与验收

修改前记录 negotiated format、plugin/SDK 版本、队列行为和同负载阶段基线。修改后用同一板卡/镜像、输入、codec 参数、分辨率、路数、时长和 CPU 负载比较序号差额、输出计数、延迟分布、画质、内存与 buffer pool；记录构建身份。没有目标设备时，写明目标构建和板测未执行。

资料性质：平台适配清单；Rockchip MPP 的源码/开发参考是 vendor-specific interface 的来源，不替代目标版本与镜像 inventory。按[共享验证政策](../../embedded-debug-workflow/references/validation-policy.md)记录。
