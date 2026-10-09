---
name: protocols-embedded
description: |
  Embedded protocols: MQTT, SSL/TLS, 5G modem AT commands, NDI video transport, protocol-conversion gateways.
  TRIGGER when: MQTT、mosquitto、broker、QoS、遗嘱消息、SSL、TLS、证书、CA、握手失败、https、mTLS、5G、4G、模组、AT 指令、AT+CSQ、APN、NDI、协议转换、Modbus 网关、云端对接、远程控制、连不上云端、云端连不上、消息发不出去、订阅收不到、证书报错、证书失败、握手失败、加密问题、4G 没信号、5G 掉线、模组没注册上、MQTT连不上、mqtt连不上、MQTT 断了、mqtt 收不到、云端连不上、订阅收不到、消息发不出去、TLS 失败、TLS 报错、SSL 失败、证书不对,
  DO NOT TRIGGER when: TCP 粘包/重连等传输层问题（用 embedded-networking）；WiFi/蓝牙无线连接（用 wireless-connectivity）,
---

# protocols-embedded

> 嵌入式常用协议：MQTT、SSL/TLS、协议转换、5G 模组通信、视频传输协议（NDI）。平台无关。

## 适用范围

嵌入式设备与云端/局域网/其他设备之间的通信协议选型、实现与排障。

---

## MQTT

### 标准工具

```bash
# 连接测试
mosquitto_sub -h<broker> -t "topic/#" -v
mosquitto_pub -h <broker> -t "topic/xxx" -m "payload" -q 1

# QoS 级别差异
#q0 最多一次（可能丢）
# q1 至少一次（可能重复）
# q2 恰好一次（最慢）
```

### 嵌入式要点

- **QoS 选 q1**：设备控制场景通常够用，q2 开销大
- **KeepAlive**：配合超时重连，心跳周期要小于 broker 的 keepalive
- **遗嘱消息（Will）**：设备异常掉线时自动通知，避免"假在线"
- **重连退避**：网络抖动时立即重连会打垮 broker

```c
// 遗嘱消息：连接建立时就注册，断线时 broker 自动发布
mosquitto_will_set(mosq, "device/status", "offline", 3, 0);
```

### 常见问题

- 设备显示在线但收不到消息 → 检查订阅的 topic 是否匹配、通配符层级
- 高频消息堆积 → QoS 过高或 broker 性能不足，设备侧应限流

---

## SSL / TLS

### 嵌入式 TLS 注意

| 关注点 | 说明 |
|---|---|
| **CA 证书** | 内网自签需导入 CA，证书过期会导致连不上 |
| **时间同步** | **证书校验依赖系统时间**，时间不对必然握手失败 |
| **证书链** | 部分平台需完整链，只放叶子证书会失败 |
| **握手耗时** | TLS 握手慢，嵌入式注意超时设置 |

**最常见坑**：**设备时间不对导致 TLS 握手失败**。表现为"证书无效"，实际是时钟问题。

```bash
# 确认时间
date
timedatectl status

# NTP 同步
timedatectl set-ntp true
```

---

## 5G 模组通信

### 常见架构

```
应用 ←AT 指令/USB/串口→ 5G 模组 ←运营商网络→ 云端
```

### 注意点

- **信号质量决定一切**：`AT+CSQ` 看信号强度，弱信号下 TCP 频繁重连
- **网络切换**：4G↔5G 切换会断连，应用层需处理
- **流量消耗**：视频回传是大户，码率与流量直接换算
- **模组 AT 指令**：各家模组指令集有差异（移远/广和/紫光展锐），需按型号适配

```bash
# AT 指令示例（具体依模组而定）
AT+CSQ          # 信号强度（0-31，99 表示未知）
AT+CGDCONT=1,"IP","apn"   # 设置 APN
```

---

## NDI（视频传输）

NDI 是 IP 视频传输协议，用于低延迟视频分发（广播制作、直播制作等场景）。

### 注意点

- **带宽需求高**：多路 1080p 需规划好交换机带宽
- **延迟**：相比裸 RTP 有协议开销，需实测
- **网络质量要求**：丢包直接影响画面
- **发现机制**：NDI 通过 mDNS 自动发现，同网段需放通 mDNS

**适用判断**：需要低延迟视频多路分发时 NDI 是好选择，但要先算带宽。

---

## 协议转换网关

嵌入式常见的"旧设备接新协议"场景：

| 转换方向 | 常见方案 |
|---|---|
| Modbus ↔ MQTT | 串口/TCP Modbus + MQTT 网关 |
| 自定义协议 ↔ 云平台 | 协议转换 SDK |
| 现场总线 ↔ 边缘节点 | 工业网关 |

**关键**：协议转换要处理**超时、重传、粘包**（见 `embedded-networking`）。

---

## 边界与注意

- TLS 失败优先查**系统时间**，不要一上来怀疑证书
- 嵌入式设备建议用 QoS1，q2 开销通常不值得
- WiFi/5G 网络下必须做重连退避，否则会打垮服务端
- 协议转换时注意粘包与超时，长连接需心跳
- 具体模组 AT 指令**必须查该型号手册**，不要套用其他厂商指令