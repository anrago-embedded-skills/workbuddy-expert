# SQLite 与文件持久化恢复：教学案例

> **合成教学输入**：本页两组夹具用于练习取证和验收，不是板卡历史、生产事故报告或实测结果。它们只提出待区分的假设。

## 案例 A：SQLite WAL 中已确认事务在断电后不可见

### 教学输入

一个 WAL 数据库在模拟重启后缺少最近一笔应用曾报告成功的更新；复开副本后 `PRAGMA integrity_check` 返回 `ok`。夹具同时提供配置快照：连接使用 WAL，`synchronous=NORMAL`。没有真实硬件掉电记录，也没有事务提交调用的返回日志。

### 候选与区分证据

| 候选 | 应收集的证据 | 如何区分 |
|---|---|---|
| 事务未真正 COMMIT 或应用过早确认 | 事务边界、COMMIT 返回码和应用 ACK 顺序 | 若没有成功 COMMIT 返回，缺少事务可能是应用确认逻辑；不能先归因到存储 |
| `NORMAL` 下崩溃/掉电丢失最近已确认事务 | 实际运行连接的 `journal_mode` 与 `synchronous`、目标 SQLite/VFS 版本、COMMIT 返回和复位类型 | WAL + `NORMAL` 允许最近提交在系统崩溃/断电后回滚而保持数据库一致；与“完整性检查成功”并不冲突 |
| 在线复制时遗漏 `-wal`，或恢复前手动删改 sidecar | 文件清单、复制方式/时间、数据库是否打开、SQLite 日志 | WAL 可能包含尚未 checkpoint 的已提交事务；只复制主库可能形成旧快照。`-shm` 保存可重建 wal-index，不能把它当作提交数据 |
| 数据库路径、挂载或 VFS 与预期不同 | 进程打开文件路径、挂载信息、链接/符号链接和启动配置 | 确认被检查的是实际在线数据库及其 sidecar，而不是另一份文件 |
| 同步调用或硬件/文件系统未兑现持久化请求 | SQLite/VFS 错误日志、目标文件系统/介质资料、同步调用返回与可控故障注入 | `FULL` 仍通过目标 VFS、文件系统和设备实现；软件配置不能单独证明存储器正确完成 flush |

恢复前只在安全副本上检查；不要删除、分离、移动或手工拼接仍在使用的 `.db`、`-wal` 或 `-shm`。需要一致副本时使用 SQLite Online Backup API，或在受控关闭/检查点后复制。SQLite 文档说明 WAL、checkpoint、wal-index 与 `FULL`/`NORMAL` 的行为，见 [WAL](https://www.sqlite.org/wal.html) 和 [`PRAGMA synchronous`](https://www.sqlite.org/pragma.html#pragma_synchronous)。

### 最小变更边界与接受标准

如果证据确认只因最近提交在掉电后可回滚，才在每个相关连接设置满足损失要求的同步等级；不要只对一个临时 sqlite3 shell 改连接设置。若是 sidecar 复制/清理错误，修复复制/备份生命周期；若是应用确认顺序错误，修复提交返回值处理。

在匹配的 SQLite/VFS 主机夹具或目标软件环境中，于事务提交前后多个注入点重复模拟崩溃并重新打开数据库。若应用声称一次写入已确认，则按产品耐久性要求验证该事务和后续事务；所有记录需满足应用逻辑不变量，数据库结构检查通过，且恢复前后副本/sidecar 生命周期可解释。SQLite 的 `integrity_check=ok` 只说明结构检查通过，不证明最近提交已经到达非易失介质。主机 VFS 模拟也不能证明目标硬件的缓存 flush 行为；物理掉电验证单独记录。

## 案例 B：原子替换文件在重启后是旧版本或缺失

### 教学输入

一个配置保存函数写同目录临时文件后调用 `fsync(temp_fd)` 和 `rename()`；重启后配置仍是旧值，或新文件名不在目录中。夹具未提供每个系统调用返回码、复位类型或文件系统/设备资料。

### 候选与区分证据

| 候选 | 应收集的证据 | 如何区分 |
|---|---|---|
| 部分写/`EINTR` 未循环处理 | 写入返回字节数、errno、调用顺序和临时文件长度 | 小于请求长度时仍继续同步/rename，会替换为不完整文件 |
| `fsync(file)`、`close` 或 `rename` 失败被忽略 | 所有系统调用返回值及 errno，失败路径日志 | 返回错误时不得向上层报告新配置已经耐久；rename 成功与否也需分别记录 |
| rename 后未同步父目录 | `renameat` 与目录 `fsync` 顺序、错误日志、文件系统语义 | 文件内容可能已同步但目录项掉电耐久性未确认；`fsync(file)` 本身不一定同步其目录项 |
| 文件系统、VFS 或设备没有兑现同步要求 | 实际挂载/驱动/设备文档与受控掉电注入结果 | POSIX/Linux API 调用成功只能作为软件层证据；底层设备仍可能错误报告 flush 完成 |

### 最小变更边界与接受标准

先完善当前写入路径：同一目录创建唯一临时文件，循环处理短写与 `EINTR`，每步检查结果，成功写完后 `fsync(temp_fd)`，检查 close，再同目录 rename，最后 `fsync(parent_dir_fd)`。失败时保留原配置、不宣称成功；只清理本次创建的临时文件。Linux [`fsync(2)`](https://man7.org/linux/man-pages/man2/fsync.2.html) 指出同步文件不一定同步所在目录；[`rename(2)`](https://man7.org/linux/man-pages/man2/rename.2.html) 说明同目录替换的原子可见性语义。最终耐久性仍依赖具体文件系统和设备。

在临时目录/文件系统 fixture 中注入每一个错误返回和短写，并在每个提交阶段执行进程崩溃模拟。每次重启后目标必须是旧的完整配置或新的完整配置，不能是部分内容；成功确认的写入须符合定义的耐久性规则，错误写入不得报告成功。重复故障/恢复循环后检查文件长度、校验和和逻辑字段。强杀进程不是掉电模拟；软件夹具通过后，如产品要求断电耐久性，再于受控目标环境单独验证。

## 主要参考

- SQLite [WAL](https://www.sqlite.org/wal.html), [`PRAGMA synchronous`](https://www.sqlite.org/pragma.html#pragma_synchronous), and [atomic commit assumptions/limits](https://www.sqlite.org/atomiccommit.html)
- Linux [`fsync(2)`](https://man7.org/linux/man-pages/man2/fsync.2.html), [`rename(2)`](https://man7.org/linux/man-pages/man2/rename.2.html), and [`write(2)`](https://man7.org/linux/man-pages/man2/write.2.html)
