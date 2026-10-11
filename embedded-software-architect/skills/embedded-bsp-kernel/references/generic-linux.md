# 通用 Linux BSP 适配

目标平台未知时，先确定 SoC、板卡、内核源码和发行/构建系统。不要按 CPU 家族推断外设能力；平台能力和寄存器细节以目标 SoC TRM、板级文档、目标内核绑定为准。

## 主线内核与厂商 BSP

| 方案 | 适用判断 |
|---|---|
| 主线内核 | 外设有主线驱动、设备树绑定和板级支持，且无需厂商专有媒体/加速接口 |
| 厂商 BSP | 目标硬件依赖尚未上游化的 ISP、VPU、显示或其他厂商组件 |

先收集运行版本和启动参数：

```sh
uname -a
cat /proc/version
cat /proc/cmdline
cat /proc/device-tree/model
```

## 检查设备树和绑定

`/proc/device-tree` 是运行时设备树的文件系统表示。使用 `dtc -I fs` 解码；传入已保存的 DTB 时使用 `-I dtb`。

```sh
dtc -I fs -O dts /proc/device-tree > running.dts
```

含有 C 头文件、标签和 overlay 的源码，应使用目标内核或 BSP 的 Kbuild 规则编译。用目标源码树验证 schema：

```sh
make O="$KOUT" ARCH="$ARCH" CROSS_COMPILE="$CROSS_COMPILE" dtbs_check
```

检查供应商树自身的 schema 版本；对于绑定修改再运行 `dt_binding_check`。参考 [Devicetree schema 文档](https://docs.kernel.org/devicetree/bindings/writing-schema.html) 和 [上游 dtc 手册](https://git.kernel.org/pub/scm/utils/dtc/dtc.git/tree/Documentation/manual.txt)。

## 构建路由

- Buildroot：以输出目录中的 `.config` 和 package 配置为准；使用该树提供的目标，例如 `make linux-rebuild`。
- Yocto：检查 layer 和 `PREFERRED_PROVIDER_virtual/kernel` 等实际配置；构建已选择的 `virtual/kernel` 或完整 image。
- 独立 Kbuild：选对 `ARCH` 和目标 ABI 编译器；保持 kernel config、头文件、符号版本和模块来自同一次目标构建。详细外部模块规则见 [Kbuild external modules](https://docs.kernel.org/kbuild/modules.html)。

`arm-linux-gnueabihf-` 仅用于 32-bit ARM hard-float。AArch64 通常需要 AArch64 工具链（如 `aarch64-linux-gnu-`）；以目标 SDK 和内核构建记录为准。

## systemd

```sh
systemd-analyze verify /etc/systemd/system/myapp.service
systemctl --failed
journalctl -b -p err
```

`After=` 只指定启动顺序；需要拉起依赖单元时另设 `Wants=` 或 `Requires=`。定位失败时保留启动时间、单元状态和完整相关日志。
