---
name: data-storage-embedded
description: |
  嵌入式设备本地数据的归属、持久性、一致性与容量问题，包括 SQLite/WAL、Redis 恢复策略、持久文件写入，以及数据增长或空间耗尽分析。
---

# data-storage-embedded

> 嵌入式数据存储：SQLite、Redis、文件存储、掉电一致性、长跑数据完整性。平台无关。

## 适用范围

嵌入式设备上的本地数据持久化：配置存储、时序数据、缓存、掉电保护。

## 主技能与辅助读取

- **主技能**：判断数据由谁拥有、如何落盘和恢复；分析 SQLite/WAL、Redis、持久文件的一致性，以及数据增长、空间耗尽或写入失败。
- **辅助读取**：只有在日志或设备状态显示块设备 I/O、文件系统或介质健康问题时，才读取 [`storage-hardware-io`](../storage-hardware-io/SKILL.md) 协查底层存储故障。

## 平台参考入口

- [通用 Linux 数据存储](references/generic-linux.md)：需要核对 Linux 文件系统、挂载、临时与持久分区或介质健康做法时读取。
- [RK3588 数据存储](references/rockchip-rk3588.md)：目标板确认是 RK3588，且需要核对板级介质或具体 BSP 部署时读取。

## 任务输入、证据分支与交付

先记录数据所有者、文件/数据库路径与挂载来源、进程/SQLite/Redis 版本、journal mode/synchronous 或 Redis RDB/AOF 配置、写入/提交/确认顺序、复位类型（进程退出、内核崩溃、掉电）、磁盘余量和原始错误。恢复期间不得删改数据库、WAL/SHM、journal 或唯一副本；先复制到安全位置并记录文件清单与哈希，避免破坏恢复证据。

| 证据 | 主查分支 |
|---|---|
| SQLite WAL 增长、已确认事务重启后缺失或完整性告警 | 核对打开期间的 `.db`/`-wal`/`-shm` 生命周期、checkpoint、实际连接的 `journal_mode`/`synchronous`、事务提交与存储同步错误；不要从 `integrity_check=ok` 推断已达到掉电耐久性 |
| 配置文件缺失/旧值/截断 | 沿临时文件写入、短写/EINTR、`fsync(file)`、rename 和 `fsync(parent directory)` 顺序逐返回值查；再确认文件系统/设备是否兑现同步 |
| Redis 重启后数据集差异 | 检查实际 RDB/AOF 配置、持久化事件与同步策略、重启日志和恢复文件；不要假设持久化默认开启 |
| ENOSPC、EIO、只读重挂或寿命指标变化 | 确认挂载、文件系统、介质健康与容量；若根因落在块层，辅助读取 [storage-hardware-io](../storage-hardware-io/SKILL.md) |

交付故障时间线、哪些写入得到成功确认、数据库/文件恢复结果、最小写入路径或配置修复范围，以及重复崩溃/重启后的逻辑不变量和完整性验收。软件强杀不能替代掉电测试；主机 fixture、目标 Linux 和实机掉电证据分开陈述。跨领域方法见 [工程工作流](../embedded-debug-workflow/references/engineering-workflow.md) 与 [验证策略](../embedded-debug-workflow/references/validation-policy.md)，需要故障注入边界时读取 [持久化恢复案例](references/persistence-recovery-case.md)。

## 命令环境与副作用

下面的 `sqlite3`、`redis-cli`、`dmesg`、介质状态路径均以 **TARGET Linux** 为前提；先确认数据目录、运行实例、权限和工具版本。`PRAGMA journal_mode=WAL` 会改数据库 journal 模式，`synchronous` 影响连接写入保证；`VACUUM` 重写数据库；`smartctl -t` 启动设备自测；`redis-server` 会启动服务。它们不是只读诊断。所有 `<...>` 参数都是必须先替换的模板。

---

## 存储选型

| 方案 | 适用 | 限制 |
|---|---|---|
| **文件 + 原子写** | 少量配置（几个 KB） | 无查询能力 |
| **SQLite** | 关系型数据、需要查询 | 单写者、写放大 |
| **Redis** | 高频读写、缓存、计数 | 工作数据集驻留内存；RDB/AOF 持久化按部署配置选择 |
| **自研二进制** | 大量时序数据、追求性能 | 需自己保证一致性 |

**关键**：Redis 是内存数据库，支持可配置的 RDB 快照和 AOF 持久化；重启后的数据恢复取决于实际配置、存储和同步策略。检查设备实际内存、cgroup 限额和 Redis 持久化配置后再评估数据集容量；不要从“嵌入式”推断 swap 状态或 OOM 结论。

---

## SQLite

### 嵌入式配置

```bash
# TARGET / database configuration change. Test on a copy or scheduled maintenance window.
# Confirm the database path and active connections; journal mode is persistent database state.
sqlite3 /data/config.db <<'SQL'
PRAGMA journal_mode=WAL;
-- In WAL mode select FULL/NORMAL from required durability and the matched SQLite docs.
-- synchronous applies to this connection; configure every relevant connection.
PRAGMA synchronous=FULL;
SQL
```

预期第一条返回 `wal` 表示 journal mode 已切换/确认；数据库忙、设置失败或返回其他模式表示未按预期生效。先核对实例、VFS、锁和版本，不重复改生产库。

```sql
-- Read-only SQL on a confirmed copy or approved diagnostic window.
PRAGMA journal_mode;
PRAGMA integrity_check;
```

预期 `integrity_check` 成功返回 `ok`；其他输出需保留完整结果并停止清理 sidecar。该检查验证结构，不证明最近事务已耐久到介质，也不修复数据库。

`VACUUM` 是维护写操作，可能需要额外可用空间并重写数据库文件；仅在确认空间、备份、活动连接和维护窗口后执行，并比较前后逻辑数据与数据库状态。

### 关键要点

- **WAL 模式**：读者可与单个 writer 并发；checkpoint 负责把 WAL 内容写回主数据库
- **`-shm` 与 `-wal` 不同**：`-shm` 保存可重建的 wal-index，不是持久数据；`-wal` 可能包含尚未 checkpoint 的已提交事务，数据库打开期间或异常退出后应与数据库文件一并保留。不要在连接打开时手动删除 sidecar
- **`synchronous`**：WAL 模式下，`FULL` 在每个事务提交后同步 WAL；`NORMAL` 在多数事务提交时不做同步，系统崩溃或断电可能丢失最近提交，但数据库仍保持一致。实际耐久性还取决于 VFS、文件系统和存储设备是否兑现同步请求
- **不适合大量写入**：SQLite 是单写模型，高频写要攒批

### 嵌入式部署注意

- 数据库文件放**持久化分区**，不要放 tmpfs（掉电丢失）
- `ulimit -n` 限制：每个连接占 fd，长连接多时注意
- 定期 `VACUUM` 和 `integrity_check`（尤其异常掉电后）

---

## Redis

### 嵌入式注意

- **持久化依配置而定**：检查实际 RDB `save` 与 AOF `appendonly` 设置和 `INFO persistence`，不要从 Redis 名称或版本推断重启行为
- **内存占用**：需设 `maxmemory` + `maxmemory-policy`，否则会撑爆设备内存
- **不适用大数据集**：嵌入式通常只有几百 MB 内存

```bash
# TARGET / read-only queries against the intended Redis instance.
redis-cli INFO memory | grep used_memory_human
redis-cli CONFIG GET maxmemory
redis-cli CONFIG GET appendonly
redis-cli CONFIG GET save
redis-cli INFO persistence
```

### 部署

```bash
# TARGET / starts the configured server; use the service manager if one owns this instance.
redis-server /etc/redis.conf
```

```conf
# redis.conf template only; size and eviction semantics come from measured workload.
maxmemory <measured-budget>
maxmemory-policy <policy-matched-to-data-loss-requirements>
appendonly yes
```

The policy above changes runtime data retention; `allkeys-*` policies may evict keys, while `noeviction` may reject writes at the limit. Validate the chosen Redis version and persistence configuration in a test instance before deployment.

---

## 掉电一致性

软件崩溃、内核崩溃、重启和实际掉电触发的缓存/文件系统路径不同；记录本次复位类型，不能用进程强杀代替掉电耐久性验证。

### 保护措施

| 措施 | 说明 |
|---|---|
| **原子写** | 同目录写临时文件 → `fsync(file)` → `rename`；Linux 掉电后仍需 `fsync(parent directory)` 才能保证目录项持久化 |
| **fsync** | 数据落盘，不依赖 page cache |
| **WAL + FULL** | SQLite 要求 WAL 同步；底层 VFS、文件系统与介质仍须兑现同步请求 |
| **掉电检测** | 备电电容 ADC 采样 / GPIO 中断 |

```c
// Linux C fragment, not a complete function. tmp_name/target_name share parent.
// write_all() must handle short writes and EINTR; check each syscall result.
// Preserve the old target if writing or syncing the temp file fails.
int dirfd = open(parent, O_RDONLY | O_DIRECTORY | O_CLOEXEC);
if (dirfd < 0) goto report_open_error;
int fd = openat(dirfd, tmp_name, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0644);
if (fd < 0) goto close_dir_and_report;
if (write_all(fd, data, len) < 0) goto close_temp_and_report;
if (fsync(fd) < 0) goto close_temp_and_report;
if (close(fd) < 0) goto report_close_error;
if (renameat(dirfd, tmp_name, dirfd, target_name) < 0) goto report_rename_error;
if (fsync(dirfd) < 0) goto report_directory_durability_unknown;
close(dirfd);
```

**要点**：同目录 `rename` 提供原子替换语义；若 Linux 掉电耐久性是要求，先同步文件，再在 rename 后同步父目录。该 C 片段显示错误分支（标签逻辑省略），不是完整函数；生产实现需关闭有效描述符、清理仅由本次创建的临时文件并保留原始 errno。

---

## 长跑数据完整性

长跑服务的数据校验：

```bash
# TARGET / read-only if permitted; dmesg access depends on kernel policy.
dmesg | grep -i "ext4\|error\|remount"   # 检查文件系统错误

# Read-only device-health queries. Confirm device type/name; tools and sysfs attributes vary.
cat /sys/block/mmcblk0/device/life_time   # only if this target exposes this attribute
mmc extcsd read /dev/mmcblk0              # inspect the life-time fields in full output
smartctl -a /dev/sda          # SATA/USB 存储
```

Expected kernel/filesystem messages identify errors or remounts; absence of messages is only evidence for the sampled ring buffer/window. eMMC life-time estimates are coarse device-reported categories, not a remaining-time prediction or proof of imminent bad blocks. Interpret their exact coding from the eMMC specification/device datasheet and correlate with I/O errors. Missing attributes/tools mean that interface is unavailable, not that the device is healthy.

---

## 边界与注意

- Redis 的工作数据集驻留内存，持久化和恢复取决于部署配置；结合实测工作集、内存限额与持久化策略评估容量
- SQLite 大量写入要攒批，不要每条都写
- 关键数据必须 fsync，不要只 write
- 使用 `maxmemory` 和合适的 eviction policy 控制 Redis 自身占用；评估 RDB/AOF 后台工作造成的额外内存需求，并用运行时内存/cgroup 数据判断 OOM 风险

## 主要参考

- SQLite Write-Ahead Logging, including the WAL file and wal-index: https://www.sqlite.org/wal.html
- SQLite `PRAGMA synchronous` durability behavior: https://www.sqlite.org/pragma.html#pragma_synchronous
- SQLite crash/recovery assumptions and limits: https://www.sqlite.org/atomiccommit.html
- Redis FAQ, in-memory data and persistence model: https://redis.io/docs/latest/develop/get-started/faq/
- Linux `fsync(2)`, including directory synchronization: https://man7.org/linux/man-pages/man2/fsync.2.html
- Linux `rename(2)`: https://man7.org/linux/man-pages/man2/rename.2.html
- Linux `write(2)` partial writes and errors: https://man7.org/linux/man-pages/man2/write.2.html
- Linux kernel MMC tools overview, including EXT_CSD inspection: https://docs.kernel.org/driver-api/mmc/mmc-tools.html
- 长时间运行前检查存储介质寿命（eMMC life_time / SMART）
- 数据库文件放持久化分区，异常掉电后先 `integrity_check`
