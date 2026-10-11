---
name: protocols-embedded
description: |
  嵌入式设备应用通信协议的选择、实现与故障分析，包括 MQTT、TLS、NDI、协议转换，以及蜂窝模组 AT/APN 命令和配置语义。
---

# protocols-embedded

> 嵌入式常用协议：MQTT、SSL/TLS、协议转换、5G 模组通信、视频传输协议（NDI）。平台无关。

## 适用范围

嵌入式设备与云端/局域网/其他设备之间的通信协议选型、实现与排障。

## 主技能与辅助读取

- **主技能**：应用协议本身的语义与配置，例如 MQTT topic/QoS/session、TLS 证书与握手、NDI 或协议转换，以及蜂窝模组 AT 命令和 APN 配置。
- **辅助读取**：出现 Wi-Fi/BLE/Thread/Matter 或蜂窝无线关联、漫游、注册、信号问题证据时，读取 [`wireless-connectivity`](../wireless-connectivity/SKILL.md)；出现 TCP 建连、重传、socket 或网络包队列证据时，读取 [`embedded-networking`](../embedded-networking/SKILL.md)。若日志显示蜂窝模组未完成 USB 枚举或驱动 probe，才读取 [`embedded-bsp-kernel`](../embedded-bsp-kernel/SKILL.md) 或 [`linux-device-drivers`](../linux-device-drivers/SKILL.md) 排查对应层。
- **跨层排障**：MQTT 经 Wi-Fi 断连时，按 broker/MQTT 日志与无线关联、信号记录选择主辅技能；两层都有证据时可同时读取，不因传输介质是 Wi-Fi 而排除协议层。

## 协议参考入口

- [协议速查表](references/protocol-cheatsheet.md)：需要 MQTT/TLS/蜂窝模组命令和常见核对顺序时读取；具体 AT 指令仍以模组型号手册为准。

## 任务输入、证据分支与交付

记录协议及版本、客户端/broker 或服务端实现、目标地址、设备时钟与证书信息、请求/响应或握手日志、重试/超时设置、复现条件，以及是否有可安全测试的环境和主题。缺日志、证书或模组准确型号时，列为待核实项；不以成功 TCP 连接推断应用协议正常。

| 证据 | 主要分支 |
|---|---|
| MQTT CONNACK、SUBACK、PUBACK、session 或 topic/filter 行为错误 | 对照 MQTT 版本、QoS、会话配置、topic 完整名称与 broker/client 日志；确认重复或丢失是否符合 QoS 语义 |
| TLS alert、证书链/有效期/主机名错误 | 在运行 TLS 的设备上核对其时钟、根 CA、链、SNI/主机名和具体验证错误；用目标所用 TLS 库版本确认选项 |
| 蜂窝注册、承载/APN 或信号命令响应异常 | 先识别模组型号、固件和 UART/USB 通道，再按该模组 AT 手册及其声明的 3GPP 版本核对；区分查询与会改变连接的设置命令 |
| socket 建连、重传或部分读写异常 | 辅助读取 [embedded-networking](../embedded-networking/SKILL.md)；协议 payload/frame 边界仍在本技能检查 |
| MQTT 经 Wi-Fi 断连同时有关联/漫游事件 | 按时间对齐 broker/MQTT 与无线日志，同时检查两层，不能把传输介质当作根因 |

交付协议状态时间线、支持/反驳假设的原始响应、最小配置或代码变化、幂等/重复/离线行为，以及重复失败和恢复后的接受条件。跨领域工作流程和验证分层按需读取 [工程工作流](../embedded-debug-workflow/references/engineering-workflow.md) 与 [验证策略](../embedded-debug-workflow/references/validation-policy.md)。

## 命令环境与副作用

以下命令须标记为 **HOST 或 TARGET Linux** 后再运行；带 `<...>` 的参数是模板。`date`、版本/状态查询和本地证书查看是读取操作；网络连接测试会创建真实连接。`mosquitto_pub` 会向 broker 发布消息，`timedatectl set-ntp` 会改时间同步服务，模组 AT 配置命令会改 PDP/APN 配置或中断承载。后几类只在测试环境和期望状态明确时执行；它们不是只读诊断。示例使用 `timeout` 限定等待时间；该工具缺失时改用目标所支持的受控测试方式。

---

## MQTT

### 标准工具

```bash
# HOST or TARGET with mosquitto clients; replace endpoint and TEST_TOPIC.
# This creates a network connection and subscribes to the named test topic.
: "${BROKER:?set to the intended test broker}"
: "${TEST_TOPIC:?set to a confirmed writable test topic}"
timeout 10s mosquitto_sub -h "$BROKER" -t "$TEST_TOPIC" -v

```

预期是在指定测试主题上收到与发送一致的 payload，或获得 broker 的连接/订阅拒绝码。`mosquitto_sub` 返回 124 表示观察窗口结束；无消息时先区分未发布、topic 不匹配、ACL/会话问题和离线积压，超时不能单独证明 broker 不可用。QoS 0 为最多一次，QoS 1 为至少一次（可能重复），QoS 2 为恰好一次交付语义且开销更高；选择须匹配应用幂等性和损失要求。

需要主动发布测试消息时使用如下 **有副作用的测试模板**。仅在专用 broker 和确认可写的测试 topic 上运行；命令会改变订阅者可见状态。

```bash
# HOST or TARGET / state-changing network action; exact test topic must be supplied.
: "${BROKER:?set to the intended test broker}"
: "${TEST_TOPIC:?set to a confirmed writable test topic}"
timeout 10s mosquitto_pub -h "$BROKER" -t "$TEST_TOPIC" -m 'synthetic-probe' -q 1
```

预期命令成功返回并有对应 broker PUBACK/订阅端观察；认证、ACL、DNS、连接或协议错误应保留原始输出，以失败阶段分层。

### 嵌入式要点

- **QoS**：按允许丢失、重复处理和端到端幂等要求选择，不固定推荐等级
- **KeepAlive**：与 broker 的服务端限制、网络/NAT 空闲时限和本地检测目标一起配置
- **遗嘱消息（Will）**：broker 在检测到非正常断开后按协议发布；检测时间与会话/retain 语义需验证
- **重连**：对齐 client/broker retry behavior，采用适合服务容量的有界退避与抖动

```c
// libmosquitto fragment: check the installed header/API version and return code.
// Register before mosquitto_connect(); QoS is 0, 1 or 2.
int rc = mosquitto_will_set(mosq, "device/status", (int)strlen("offline"),
                            "offline", 1, false);
if (rc != MOSQ_ERR_SUCCESS) { /* handle configuration error */ }
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
| **时间同步** | 核对目标时钟是否落在证书有效期内；具体验证由客户端 TLS 库和配置决定 |
| **证书链** | 部分平台需完整链，只放叶子证书会失败 |
| **握手耗时** | TLS 握手慢，嵌入式注意超时设置 |

若日志报告证书有效期失败，时钟是一个候选原因；还要检查实际证书链、主机名/SNI、CA 集和 TLS 库返回码。

```bash
# TARGET / read-only; timedatectl requires systemd.
date
timedatectl status
```

预期 `date` 和 systemd 状态能显示目标时钟/NTP 情况；非 systemd 目标或权限不足时改读该系统的时间同步服务日志。若已确认需启用 systemd NTP 同步，这是状态变更：

```bash
# TARGET / service configuration change; only after the time source and policy are known.
timedatectl set-ntp true
```

成功只说明 systemd 接受设置；之后须再次读状态并确认时钟实际收敛。失败通常表示服务/权限/目标支持条件不符，不能推断证书问题已修复。

---

## 5G 模组通信

### 常见架构

```
应用 ←AT 指令/USB/串口→ 5G 模组 ←运营商网络→ 云端
```

### 注意点

- 信号读数只是链路线索；关联注册状态、制式/频段、运营商日志和传输层重传/断连证据
- **网络切换**：4G↔5G 切换会断连，应用层需处理
- **流量消耗**：视频回传是大户，码率与流量直接换算
- **模组 AT 指令**：先核对精确型号与固件手册；命令名和返回语义可能随版本变化

```text
# TARGET modem console; query template only, subject to the exact model/firmware manual.
AT+CSQ
```

查询响应的编码范围需按 3GPP TS 27.007 版本和模组手册解释，不能套用跨制式的信号阈值。`AT+CGDCONT` 及相似配置命令会改变 PDP context；只有确认模组型号、运营商 APN、SIM、context id 和维护窗口后才从对应手册构造，不提供通用可执行值。预期输出包含模组返回的注册/信号字段；`ERROR`、超时或未知命令可能表示固件/命令模式/串口通道不匹配，先确认通道，不重复发送配置命令。

---

## NDI（视频传输）

NDI 是 IP 视频传输协议，用于低延迟视频分发（广播制作、直播制作等场景）。

### 注意点

- **带宽需求高**：多路 1080p 需规划好交换机带宽
- **延迟**：相比裸 RTP 有协议开销，需实测
- **网络质量要求**：丢包直接影响画面
- **发现机制**：按所用 NDI SDK/版本的 discovery 配置核对；不要预设所有部署仅使用 mDNS

**适用判断**：需要低延迟视频多路分发时可评估 NDI。按目标 SDK/版本和实际 payload、并发流数、链路条件测量；不要用单一分辨率的固定带宽估计替代目标测量。

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

- TLS 证书有效期错误时核对目标时钟，并同时检查证书链、CA、主机名/SNI 和库错误
- MQTT QoS 按应用的重复、丢失与幂等要求选择；不设普遍等级
- Wi-Fi/蜂窝场景将退避、协议会话恢复和幂等性作为需验证的设计要求
- 协议转换时注意粘包与超时，长连接需心跳
- 具体模组 AT 指令**必须查该型号手册**，不要套用其他厂商指令

## 主要参考

- Eclipse Mosquitto client documentation: https://mosquitto.org/man/mosquitto_sub-1.html
- Eclipse Mosquitto `libmosquitto` API (including `mosquitto_will_set`): https://mosquitto.org/api2/
- OASIS MQTT Version 5.0 specification: https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
- IETF TLS 1.3 specification: https://www.rfc-editor.org/rfc/rfc8446
- 3GPP TS 27.007 AT command interface; select the revision implemented by the modem: https://www.3gpp.org/dynareport/27007.htm
