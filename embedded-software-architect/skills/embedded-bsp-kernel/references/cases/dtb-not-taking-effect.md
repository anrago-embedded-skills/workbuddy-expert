# 案例：DTS 改了但 runtime 节点未改变

> **合成教学夹具**：以下请求、路径、输出和设备树片段都是构造的练习材料，不是现场记录，不代表任何板卡构建或启动成功。

## 输入

用户报告：sensor 节点已加到 `board-rev-b.dts`，构建目录产生了 `sensor.dtb`，但目标机 `/sys/bus/i2c/devices/` 看不到该传感器。练习夹具给出：

```text
[SYNTHETIC HOST build note] make dtbs completed; output: out/arch/arm64/boot/dts/vendor/board-rev-b.dtb
[SYNTHETIC TARGET observation] /proc/device-tree/model -> "Example Board Rev B"
[SYNTHETIC TARGET observation] runtime tree has /soc/i2c@12340000 but no /sensor@36 child
[SYNTHETIC U-BOOT note] printenv bootcmd fdtfile -> bootcmd selects fit.itb; fdtfile is unset
```

代码和路由值均为教学 placeholder：

```dts
/* [SYNTHETIC FRAGMENT] 不可直接套用到真实板卡。 */
&i2c2 {
    status = "okay";
    sensor@36 {
        compatible = "example,sensor";
        reg = <0x36>;
        status = "okay";
    };
};
```

## 竞争假设与区分证据

| 假设 | 需要收集的最小证据 | 可支持/排除什么 |
|---|---|---|
| 构建了 DTB，但镜像打包没有选它 | SDK 的最终 image/fit 构建输入与 manifest、产物哈希、启动日志中的选中配置 | 单独出现 `out/.../board-rev-b.dtb` 不能证明被打包或启动 |
| bootloader 选择了另一个 kernel/DTB/overlay/slot | 目标串口启动日志、实际启动脚本/环境和启动包清单；U-Boot 中对已确认 FDT 地址查看节点 | 若 bootloader 端无可确认地址，不猜 `fdt_addr_r`，改从 SDK 文档查交接方式 |
| 目标加载了预期 DTB，但节点在 DTS include/overlay 中未启用或被覆盖 | 构建输入展开结果与目标 `dtc -I fs -O dts /proc/device-tree` 的节点/属性比较 | 分清预处理/overlay 问题与选错镜像 |
| sensor 节点存在但其 bus/驱动没有枚举 | runtime tree 节点实际路径、父 I2C 控制器运行状态、`/sys/bus/i2c/devices/` 和匹配日志 | 如果节点不存在，先不要修改驱动 compatible |

## 最小修复边界

先按证据修改打包选择、启动配置或 DTS 中真正不符的节点。如果目标 runtime tree 缺节点但源 DTS 与绑定均正确，最小改动可能只是修复 SDK recipe/FIT/overlay 清单中使用的输入文件；若运行时节点确实因 `status` 禁用且其他资源描述均正确，才按 binding 与板级资料启用节点：

```diff
/* [SYNTHETIC FRAGMENT] 仅当运行时选中的节点被错误禁用时考虑此属性。 */
- status = "disabled";
+ status = "okay";
```

不因设备缺失而盲目改地址、GPIO、overlay 顺序或 `fdt_addr_r`。设备树修复之外若已进入目标启动步骤，先记录原始启动项、原产物和可验证恢复路径。

## 预期证据与回归

修复后的预期证据（不是本案例已观察到的结果）：目标 SDK 构建及 `dtbs_check` 对应同一 DTS 输入；打包清单指向预期 DTB/overlay；目标 runtime tree 显示目标节点及属性；设备在父总线注册后出现；之后再独立确认 driver match/probe。

回归包括干净重建、产物哈希与 manifest 对照、启动所选镜像/overlay 对照、runtime tree 节点/属性检查、传感器出现与 driver probe 检查，以及从原启动项恢复的演练。如果没有实际 SDK、bootloader 或板卡，只能交付静态/构建证据，并将后续项标记为未验证。上游依据：[DeviceTree 使用模型](https://docs.kernel.org/devicetree/usage-model.html)、[DeviceTree schema 编写与检查](https://docs.kernel.org/devicetree/bindings/writing-schema.html)、[U-Boot environment 变量](https://docs.u-boot.org/en/latest/usage/environment.html)。
