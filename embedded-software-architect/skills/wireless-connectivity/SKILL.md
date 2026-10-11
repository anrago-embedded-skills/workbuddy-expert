---
name: wireless-connectivity
description: |
  嵌入式设备 Wi-Fi、BLE、Thread/Matter 与蜂窝无线链路的关联、配网、漫游、信号质量和射频稳定性分析。
---

# wireless-connectivity

> 嵌入式无线通信：WiFi、蓝牙 BLE、Matter、5G 模组的连接管理、漫游、性能排查。

## 适用范围

无线网络的配置、连接稳定性、漫游、性能问题定位。

## 主技能与辅助读取

- **主技能**：无线侧的关联、配网、信号、漫游和射频稳定性；包括 Wi-Fi、BLE、Thread/Matter，以及蜂窝无线注册或信号链路。
- **辅助读取**：MQTT 经 Wi-Fi 断连时，只有无线关联、信号或漫游记录能支持链路问题时读取本技能；broker/MQTT 错误由 [`protocols-embedded`](../protocols-embedded/SKILL.md) 分析。两层均有证据时可同时读取。
- 若观测到 TCP socket、重传或网络包队列问题，读取 [`embedded-networking`](../embedded-networking/SKILL.md)；蜂窝模组 AT/APN 命令语义归 [`protocols-embedded`](../protocols-embedded/SKILL.md)，只有 USB 枚举、驱动 probe 或主控支持问题证据出现时才辅助读取 [`embedded-bsp-kernel`](../embedded-bsp-kernel/SKILL.md) 或 [`linux-device-drivers`](../linux-device-drivers/SKILL.md)。

## 任务输入、证据分支与交付

输入目标 SoC/板卡和无线模组准确型号、驱动/固件与网络管理器版本、频段/信道、关联与漫游时间、信号/速率/重试采样、对端 AP/手机或 Border Router 记录，以及应用中断时间。只知道 SoC 名称时仍可开始 Linux 通用采样，但模组/驱动能力保持未知。

| 证据 | 主查层与区分步骤 |
|---|---|
| 目标未关联、认证/配网失败 | 对齐关联状态机、AP/peer 日志和凭据/安全模式；不要从 IP 缺失直接归因 DHCP |
| 已关联但 RSSI、速率、重试或漫游同时变化 | 比较多时点链路质量、信道占用、扫描/漫游日志和同地点对照；RSSI 单值不代表可用吞吐 |
| 无线仍关联但 TCP 重传或 socket 队列异常 | 辅助 [embedded-networking](../embedded-networking/SKILL.md)；关联状态不能证明上层路由/对端正常 |
| MQTT/TLS 在无线切换时失败 | 同时对齐 [protocols-embedded](../protocols-embedded/SKILL.md) 的 broker/握手证据和无线事件 |
| BLE discovery/pairing/GATT 或 Thread/Matter commissioning 失败 | 以 peer、协议栈/SDK 版本、配网阶段和服务日志为主；切分电源/射频、匹配/密钥、协议状态 |

交付无线与业务事件时间线、支持或排除候选根因的记录、最小配置/代码范围，以及重复连接、漫游/断连后恢复、低信号和空闲时的接受结果。公共任务交付和证据层级按需引用 [工程工作流](../embedded-debug-workflow/references/engineering-workflow.md) 与 [验证策略](../embedded-debug-workflow/references/validation-policy.md)。

## 命令环境

以下默认是 **TARGET Linux** 且 `iw`/BlueZ 工具存在；先以 `ip link`、`iw dev`、`rfkill`（若安装）和目标日志确认接口及权限。`<...>` 是模板，输出空白也可能是目标接口、驱动、固件或工具版本不支持该字段。状态查询只描述当前观察；扫描可能请求射频扫描并影响正在进行的流量，`iw ... set` 会改无线状态，不能当作只读诊断。

## 平台参考入口

- [RK3588 无线连接适配](references/rockchip-rk3588.md)：目标板确认是 RK3588，且需要核对板级模组、驱动或 SDK 版本时读取。

---

## 核心认知：无线 ≠ 有线

| 维度 | 有线 | 无线 |
|---|---|---|
| 延迟 | 稳定 | **抖动明显** |
| 丢包 | 极少 | 受干扰、重传影响 |
| 带宽 | 高且稳 | 受信号强度/信道共享影响 |
| 断连 | 极少 | **漫游、信号弱、休眠**导致 |

**嵌入式必须假设无线会断**，所有网络设计都要考虑断连重连。

---

## WiFi

### 工具

```bash
# TARGET / read-only snapshot. Set IFACE to an interface shown by `ip link`.
: "${IFACE:?set IFACE to the observed wireless interface}"
ip addr show dev "$IFACE"
iw dev "$IFACE" link           # AP, frequency, signal and last-used bitrate if supported

# Radio scan request; may interrupt/alter active traffic and needs driver support.
iw dev "$IFACE" scan | grep SSID
```

`iw ... link` 预期显示当前 AP、频率、信号和最后使用的速率，或明确显示 `Not connected`。扫描无结果不能证明没有 AP：可能受权限、频段、监管域、扫描能力或过滤方式影响。

设置发射功率不是排查的默认步骤。只有监管域、驱动支持、链路预算与当前批准配置已核实后，才按 `iw` 版本手册将如下 **TARGET 状态变更模板**用于受控试验；数值单位为 mBm，勿照抄占位值。

```bash
# TARGET / state-changing template. Record old state and restore it after the experiment.
: "${IFACE:?set IFACE to the observed wireless interface}"
: "${APPROVED_TXPOWER_MBM:?set an approved numeric mBm value from the applicable regulatory/driver data}"
iw dev "$IFACE" set txpower fixed "$APPROVED_TXPOWER_MBM"
```

成功回显或返回 0 仍须重新查询并验证应用行为；`Operation not supported`、`Invalid argument` 等表示该接口/驱动/域不支持请求。错误功率配置可能破坏链路或违反当地法规。

### 信号强度解读

信号值只能作为与同一设备/驱动的速率、重试、频段、天线链和应用丢包一起观察的线索。没有适用于所有芯片、频段、天线和负载的通用 dBm 分界；用目标业务的接收/发送错误、吞吐和恢复时间定义阈值。

### 省电与保活

- Wi-Fi 省电策略影响功耗/延迟折衷；通过目标 workload 比较后再决定
- DHCP 续租/重绑定行为需结合目标网络管理器日志和实际租约状态确认
- **隐藏 SSID** 的网络需手动指定 SSID

```bash
# TARGET / read-only; query only if the driver supports this interface.
: "${IFACE:?set IFACE to the observed wireless interface}"
iw dev "$IFACE" get power_save
```

关闭省电是可选的 **TARGET 状态变更实验**，不是通用修复。先保存当前值、记录驱动/固件和功耗要求，再在受控条件下测试；之后恢复原设置。

```bash
# TARGET / state-changing experiment. Replace IFACE and restore the recorded state.
: "${IFACE:?set IFACE to the observed wireless interface}"
iw dev "$IFACE" set power_save off
```

成功仅表示设置请求被接受，随后要重读状态并重测业务/功耗；不支持或状态未变时查看目标驱动/固件文档，不反复盲设。

---

## 蓝牙 BLE

### 工具

```bash
# TARGET / read-only BlueZ queries; bluetoothd and bluetoothctl must be available.
bluetoothctl show
bluetoothctl devices
```

### 嵌入式 BLE 注意

- **BLE 与经典蓝牙（BR/EDR）协议不同**，不能混用
- **连接间隔（Connection Interval）** 直接决定功耗与实时性
- **MTU 协商**：长包需协商更大 MTU，否则分片严重
- **配对流程**：常见问题是配对信息丢失导致连不上

```bash
# TARGET / read-only query; replace PEER with a discovered Bluetooth address.
: "${PEER:?set to the target peer address}"
bluetoothctl info "$PEER"
```

Expected output identifies controller/device and reported peer properties; a missing peer may mean no current discovery, expired cache, adapter/daemon absence or unsupported property, not proof that the radio hardware is absent.

---

## Matter

Matter 是智能家居连接标准（基于 WiFi/Thread/BLE）。

### 要点

- **Matter 需 IPv6**，且本地网络需支持
- **配网流程**（Commissioning）是使用门槛，需按标准流程走
- **生态兼容**：需加入 Matter 生态（CSA 认证）

**适用判断**：Matter 主要面向智能家居/IoT 消费类，**工业或专用设备通常不需要**。如果你的产品要进 Matter 生态或对接 Matter 设备，才需要关注。

---

## Thread

Thread 是基于 IPv6 的低功耗 mesh 网络协议。

| 维度 | 说明 |
|---|---|
| 基础 | **IPv6-based** |
| 拓扑 | Mesh（多跳） |
| 低功耗 | 适合电池设备 |
| 依赖 | **需 IPv6 网络 + Border Router** |

**注意**：Thread 与 WiFi 共存（2.4GHz）可能互相干扰，部署时考虑信道规划。

---

## 连接管理通用原则

### 重连退避（所有无线通用）

```
Use bounded backoff with jitter when the peer/service and protocol permit retry. Choose the cap and reset condition from expected recovery time and backend capacity; avoid retrying a whole provisioning/session flow when only an application request should be retried.
```

### 连接状态监控

```bash
# TARGET / read-only route snapshot and bounded ICMP probes; replace peers.
: "${GATEWAY:?set to the configured target gateway}"
: "${KNOWN_PEER_IP:?set to a known permitted target peer}"
ip route show default           # 默认路由是否正常
ping -c 3 "$GATEWAY"            # configured gateway
ping -c 3 "$KNOWN_PEER_IP"       # known permitted peer, not a fixed public address

# 分层判断：ping 网关通但外网不通 → 上游或DNS 问题
```

### 漫游

设备在多个 AP 间移动时的切换：

- 漫游触发可能依 RSSI、driver/daemon policy 和 AP context；用目标日志确认原因
- **漫游中断时间**是业务可感知的关键指标
- 视频业务要重点测**漫游时的丢帧与恢复时间**

---

## 无线性能排查顺序

1. **关联与地址**（`iw link`、`ip addr`、路由）→ 分别检查无线关联与 IP 配置
2. **链路质量变化**（RSSI、PHY rate、重试、丢包）→ 用时间序列和 peer/AP 侧记录互证
3. **信道与负载** → 查询目标支持的统计；`station dump` 依模式和驱动而定，不能在所有客户端接口上假设可用
4. **省电策略** → 先查询，只有受控对照测试才变更
5. **重连日志** → 是否频繁掉线

---

## 边界与注意

- 视频业务需同步记录信号、PHY rate/重试、业务丢帧和漫游；单一 RSSI 不能定因
- 无线抖动无法根治，设计上要容忍断连（重连 +状态机）
- 重连需考虑退避、抖动、恢复条件和会话语义；退避时间依后端与业务要求确定
- Matter/Thread 仅在智能家居/IoT 场景需要，工业场景一般用不上
- 蓝牙需区分 BLE 与经典蓝牙，协议不同

## 主要参考

- Linux Wireless `iw` documentation, including the `set txpower` syntax: https://wireless.docs.kernel.org/en/latest/en/users/documentation/iw.html
