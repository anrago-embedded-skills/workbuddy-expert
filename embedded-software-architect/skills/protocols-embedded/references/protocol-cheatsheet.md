# 协议速查表

> MQTT / TLS / 5G 常用命令与配置。详细方法论见主 SKILL.md。

## MQTT

```bash
# 订阅（-v 显示内容）
mosquitto_sub -h <broker> -p 1883 -t "topic/#" -v

# 发布
mosquitto_pub -h <broker> -t "topic/xxx" -m "payload" -q 1

# 带认证/加密
mosquitto_pub -h <broker> -u user -P pass --cafile ca.crt -t "t" -m "msg"
```

| QoS | 语义 | 开销 | 建议 |
|---|---|---|---|
| 0 | 最多一次 | 最低 | 高频遥测 |
| 1 | 至少一次 | 中 | **设备控制推荐** |
| 2 | 恰好一次 | 最高 | 一般不用 |

## TLS 排查

```bash
# 关键：先看时间！证书校验依赖系统时钟
date
timedatectl status

# 测试连通与证书
openssl s_client -connect <host>:443 -servername <host>

# 证书有效期
openssl x509 -in cert.pem -noout -dates
```

**握手失败排查顺序**：
1. **系统时间**（最常见）
2. CA 证书是否正确导入
3. 证书链是否完整
4. 证书是否过期
5. 主机名是否匹配

## 5G 模组

```bash
# AT 指令（依模组型号而定，必须查该型号手册）
AT                       # 确认通信
AT+CSQ                   # 信号强度：0-31，99 未知
AT+CGDCONT=1,"IP","apn"   # 设置 APN
AT+CEREG?                # 网络注册
AT+CGATT?                # 附着状态
```

**信号强度判读**：CSQ > 20 可用，< 10 信号差（TCP 会频繁重连）。

## NDI

```bash
# 依赖 mDNS 发现，需放通 mDNS（UDP 5353）
# 带宽估算：1080p60 约需 20+ Mbps/路
```

## 边界

- AT 指令**厂商不通用**，必须查具体模组手册
- TLS 问题先查时间，再查证书
- MQTT 高频消息需限流，否则可能压垮 broker