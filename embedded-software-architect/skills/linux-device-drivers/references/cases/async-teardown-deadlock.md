# 案例：解绑时同步取消 work 导致死锁

> **合成教学夹具**：触发步骤、等待关系和日志为合成练习材料，不是现场历史或真实板卡测量。

## 输入

```text
[SYNTHETIC TEST] userspace requests driver unbind while device I/O is active
[SYNTHETIC TARGET task trace] remove path waits in cancel_work_sync(); worker waits for ctx->lock
[SYNTHETIC CODE REVIEW] remove holds ctx->lock across cancel_work_sync(); worker acquires ctx->lock before completing
```

## 竞争假设与区分证据

| 假设 | 区分证据 | 结果含义 |
|---|---|---|
| remove 持有 worker 需要的锁并等待 worker | blocked stack、lockdep/锁状态（若有）和 remove/worker 两条调用路径的同一把锁 | 形成直接等待环：remove 等 worker，worker 等锁 |
| IRQ/timer/producer 在 cancel 后重新排队 | 搜索所有 `queue_work`/`mod_delayed_work`/timer 重启路径；记录 stop 状态是否与 enqueue 同步 | 仅一次 cancel 不能保证之后不再排队 |
| 硬件仍在 DMA 或 IRQ 活动 | 设备状态、IRQ 计数/回调、完成队列和硬件停止确认 | 不能提前释放资源；等待时可能依赖仍需运行的 completion producer |
| 锁之外还有打开的用户 fd 或 subsystem callback | open/release 计数、调用栈、已注册接口的回调引用 | unregister 阻止新入口不等于旧调用已退出 |

## 修复边界

按真实硬件依赖制定 teardown 顺序：置 `stopping` 并让所有生产者拒绝新工作；阻止/停止会重排 work 的 IRQ、timer 或设备事件（若 DMA completion 需要 IRQ，则先保留完成 IRQ）；让硬件静止；在不持有 worker 所需锁时同步 IRQ/work/timer/kthread；最后释放回调使用的状态和 DMA buffer。每个步骤都要考虑取消和并发 enqueue 是否有同步关系。

以下伪代码是**非编译片段**，只演示释放锁后再等待 work；硬件停止与 IRQ 顺序必须由目标设备协议确定：

```c
/* [SYNTHETIC PSEUDOCODE] 非完整驱动，不能直接编译或照抄。 */
mutex_lock(&ctx->lock);
ctx->stopping = true;   /* queue 路径也必须检查同一状态并同步它 */
mutex_unlock(&ctx->lock);

/* 按硬件协议禁止新请求/重新排队；不要在此假定具体寄存器操作。 */
stop_and_quiesce_device(ctx);
cancel_work_sync(&ctx->work); /* 必须在 worker 需要的锁之外等待 */
```

若 worker 依赖中断确认 DMA 结束，应调整 `stop_and_quiesce_device()` 的顺序，使 completion 中断先能完成，再同步退出 IRQ。不能只增加 timeout 后释放仍被访问的状态；这会把死锁改成 use-after-free。

## 预期证据与回归

预期：锁顺序图中无环；停止状态一旦可见，所有 queue 路径不再生成工作；remove 等待期间需要的完成事件仍可到达；硬件静止和所有异步访问退出后才释放资源。未提供目标驱动与硬件协议时这些仅是检查标准。

回归在目标系统上覆盖 work pending、worker 执行中、IRQ 与完成同时发生、重复 unbind/bind、错误恢复和已打开 fd 跨越 remove。启用 lockdep/tracepoint 等需目标配置支持。本案例未提供目标驱动或内核树，未进行目标构建或板卡测试；实际 teardown 顺序须按目标硬件协议验证。依据：[workqueue 同步取消保证与并发 enqueue 限制](https://docs.kernel.org/core-api/workqueue.html)、[driver remove 生命周期](https://docs.kernel.org/driver-api/driver-model/driver.html)。
