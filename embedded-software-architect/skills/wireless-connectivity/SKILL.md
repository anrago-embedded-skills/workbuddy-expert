---
name: wireless-connectivity
description: |
  Wireless connectivity: WiFi, BLE, Matter, Thread, 5G radio link, roaming and signal quality.
  TRIGGER when: WiFi、wifi、wlan、无线、SSID、信号强度、信号弱、掉线、漫游、蓝牙、BLE、bluetooth、BLE 配对、连接间隔、MTU、Matter、智能家居、Thread、mesh、5G 网络、模组信号、连不上蓝牙、蓝牙搜不到、蓝牙连不上、连不上 WiFi、WiFi 连不上、连不上网、WiFi 断、WiFi 掉线、信号差、信号弱、网断了、连不上热点、掉线重连太频繁、漫游掉线、WiFi连不上、wifi连不上、蓝牙连不上、连不上WiFi、连不上wifi、连不上蓝牙、无线连不上、网络连不上、上不了网、断网了、网断了、WiFi断了、网络不稳,
  DO NOT TRIGGER when: 有线网络性能/TCP 层问题（用 embedded-networking）；模组 AT 指令与 MQTT（用 protocols-embedded）,
---

# wireless-connectivity

> 嵌入式无线通信：WiFi、蓝牙 BLE、Matter、5G 模组的连接管理、漫游、性能排查。

## 适用范围

无线网络的配置、连接稳定性、漫游、性能问题定位。

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
# 状态
ip addr show wlan0
iw dev wlan0 link              # 当前连接信息（含信号强度）

# 扫描
iw dev wlan0 scan | grep SSID

# 功率
iw dev wlan0 set wlan0 txpower fixed 1500
```

### 信号强度解读

```bash
iw dev wlan0 link | grep signal
```

| signal | 质量 | 用途 |
|---|---|---|
| -30 ~ -50 | 极好 | 视频流、多路都OK |
| -50 ~ -65 | 良好 | 一般业务可用 |
| -65 ~ -75 | 较弱 | **视频会卡**，仅数据 |
| -75以下 | 差 | 不可用 |

**关键**：**视频/高带宽业务要求 -65dBm 以上**，否则必卡。

### 省电与保活

- **WiFi 省电模式**会导致延迟抖动，实时场景需关闭
- **DHCP 续租**周期影响断连表现，长租约更稳
- **隐藏 SSID** 的网络需手动指定 SSID

```bash
# 查看省电设置
iw dev wlan0 get power save
```

---

## 蓝牙 BLE

### 工具

```bash
bluetoothctl
hciconfig           # 查看适配器
hciconfig -a        # 详细状态
```

### 嵌入式 BLE 注意

- **BLE 与经典蓝牙（BR/EDR）协议不同**，不能混用
- **连接间隔（Connection Interval）** 直接决定功耗与实时性
- **MTU 协商**：长包需协商更大 MTU，否则分片严重
- **配对流程**：常见问题是配对信息丢失导致连不上

```bash
# GATT MTU 协商
bluetoothctl info <dev>
```

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
立即重连会打垮网络 → 必须指数退避
1s → 2s → 4s → 8s → 30s（上限）
```

### 连接状态监控

```bash
# 网络层
ip route show default           # 默认路由是否正常
ping -c 3 <gateway>             # 网关连通性
ping -c 3 8.8.8.8               # 外网连通性

# 分层判断：ping 网关通但外网不通 → 上游或DNS 问题
```

### 漫游

设备在多个 AP 间移动时的切换：

- **漫游时机**由信号阈值驱动，阈值太低会乒乓切换
- **漫游中断时间**是业务可感知的关键指标
- 视频业务要重点测**漫游时的丢帧与恢复时间**

---

## 无线性能排查顺序

1. **信号强度**（`iw link`）→ 弱则先解决覆盖
2. **信道冲突**（同信道干扰）→ 改信道或降功率
3. **带宽占用**（`iw dev wlan0 station dump`）→ 有大流量竞争
4. **省电设置** → 关闭省电重测
5. **重连日志** → 是否频繁掉线

---

## 边界与注意

- **视频业务必须先确认信号强度**，弱信号下卡顿不是代码问题
- 无线抖动无法根治，设计上要容忍断连（重连 +状态机）
- 重连退避是必须的，无脑立即重连会打垮网络
- Matter/Thread 仅在智能家居/IoT 场景需要，工业场景一般用不上
- 蓝牙需区分 BLE 与经典蓝牙，协议不同