# 排障流程速查表

> 分层定位的快速执行清单。详细方法论见主 SKILL.md。

## 分层定位顺序（从上往下，逐层排除）

| 层 | 排查手段 | 关键判断 |
|---|---|---|
| **应用层** | 日志、`strace`、`gdb` | 业务逻辑/参数/时序 |
| **系统层** | `systemctl`、`journalctl`、资源占用 | 服务/权限/配置 |
| **驱动层** | `dmesg`、`/sys/class/video4linux`、`media-ctl -p` | 驱动绑定/ioctl |
| **硬件层** | 万用表/寄存器/手册 | 供电/信号 |

**铁律**：上层没排除，不要动下层。

## 排障五步

1. **澄清现状** — 板型、固件、现象、频率、最近有无变更
2. **抓现场** — 复现时的 `dmesg` / `journalctl`（不要事后回忆）
3. **立假设 + 验证** — **一次一个假设**，被推翻就换
4. **修复 + 回归** — 板上验证目标功能 + 查日志无新增 error
5. **长跑验证** — 短时间正常不代表稳定

## 「没反应」类问题先查这三条

```bash
cat /proc/<pid>/status | grep -E "^State|^TracerPid"
ps -ef | grep defunct
cat /proc/<pid>/wchan
```

| 状态 | 含义 |
|---|---|
| `TracerPid` 非 0 | 被 ptrace 冻结 |
| `State: T` | 被信号暂停 |
| `State: Z` | 僵尸，父进程未回收 |

**不要一上来就重启服务**——会毁掉现场。

## 部署验证

```bash
scp myapp root@<board>:/usr/bin/
ssh root@<board> "systemctl restart myapp"
ssh root@<board> "myapp --version"   # 确认版本真的更新了
```

## 长跑采样

```bash
while true; do
  echo "$(date) rss=$(ps -o rss= -p <pid>) cpu=$(top -bn1 -p <pid> | tail -1 | awk '{print $9}') temp=$(cat /sys/class/thermal/thermal_zone0/temp)"
  sleep 300
done | tee /tmp/longrun.log
```

## 常见误判

| 现象 | 容易误判为 | 实际可能是 |
|---|---|---|
| 跑久了变慢 | 内存泄漏 | **过热降频** |
| 进程在但无响应 | 死锁 | 被 ptrace 冻结 |
| 偶发失败 | 代码 bug | 网络抖动/超时设置过短 |
| 编译正常但板上不行 | — | 交叉编译环境/字节序/对齐 |

## 边界

- 一次只改一个变量，否则无法归因
- 长跑才算数
- 修复后必须回归
- 实测数据用具体数字