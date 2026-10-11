# 内容与工程效果评测

这份矩阵评估技能是否帮助完成工程任务，补充 `expert-scenarios.md` 的路由/正文读取检查。下面的案例输入均为教学构造，不是生产日志或板上测试记录。

## 评测方法

1. 固定原始输入、模型/推理设置、工具和权限。对照组只提供原始问题与证据；技能组先使用实际 Agent 路由取得相应正文/条件参考，再处理同一输入。两组使用新上下文，不能相互看到答案或评分表。
2. 先记录评价标准，再读输出。保留实际读取记录、来源与执行环境，区分候选原因和已证实结论。只有实际执行的工具/构建/板测才能写通过。
3. 分别记录：关键证据是否齐全、候选原因与区分检查、最小完整修复、无效/错误动作、产物身份、验收与恢复方案。不要把多写了命令或引用了技能名称当作收益。
4. 对教学输入评估推理和计划；对工具使用确定性夹具测试；对真实 SDK/板卡另行构建和回归。少量离线观察不能统计为跨模型稳定性或实际宿主调用成功率。

## 内容矩阵

| 案例输入 | 参考 | 关键观察标准 | 真实目标验证状态 |
|---|---|---|---|
| 源码 DT 与运行树不同，启动选择旧 DTB | [DTB 未生效](../embedded-software-architect/skills/embedded-bsp-kernel/references/cases/dtb-not-taking-effect.md) | 先核对运行 DT/overlay/引导产物身份；分开考虑错误文件、bootloader 修改与配置；不盲改驱动 | 未进行目标构建/板测 |
| consumer 获取 regulator 返回 defer，provider 尚未就绪 | [probe defer](../embedded-software-architect/skills/linux-device-drivers/references/cases/probe-defer.md) | 核对错误、provider、资源映射与运行描述；不吞 errno、不写忙等重试；修改前确认硬件和目标 binding | 未进行目标构建/板测 |
| remove 持锁同步取消 work，work 也需要该锁并可能重新入队 | [异步卸载死锁](../embedded-software-architect/skills/linux-device-drivers/references/cases/async-teardown-deadlock.md) | 找出等待环、停止生产者和 requeue、在正确锁边界同步退出；保留硬件依赖及 fd 生命周期未知项 | 未进行目标构建/板测 |
| streaming DMA 映射保留多轮，CPU 与设备反复访问 | [DMA 所有权](../embedded-software-architect/skills/linux-device-drivers/references/cases/streaming-dma-ownership.md) | 区分 CPU/物理/DMA 地址，检查方向、完成/所有权、sync/unmap 生命周期；不直接宣布所有花屏都是缓存问题 | 未进行目标构建/板测 |
| memcg 限额、事件和 victim 日志吻合，宿主有余量、RSS增长 | [memcg OOM](../embedded-software-architect/skills/embedded-perf-debug/references/cases/memcg-oom.md) | 区分 OOM 范围与内存增长原因，核对有效层级和计费类别，不把 RSS 增长直接判为泄漏 | 未进行目标板故障/恢复验证 |
| 采集计数正常，后续编码或队列阶段丢帧 | [掉帧定位](../embedded-software-architect/skills/media-pipeline-linux/references/cases/frame-drop.md) | 同窗口逐阶段计数/时间戳和协商，识别最早差异，考虑背压/处理/负载；无计数语义就不比较数字 | 未进行目标管线/性能验证 |
| 连接断开、部分读写与重连后的重复/丢失消息 | [网络恢复](../embedded-software-architect/skills/embedded-networking/references/connection-recovery-case.md) | 区分传输与协议会话，处理 partial I/O、超时、退避、fd 退出与重复语义；用重复故障/恢复验收 | 未进行目标网络故障注入 |
| 掉电后 SQLite/WAL 或原子替换文件需恢复 | [持久化恢复](../embedded-software-architect/skills/data-storage-embedded/references/persistence-recovery-case.md) | 保留 sidecar/原文件，区分一致性与耐久性、文件与目录同步；恢复前不盲删文件或执行 VACUUM | 未进行目标介质掉电测试 |

## 结果记录

```text
输入身份/是否教学夹具：
模型、设置、工具与权限：
对照组/技能组、上下文隔离：
主技能、实际正文/参考来源（仅技能组）：
关键证据与缺失项：
候选原因、区分检查和预期分支：
错误/无效动作与影响：
最小变更、产物、验收与恢复：
实际执行及结果：
未执行条件、局限与后续验证：
```

本矩阵本身不是已通过的结果。仓库维护者将本次实际运行的工具测试和离线观察记录在实施计划中；WorkBuddy 原生加载、真实 SDK 构建及硬件行为分别保留未验证状态，直至有对应证据。
