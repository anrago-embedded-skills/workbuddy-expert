# 案例：probe 返回 `-EPROBE_DEFER`

> **合成教学夹具**：请求、日志和 resource 名称是构造的练习输入，不是现场日志，也不表示任何真实驱动、内核或设备已验证。

## 输入

```text
[SYNTHETIC TARGET dmesg] example-sensor 2-0036: supply vdd not ready: -517
[SYNTHETIC TARGET debugfs] devices_deferred contains: 2-0036 example-sensor
[SYNTHETIC TARGET sysfs] /sys/bus/i2c/devices/2-0036 has no driver symlink
```

代码片段仅说明保留原始错误：

```c
/* [SYNTHETIC FRAGMENT] 需按目标内核 API 和真实资源名适配。 */
supply = devm_regulator_get(dev, "vdd");
if (IS_ERR(supply))
        return dev_err_probe(dev, PTR_ERR(supply), "failed to get vdd\n");
```

## 竞争假设与区分证据

| 假设 | 区分证据 | 判断方向 |
|---|---|---|
| 合法 supplier 尚未 probe | consumer 的真实资源获取 errno 为 `-EPROBE_DEFER`；deferred 条目与目标 regulator/GPIO/clock provider 节点和 driver 状态对应 | 保留 defer，找出 provider 尚未就绪原因；确认 provider 后续 probe 是否触发 consumer 重试 |
| 必需 supplier 根本未描述或未启用 | 对照 binding 中的 supply/clock/reset/GPIO 属性、runtime tree、provider driver/config 与板级连接 | 这常是持续不就绪问题；盲目重试不能修正缺失描述 |
| provider 自己 probe 失败 | 同一启动时段的 provider 错误、它的 deferred/resource 条目和父依赖 | 先查 provider 错因，不在 consumer 中绕过 |
| 其他 errno 被包装或误判成 defer | 查看返回路径、`PTR_ERR()`/转换和 `dev_err_probe()` 调用；追到具体资源 API | 只在 framework 返回 defer 时保留 defer；真实 `-EINVAL`、`-ENODEV` 等仍按原错误处理 |
| defer 后留有已注册子设备/接口 | 检查 probe 错误路径对已注册对象的清理和注册先后 | 把硬依赖获取提前；避免返回 defer 时留下会触发重试循环的子设备 |

debugfs 中 `devices_deferred` 是否存在受目标配置/内核影响。条目消失也不能单独证明设备已正确工作；仍要检查驱动绑定及后续 I/O。

## 最小改动、成功证据与回归

如果这是硬件必需资源且目标 binding 确认它确实存在，按真实 consumer API 取得资源，并原样传播错误：

```c
/* [SYNTHETIC FRAGMENT] 仅用于返回真实 provider errno 的既有 probe 路径。 */
ret = acquire_required_supply(dev, &supply); /* 占位：按目标 API 替换 */
if (ret)
        return dev_err_probe(dev, ret, "failed to acquire required supply\n");
```

不要通过吞掉 defer、硬编码电压、改成任意延迟重试、把必需依赖当 optional 或伪造成功来“修复”。如果资源在设计上可选，只使用目标 binding 与 API 明确支持的 optional 语义。

预期成功证据：supplier 节点/驱动就绪；consumer 在资源可用后再次 probe；deferred 条目按目标行为清除；设备绑定；错误路径没有残留注册对象。以上为期望，不是已测结果。

回归覆盖 provider 晚注册后重试、provider 持续失败、consumer probe 在后续资源失败时清理已取资源、重复 bind/unbind 以及启动顺序变化。本案例未提供目标源码树或硬件，未进行目标构建或板卡测试；真实验证依赖目标树、配置、provider 与硬件。依据：[设备模型 probe/defer 规则](https://docs.kernel.org/driver-api/driver-model/driver.html)、[`dev_err_probe()` 与 deferred reason](https://docs.kernel.org/driver-api/infrastructure.html)。
