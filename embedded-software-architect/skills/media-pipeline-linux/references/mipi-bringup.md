# MIPI-CSI / MIPI-DSI bring-up

> 仅在摄像头 MIPI-CSI 或显示面板 MIPI-DSI 链路的拓扑、lane、带宽、格式或时序问题需要时加载。先确认具体 SoC、传感器/桥接器/面板和 BSP；平台专用节点与命令见 [media-pipeline-linux](../SKILL.md) 中对应的 SoC 参考。

## MIPI-CSI 摄像头

```bash
# TARGET · 只读枚举实际 media graph；工具/权限/driver 缺失分开记录。
media-ctl -p
# TARGET · 参数模板；替换为枚举到的 capture node 后只读格式查询。
v4l2-ctl -d <CAPTURE_NODE> --list-formats-ext
```

- 用 `media-ctl -p` 查看实际 media topology 与 enabled links；再核对 sensor、CSI receiver、ISP 和 capture node 的连接。
- 确认传感器输出格式、尺寸、帧率和 V4L2 节点实际协商值；`/dev/video0` 只是示例，先枚举目标设备。
- 多摄像头或多虚拟通道场景要核对 virtual channel、lane 分配和共享带宽；驱动暴露方式依 SoC/BSP 而异。

### 设备树 endpoint 与接线核对

仅当目标使用设备树描述 sensor 到 receiver 的端点链路，且故障证据指向 topology、lane 或 link frequency 不匹配时，按目标设备 binding 逐项核对：

- 沿 endpoint 的 `remote-endpoint` 关系检查 sensor 与 receiver 两端是否互相指向预期节点，并与原理图及运行时 `media-ctl -p` topology 对照。
- 若两端 binding 支持这些属性，核对 `data-lanes` 的数量与顺序、`clock-lanes` 以及 `link-frequencies` 是否符合目标芯片、sensor 和板级接线要求；只采用原理图、目标 binding 和运行时信息能证实的值。
- 不推测缺失属性的数值，也不把某个 sensor、receiver、bridge 或 panel 的属性要求套用到其他器件；不同 binding 可能要求不同属性或 lane 编号。

## MIPI-DSI 显示面板

```bash
# TARGET · 只读查询 DRM connectors/modes；预期显示当前驱动暴露的输出；需目标安装 modetest 和 DRM 支持。
modetest -c
# TARGET · 只读 debugfs 状态；debugfs 未启用/挂载或权限不足时可能无法读取。
cat /sys/kernel/debug/dri/0/state
```

- 将 connector、mode 与目标 panel 的实际时序对照；具体时序来源依驱动、设备树和面板文档而定。
- lane 数与速率共同限制链路带宽。双 lane 的 1080p60 等高像素率模式需要先核算总带宽与时序开销，不能仅凭分辨率判断可行。
- 黑屏、花屏或无 mode 时，先确认 panel/link 配置是否匹配目标面板；debugfs 和 `modetest` 能力取决于目标内核配置与 DRM 驱动。

## 路由

MIPI capture、sensor 到 ISP/V4L2 的问题仍以本技能为主；单纯 Qt/QML 界面故障先选 [qt-embedded-rendering](../../qt-embedded-rendering/SKILL.md)。PCIe/SATA/NVMe/RAID 设备枚举与健康状态归 [storage-hardware-io](../../storage-hardware-io/SKILL.md)。

## 主要参考

- [Linux common video interface endpoint binding](https://github.com/torvalds/linux/blob/master/Documentation/devicetree/bindings/media/video-interfaces.yaml) — 通用 endpoint/remote-endpoint 与 lane/frequency 属性定义；具体设备还需以目标 kernel 版本及 device binding 为准。
