# RK3588 显示与 GPU 适配清单（ARM64 示例）

> 只在目标 SoC 已确认 RK3588 且问题涉及 EGL/GLES、Weston 或图形 driver 时加载。Rockchip datasheet 将 RK3588 GPU 列为 ARM Mali-G610 MC4，但这不保证某镜像选用相同 Mali driver、EGL library、kernel module、设备节点或 devfreq 接口。[Rockchip RK3588 Brief Datasheet](https://www.rock-chips.com/uploads/pdf/2022.8.26/191/RK3588%20Brief%20Datasheet.pdf)。当前目标 BSP/板卡未指定，目标构建和板测未验证。

## 标准 TARGET 查询

以下查询只查看目标已暴露的通用图形状态；工具可能缺失，且 `glxinfo` 需要已有 X11 display：

```bash
ps -ef | grep -E "weston|Xorg|Xwayland"
echo "$WAYLAND_DISPLAY"
echo "$DISPLAY"
eglinfo
glxinfo -B
```

记录 renderer/vendor/version、加载库、compositor/backend/session 和错误日志。`eglinfo` 的能力列表不等于活跃应用使用的 renderer；`glxinfo -B` 只代表其当前 GLX/X11 context。应用实际 renderer/profile 比 SoC 名称更能证明当前路径。

## BSP/SDK inventory

按设备实际安装的 kernel/userland 和板卡修订核对：

- BSP/kernel/firmware/Qt/Weston/Mesa 或 vendor runtime 版本与 ABI。
- 实际 EGL vendor JSON/library、driver/backend 模块、应用装载路径及官方 matching release note。
- renderer string、EGL/GLES version/extensions、可用 DRM render node 和权限（节点名称由实际枚举给出）。
- 只有实际存在时才读取对应 GPU frequency/utilization/thermal counter，并从 BSP 文档确认路径、单位和采样语义。

SoC 手册是功能背景，不支持具体用户态文件、debugfs 节点、频率表、Weston backend 名或 Mali API 的结论；不写未经目标 BSP 文档证明的 `/dev/mali*`、`gpuinfo`、`/usr/lib/mali/` 或 `/sys/class/devfreq/*.gpu/*` 配方。若这些路径对诊断必要，先从匹配 BSP/SDK 文档确认并对目标枚举。

## 路由、修改与验收

若首个差异位于 connector/mode/plane/CRTC/atomic commit，使用 [媒体技能 DRM/KMS 参考](../../media-pipeline-linux/references/rockchip-rk3588.md)；若位于 Qt QPA/scene graph，使用 [Qt skill](../../qt-embedded-rendering/SKILL.md)；OpenCV/NPU 模型转换或推理仅在任务需要时使用 [vision-inference.md](vision-inference.md)。不同层的时延与指标不能混作“GPU 慢”。

仅对已证实的 renderer/driver path 修改设置；在相同 RK3588 板卡、BSP/driver、session、scene/分辨率和负载下比较实际 renderer、render/present frame-time、可用频率/thermal、CPU/内存和屏显质量。无目标 BSP/板卡时注明构建与板测未执行。参考资料的适用版本与验证状态遵循[共享验证政策](../../embedded-debug-workflow/references/validation-policy.md)。
