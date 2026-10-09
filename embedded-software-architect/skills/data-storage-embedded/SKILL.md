---
name: data-storage-embedded
description: |
  Embedded data persistence: SQLite (WAL/durability), Redis (in-memory caveats), atomic write + fsync, flash media lifetime monitoring.
  TRIGGER when: SQLite、sqlite3、数据库、db、journal_mode、WAL、Redis、redis、缓存、持久化、掉电、断电、数据丢失、写盘、原子写、fsync、eMMC、life_time、SD 卡、存储寿命、数据损坏、integrity_check、存不下、写满了、空间不够、数据丢了、记录没了、存了没起来、数据库挂了、数据损坏、存不进、存了没保住、断电丢数据、写盘失败、查询慢、数据库卡、存储写满了、盘写满了、磁盘满了、硬盘满了、空间写满了、数据写不进去、存了没保住、数据库写满了、db满了、写不进盘,
  DO NOT TRIGGER when: PCIe/SATA/RAID 硬件存储管理（用 storage-hardware-io）,
---

# data-storage-embedded

> 嵌入式数据存储：SQLite、Redis、文件存储、掉电一致性、长跑数据完整性。平台无关。

## 适用范围

嵌入式设备上的本地数据持久化：配置存储、时序数据、缓存、掉电保护。

---

## 存储选型

| 方案 | 适用 | 限制 |
|---|---|---|
| **文件 + 原子写** | 少量配置（几个 KB） | 无查询能力 |
| **SQLite** | 关系型数据、需要查询 | 单写者、写放大 |
| **Redis** | 高频读写、缓存、计数 | **内存态，重启即丢**，需持久化 |
| **自研二进制** | 大量时序数据、追求性能 | 需自己保证一致性 |

**关键**：Redis **不是**数据库，它在内存里。嵌入式默认 0 swap 的情况下，把大量数据放 Redis 会直接 OOM。

---

## SQLite

### 嵌入式配置

```bash
sqlite3 /data/config.db
PRAGMA journal_mode=WAL;      # 关键：WAL 模式提升并发与持久性
PRAGMA synchronous=NORMAL;   # FULL 更安全但慢，NORMAL 是平衡点
```

```sql
PRAGMA journal_mode;      -- 确认当前模式
PRAGMA integrity_check;   -- 校验完整性
VACUUM;                   -- 回收空间
```

### 关键要点

- **WAL 模式**：默认 rollback journal 写放大严重，WAL 更适合嵌入式并发读
- **WAL 需要共享内存**：`-shm` 文件，放到**非 tmpfs**否则掉电易损
- **`synchronous`**：NORMAL 在断电时可能丢最后几个事务，FULL 更安全
- **不适合大量写入**：SQLite 是单写模型，高频写要攒批

### 嵌入式部署注意

- 数据库文件放**持久化分区**，不要放 tmpfs（掉电丢失）
- `ulimit -n` 限制：每个连接占 fd，长连接多时注意
- 定期 `VACUUM` 和 `integrity_check`（尤其异常掉电后）

---

## Redis

### 嵌入式注意

- **默认无持久化**，重启数据全丢 → 必须配RDB/AOF
- **内存占用**：需设 `maxmemory` + `maxmemory-policy`，否则会撑爆设备内存
- **不适用大数据集**：嵌入式通常只有几百 MB 内存

```bash
redis-cli INFO memory | grep used_memory_human
redis-cli CONFIG GET maxmemory
redis-cli CONFIG GET appendonly
```

### 部署

```bash
redis-server /etc/redis.conf
```

```conf
maxmemory 128mb
maxmemory-policy allkeys-lru
appendonly yes
```

---

## 掉电一致性

**嵌入式设备最常见的数据丢失场景是意外掉电**，不是软件崩溃。

### 保护措施

| 措施 | 说明 |
|---|---|
| **原子写** | 写临时文件 → fsync → rename |
| **fsync** | 数据落盘，不依赖 page cache |
| **WAL + FULL** | 数据库层保证 |
| **掉电检测** | 备电电容 ADC 采样 / GPIO 中断 |

```c
// 原子写：写临时文件 → fsync → rename
int fd = open(tmpfile, O_WRONLY|O_CREAT|O_TRUNC, 0644);
write(fd, data, len);
fsync(fd);        // 关键：确保落盘
close(fd);
rename(tmpfile, target);   // 原子替换
fsync(dirfd);              // 确保目录项也落盘
```

**要点**：`rename` 是原子的，但**必须 fsync 目录**，否则断电后仍可能丢。

---

## 长跑数据完整性

长跑服务的数据校验：

```bash
# 文件系统层面
dmesg | grep -i "ext4\|error\|remount"   # 检查文件系统错误

# 存储介质健康（eMMC/SSD）
cat /sys/block/mmcblk0/device/life_time
mmc extcsd read /dev/mmcblk0 | grep -i lifetime
smartctl -a /dev/sda          # SATA/USB 存储
```

**关键**：eMMC 有**寿命**指标，`life_time` 接近 `0x0b` 意味着接近寿命末期，可能随时坏块。这会导致随机数据损坏，必须监控。

---

## 边界与注意

- **Redis 是内存态**，当数据库用会在掉电时全丢，且吃光内存
- SQLite 大量写入要攒批，不要每条都写
- 关键数据必须 fsync，不要只 write
- 0 swap 设备上给 Redis 设maxmemory 上限，否则可能触发 OOM 连锁
- 长时间运行前检查存储介质寿命（eMMC life_time / SMART）
- 数据库文件放持久化分区，异常掉电后先 `integrity_check`