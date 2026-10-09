# 通用 Linux BSP 适配

> 目标平台未知、或使用通用 ARM64 SoC 时的通用做法。Linux 内核接口本身是标准的，平台差异在能力与芯片文档。

## 主线内核 vs BSP

| | 主线内核 | 厂商 BSP |
|---|---|---|
| 优势 | 新、稳定、社区支持 | 包含厂商专有驱动 |
| 劣势 | 缺专有驱动（MIPI/ISP/VPU等） | 老、有 patch、可能有 bug |
| 适用 | 标准外设、不需专有加速 | 需要 MIPI CSI / ISP / VPU |

```bash
# 确认当前内核来源
uname -a
cat /proc/version
```

**决策**：如果目标板需要 MIPI 摄像头、ISP、特定硬解，通常必须用 BSP；如果只需标准外设（USB/网口/串口/标准显示），主线内核更省心。

## 设备树通用检查

```bash
cat /proc/device-tree/model       # 板型
ls /proc/device-tree/            # 节点
dtc -I dtb -O dts /proc/device-tree/ 2>/dev/null > running.dts
```

**关键**：确认运行时设备树，可能含 dtso overrides，不能只看源文件。

## Buildroot（通用用法）

```bash
make menuconfig
make -j$(nproc)
make linux-rebuild
```

```
output/target/    # 根文件系统
output/images/    # 镜像
```

## Yocto（通用用法）

```bash
bitbake-layers show-layers
bitbake <image-name>
```

## systemd 通用检查

```bash
systemctl list-units --failed       # 失败的单元
journalctl -b -p err                # 本次启动的错误
systemctl-analyze                   # 启动耗时分析
```

## 边界与注意

- 平台未知时**先确认型号**再决定主线还是 BSP，不要盲目开工
- 主线内核缺驱动时，优先评估 BSP 成本 vs 手写驱动成本
- 未确认硬件能力前不要承诺性能指标
- 具体芯片寄存器/时钟配置必须查该芯片 TRM