# 取证速查表

> 排障最常用的命令集合，按场景组织。详细方法论见主SKILL.md。

## 一次抓全现场（排障第一步）

```bash
# 系统与版本
uname -a
cat /etc/os-release
cat /proc/device-tree/model

# 内存全局快照
free -h
grep -E "MemAvailable|SwapTotal|CmaFree|Slab" /proc/meminfo
cat /proc/buddyinfo
cat /proc/zoneinfo

# 进程 Top 10
ps -eo pid,rss,vsz,stat,comm --sort=-rss | head -11

# 磁盘
df -h

# 内核日志（最关键）
dmesg -T | tail -100

# 服务状态
systemctl --failed
journalctl -b -p err --no-pager | tail -30
```

RSS 增长或分配失败只是线索，不能直接作为根因结论。遇到 OOM 时，将完整内核事件与受影响进程的 cgroup 和内存计数器对照。对于 cgroup v2，从 `/proc/<pid>/cgroup` 解析对应路径，再检查该 cgroup 的 `memory.current`、`memory.max` 和 `memory.events`；对于 cgroup v1，检查目标系统挂载的 controller 文件。特定的高阶或 DMA/CMA 分配失败，应结合申请约束以及可用的 buddy/zone/CMA 证据判断。

## fd / 句柄

```bash
ls /proc/<pid>/fd | wc -l                    # 当前 fd 数
cat /proc/<pid>/limits | grep -i "open files"   # 上限
ls -l /proc/<pid>/fd | awk '{print $NF}' | sed 's/[0-9]*$//' | sort | uniq -c  # 类型分布
```

## 网络

```bash
ss -s # 连接总览
ss -tan | awk '{print $1}' | sort | uniq -c | sort -rn   # 按状态统计
ss -tan state time-wait | wc -l
ss -tan state close-wait | wc -l
ip -s link show eth0 | grep -iE "drop|error"
```

## 视频 / 媒体

```bash
media-ctl -p                          # 摄像头拓扑
v4l2-ctl -d /dev/video0 --all
v4l2-ctl -d /dev/video0 --list-formats-ext
v4l2-ctl -d /dev/video0 --get-fmt-video   # 确认实际生效格式
modetest -c -p                       # DRM 显示状态
cat /sys/kernel/debug/dri/0/state
```

## GPU / 渲染

```bash
cat /sys/class/devfreq/*.gpu/cur_freq    # GPU 频率（降频是性能问题常见原因）
eglinfo | grep -i renderer               # 确认是否软件渲染
echo $QT_QPA_PLATFORM
```

## 存储健康

```bash
cat /sys/block/mmcblk0/device/life_time  # eMMC 粗粒度寿命估计；接口/字段按目标驱动和器件手册核对
smartctl -a /dev/sda | grep -iE "health|life"
cat /proc/mdstat                         # RAID 状态
```

## 温度（性能问题易误判为泄漏）

```bash
cat /sys/class/thermal/thermal_zone*/temp
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq
```

## 长跑采样

```bash
while true; do
  echo "$(date) \
    rss=$(ps -o rss= -p <pid>) \
    fd=$(ls /proc/<pid>/fd 2>/dev/null | wc -l) \
    mem=$(free -m | awk '/Mem:/{print $3}') \
    temp=$(cat /sys/class/thermal/thermal_zone0/temp)"
  sleep 300
done | tee /tmp/longrun.log
```

## 边界

- 这些是**取证命令**，具体分析逻辑见主 SKILL.md
- 部分命令需 root 权限
- 抓现场要快，异常现场会被覆盖
- 单次 RSS、fd、CMA 或 `MemAvailable` 读数不能单独证明泄漏、OOM 范围或碎片化
- 长跑采样按复现窗口运行；按 Ctrl-C 停止并记录采样时长
