# RK3588 无线连接适配

> RK3588 板卡通常通过**外接模组**而非内置芯片实现无线，需先确认模组型号。

## 常见无线模组

| 类型 | 接口 | 驱动 |
|---|---|---|
| WiFi/BT 模组 | SDIO / USB | 厂商驱动（RTL/MTK/Atheros 等） |
| 4G/5G 模组 | USB / UART | AT 指令（移远/广和/紫光展锐） |

**关键**：**先确认具体模组型号**，AT 指令集与驱动不同厂商不通用。

## WiFi

```bash
# 接口识别
ip link show | grep -i wlan
iw dev                    # 无线接口列表

# 连接状态与信号
iw dev wlan0 link

# 扫描
iw dev wlan0 scan | grep SSID

# 省电（实时场景需关闭）
iw dev wlan0 get power save
```

### Rockchip 特有注意

- 部分 SDK 的 WiFi 驱动需匹配**特定内核版本**
- 省电模式会导致延迟抖动，视频场景需关闭
- 信号强度要求同通用文档（视频需 -65dBm 以上）

## 蓝牙 BLE

```bash
bluetoothctl
bluetoothctl info <dev>       # 含 GATT MTU 信息
hciconfig -a
```

**注意**：部分 RK SDK 蓝牙与 WiFi 共用驱动，需注意依赖关系。

## 4G / 5G 模组

```bash
# 常见 AT 指令（依模组而定，必须查该型号手册）
AT                       # 确认通信
AT+CSQ                   # 信号强度（0-31，99 未知）
AT+CGDCONT=1,"IP","apn"   # 设置 APN
AT+CEREG?                # 网络注册状态
```

**要点**：
- 信号弱（CSQ < 10）时 TCP 会频繁重连
- 4G↔5G 切换会断连，应用层需处理
- AT 指令响应慢时，注意超时设置
- **不同厂商模组指令集不同，不要套用**

## Matter / Thread

**注意**：Matter/Thread 通常需**额外协议栈与认证**，不是芯片自带能力。

- Matter：需加入 CSA 生态，完成认证
- Thread：需 **Border Router**（常由 WiFi 芯片承担）
- 多数 RK3588 方案商不内置 Matter 支持，**需确认具体方案**

## 边界

- **模组型号必须先确认**，指令集与驱动不通用
- WiFi/BT 驱动与内核版本绑定，升级内核需确认驱动兼容
- 5G 切换断连需应用层处理
- Matter/Thread 需方案商确认支持情况