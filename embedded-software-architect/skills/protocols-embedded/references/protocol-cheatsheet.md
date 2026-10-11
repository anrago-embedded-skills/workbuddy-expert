# 协议速查表

> MQTT / TLS / 5G 常用命令与配置。详细方法论见主 SKILL.md。

以下示例需先选定 HOST 或 TARGET，并确认客户端/库版本、端点和权限。`<...>` 表示必须替换的模板字段。网络连接会产生实际流量；发布、改时间同步和配置模组会改状态。无指定测试 broker/topic 或目标模组手册时，只阅读模板，不发送。

## MQTT

```bash
# HOST or TARGET; client version and broker protocol settings must match.
# Subscribe to a confirmed test topic; expect matching messages or broker rejection.
: "${BROKER:?set to the intended test broker}"
: "${PORT:?set the intended broker port}"
: "${TEST_TOPIC:?set to a confirmed test topic}"
timeout 10s mosquitto_sub -h "$BROKER" -p "$PORT" -t "$TEST_TOPIC" -v

# State-changing probe: publishes to broker. Use only an approved test topic and payload.
: "${BROKER:?set to the intended test broker}"
: "${PORT:?set the intended broker port}"
: "${TEST_TOPIC:?set to a confirmed writable test topic}"
timeout 10s mosquitto_pub -h "$BROKER" -p "$PORT" -t "$TEST_TOPIC" -m 'synthetic-probe' -q 1
```

If `timeout` returns 124 for the subscriber, the 10-second observation window ended; no message can mean no publish, topic/ACL mismatch, session behavior, or transport failure. Preserve client and broker status before assigning cause. Use a supported credential mechanism rather than a literal password in shell history. Verify options with installed client `--help` if versions differ. If `timeout` is unavailable, run interactively and stop it deliberately after the chosen window.

| QoS | 语义 | 相对开销 | 选择条件 |
|---|---|---|---|
| 0 | 最多一次，可能丢失 | 最低 | 允许丢失 |
| 1 | 至少一次，可能重复 | 高于 QoS 0 | 处理具有幂等性或去重能力 |
| 2 | MQTT flow 内恰好一次交付语义 | 较高 | 端到端要求确实需要该语义 |

## TLS 排查

```bash
# TARGET / read-only; timedatectl requires systemd.
date
timedatectl status

# HOST or TARGET with OpenSSL; opens an outgoing TLS connection.
: "${TLS_HOST:?set the peer hostname}"
: "${TLS_PORT:?set the peer port}"
openssl version
timeout 10s openssl s_client -connect "$TLS_HOST:$TLS_PORT" -servername "$TLS_HOST"

# HOST / reads a local certificate file.
: "${CERT_FILE:?set the certificate file to inspect}"
openssl x509 -in "$CERT_FILE" -noout -dates
```

Compare target clock, peer certificate/chain, SNI/hostname and the target TLS library's validation result. Plain `s_client` output is diagnostic and may continue despite verification errors; verify options against that OpenSSL version before treating its exit status as certificate acceptance. A connection failure can also be DNS, routing, firewall, or server policy.

For a systemd target with a confirmed time policy/source, this changes the time synchronization service and is not read-only:

```bash
# TARGET / state-changing service configuration; only with a confirmed time source/policy.
timedatectl set-ntp true
```

Success means the setting was accepted, not that time has synchronized. Query status again and inspect the time source logs; use the documented service on non-systemd targets.

## 5G 模组

```text
# TARGET modem console. Query templates only, if supported by this model/firmware.
AT+CSQ
AT+CEREG?
AT+CGATT?
```

Interpret fields using the exact modem manual and matching 3GPP TS 27.007 revision. Do not use a universal signal threshold. `AT+CGDCONT` changes a packet-data context; construct it only from the confirmed modem manual, SIM/operator APN and context plan. `ERROR` or timeout can mean unsupported command, wrong command mode or transport, not automatically a network fault.

## NDI

```bash
# Check the discovery mechanism for the exact NDI SDK/version and deployment mode.
# Measure payload rate, stream count and loss on a representative target workload.
```

## 边界

- AT commands and response fields require the exact modem/firmware manual
- TLS diagnosis uses target-clock and concrete library errors alongside chain and hostname checks
- MQTT publishing/subscribing against production topics changes live application state; use a designated test broker/topic
