# 通用 Linux 显示与 GPU 适配

> 平台尚未确认、或目标专用路径暂时不可用时可从本页继续。它提供标准 compositor/EGL/GLES 调查入口，不表示目标安装特定 GPU driver、工具或硬件路径。

## 先确认当前图形 session

以下是 **TARGET 只读查询**，需要相关工具已安装：

```bash
ps -ef | grep -E "weston|Xorg|Xwayland"
echo "$WAYLAND_DISPLAY"
echo "$DISPLAY"
```

进程/session 信息用于确定当前客户端连接位置；空值、工具缺失和权限问题都需结合启动管理器、service log 和应用日志分析。

## renderer 与 EGL 能力

```bash
# TARGET · 查询 EGL version/vendor/config/extensions；需目标镜像提供工具和 EGL display。
eglinfo

# TARGET · 仅已有可用 X11 display 时运行；输出该 GLX context 的 renderer/version。
glxinfo -B
```

当 `glxinfo -B` 显示 software renderer，可将其作为该 X11 context 软件渲染的直接线索；`eglinfo` 输出 EGL capability，不一定证明正在运行的应用选择了哪一个 GL renderer。优先取应用实际 `GL_RENDERER`/vendor、Qt logging 或目标 driver profile；别仅凭 toolkit 存在或 `eglinfo` 某扩展项判断应用走硬件加速。

若需观察频率、利用率或温度，先只读枚举目标系统实际暴露的监控节点并查对应 driver 文档：

```bash
# TARGET · 只读列出 devfreq class 项目；此列表不保证有 GPU 项，也不统一 metric 文件名。
ls /sys/class/devfreq/
```

对目标真实节点记录 governor、current/available frequency、thermal throttle 或 utilization 字段及单位；节点不存在或无 counter 时写明不可用，不用未经确认的通配路径代替。

## compositor 选择

Weston、Xorg 或嵌入式 vendor compositor 的取舍依目标应用/API、显示路径、包支持、资源预算和窗口需求；没有通用的性能排序。已有 compositor 下记录 backend、client protocol/session、startup log 和可用 display connector。启动/切换 compositor 属于有状态操作，使用对应技能主文档的模板并先确认目标 session 与恢复方式。

## 分流与验收

- EGL context/config/library 加载错误：核对目标 library、ABI、EGL vendor/config 和匹配 BSP。
- 应用 renderer 为 software：记录 renderer 及实际 library，再判断是否有可用 driver/backend。
- renderer 正常但绘制过慢：量取 app/GPU/render/present 阶段时间和目标可用的调度/频率指标。
- connector/mode/plane/CRTC/vblank 证据异常：转到 [media-pipeline-linux DRM/KMS](../../media-pipeline-linux/SKILL.md)。Qt/QML scene graph/QPA 优先转 [qt-embedded-rendering](../../qt-embedded-rendering/SKILL.md)。

同一 app/scene、分辨率、session、驱动 build、系统负载下比较 renderer、frame-time、present、CPU/GPU/内存和输出质量；把 HOST 工具输出与目标设备采样分开标记。没有目标 runtime/板卡时明确未执行目标构建和板测。

资料/验证限制按[共享验证政策](../../embedded-debug-workflow/references/validation-policy.md)记录。
