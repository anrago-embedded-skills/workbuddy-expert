# RK3588 无线连接适配

> 仅在目标 SoC 确认为 RK3588，且无线模组、板卡和 SDK 版本已识别后读取。SoC 名称不能唯一确定板级无线器件、驱动、固件或管理程序。

## 先识别板级能力

从 BOM/原理图/模组丝印和准确板卡 SKU 确认器件；用 `ip link`, `iw dev`, `rfkill list`（如安装）、`lsusb`/`lspci`（按总线与工具可用性）及本次启动日志核对枚举和驱动绑定。记录固件文件名、内核配置、启动参数与方案商 SDK/提交版本。接口、命令和路径以实际 rootfs/SDK 为准；本页不承诺任何厂商私有工具或固定目录存在。

如果枚举缺失，查总线/供电/复位与内核日志；枚举存在但 netdev 不见，查驱动 probe/firmware 加载；netdev 存在但不关联，按无线协议栈与 AP 日志分支。记录能否发现接口、绑定驱动、成功关联、获取地址及业务恢复这几项预期结果。失败只把调查推进到当前缺失的阶段，不推断具体私有命令。

## WiFi

```bash
# TARGET / read-only; tools may be absent from a minimal rootfs.
ip link show
iw dev

# 连接状态与信号
: "${IFACE:?set IFACE to the wireless interface shown by `iw dev`}"
iw dev "$IFACE" link

# Radio scan request; may affect traffic and requires driver/regulatory support.
iw dev "$IFACE" scan | grep SSID

# TARGET / read-only query; support is driver-dependent.
iw dev "$IFACE" get power_save
```

Expected `iw ... link` reports association/AP, frequency and supported signal/rate fields or `Not connected`; missing fields/tool errors indicate a capability or access limit. Scan output lists observations at that time; empty output does not prove the radio or AP is absent.

### Rockchip 特有注意

- 对照交付 SDK 中驱动源码/模块、固件包、内核配置和方案商 release notes 的精确版本矩阵；不要从“RK3588”推断驱动兼容性。
- 若需评估省电影响，先读取当前配置并以目标视频/控制负载做受控 A/B；改变省电设置会改变无线运行状态和功耗。
- 不以单一 RSSI 作为质量门槛；同步保存同一时窗下的频率、速率、重试、掉线/漫游和应用丢帧。

## 蓝牙 BLE

```bash
# TARGET / read-only BlueZ queries; requires the actual BlueZ tools/daemon.
bluetoothctl show
bluetoothctl devices
```

Expected output describes the active controller and cached/discovered peers; no controller/device may reflect missing BlueZ, no scan/cache, adapter enumeration or access state. Check the corresponding service and boot logs before attributing hardware failure.

发现不到 controller 时，核对模组总线、设备枚举、驱动/固件和 BlueZ 启动日志。若平台把 Wi-Fi/BT 组合在同一模组，依实际模块手册检查供电、共存与复位依赖，不从 SoC 名称推断。

## 4G / 5G 模组

```text
# TARGET modem console. Query only if this exact model/firmware manual supports it.
AT+CSQ
AT+CEREG?
```

**要点**：
- 解释响应范围时匹配模组手册和所实现的 3GPP 版本，不用通用 CSQ→TCP 断连阈值
- 若登记状态或 RAT 变化与应用断连同时发生，对齐模组事件、`ip route`/地址、TCP 和业务日志
- `AT+CGDCONT` 等参数设置会改变模组承载；只按准确型号/固件说明和网络提供的 APN 配置构造，成功回显后仍需检查注册、地址与业务状态
- 命令不支持或无响应时先确认端口、数据模式/AT 模式和固件版本，不重复配置

## Matter / Thread

**注意**：Matter/Thread 能力由板级射频器件、栈版本、Border Router 和产品认证范围共同决定，不可从 SoC 名称推断。

- Matter：按产品目标与对应协议栈/认证文档核对
- Thread：核对实际 802.15.4 radio、Thread 栈和 Border Router 实现

## 边界

- **模组型号必须先确认**，指令集与驱动不通用
- Wi-Fi/BT 驱动与固件的版本关系以具体 SDK/模块 release notes 为准，升级内核需核对兼容性
- 5G 切换断连需应用层处理
- Matter/Thread 需方案商确认支持情况
