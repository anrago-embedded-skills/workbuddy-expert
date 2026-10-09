# 取证速查表

> 排障最常用的命令集合，按场景组织。详细方法论见主SKILL.md。

## 一次抓全现场（排障第一步）

```bash
# 系统与版本
uname -a
cat /etc/os-release
cat /proc/device-tree/model

# 内存
free -h
grep -E "MemAvailable|SwapTotal|CmaFree|Slab" /proc/meminfo

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

## fd / 句柄

```bash
ls /proc/<pid>/fd | wc -l                    # 当前 fd 数
cat /proc/<pid>/limits | grep -i "open files"   # 上限
ls -l /proc/<pid>/fd | awk '{print $NF}' | sed 's/[0-9]*$//' | sort | uniq -c  # 类型分布
```

## 网络

```bash
ss -s# 连接总览
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
cat /sys/block/mmcblk0/device/life_time  # eMMC 剩余寿命
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