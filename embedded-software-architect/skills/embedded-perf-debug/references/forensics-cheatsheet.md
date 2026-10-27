# 取证速查表

> 仅在当前故障分支需要命令/字段速查时读取。除明确标为 HOST 的 Oops 导出和符号化外，代码块在受影响系统 **TARGET** 上运行。目标工具、选项、权限和内核字段随镜像变化；缺失或拒绝访问时记录具体 `unavailable` 原因，不把缺少数据当作零值或否定证据。
>
> 特定进程的 PID/TID 验证和 thermal/资源采样统一使用 [embedded-debug-workflow 的 process-sampling.md](../../embedded-debug-workflow/references/process-sampling.md)。先在同一个 TARGET shell 完成其验证段，再执行本页使用 `target_pid` 或 `target_proc` 的命令。

## 系统快照

```sh
# TARGET：基础身份和内存证据；/proc、设备树、dmesg 权限可能受限
uname -a
cat /etc/os-release
cat /proc/device-tree/model
free -h
grep -E 'MemAvailable|SwapTotal|CmaFree|Slab' /proc/meminfo
cat /proc/buddyinfo
cat /proc/zoneinfo

df -h
dmesg -T | tail -100
```

下面是可选服务管理器和进程工具；`journalctl` 只适用于使用 systemd 的目标，`systemctl` 和 `ps --sort` 也可能不存在或选项不同。先确认实际命令实现，读取失败时记录工具/权限错误。

```sh
# TARGET：systemd 日志和 procps 风格进程列表（均为可选）
systemctl --failed
journalctl -b -p err --no-pager | tail -30
ps -eo pid,ppid,user,vsz,rss,stat,comm --sort=-rss | head -30
```

这些快照只用于定位。RSS、`MemAvailable`、CMA、buddy order 或一次失败都不能单独证明泄漏、OOM 范围或碎片化。内存增长要识别类别和归属；高阶或 DMA/CMA 申请失败要结合真实申请约束、日志和适用的瞬时 zone/buddy/CMA 证据。

### OOM 与 cgroup

指定进程时先使用前述已验证变量：

```sh
# TARGET：按当前目标系统的 cgroup 版本和挂载布局继续检查
cat "${target_proc}/cgroup"
```

cgroup v2 要将 `/proc` 中的相对路径结合实际挂载映射解析到正确目录，再比较 `memory.current`、`memory.max`、`memory.events` 及有效祖先限制；cgroup v1 要找到已挂载的 memory controller 和相应限制/失败计数。不要根据目标系统未知的目录结构套用猜测路径。无法获得归属或映射时，不将 OOM 定性为全局还是 memcg。

`swapon --show` 或 `/proc/swaps` 显示当前 swap 状态。`SwapTotal: 0` 只表示当前未配置 swap，不证明全局内存耗尽，也不能单独解释某进程被杀。只有目标实际启用 zram 时才调查其影响。

## 指定进程内存、映射和 fd

先从目标现场确认 PID，并按本页开头的共享参考建立 `target_pid` 与 `target_proc`。`maps`、`limits`、fd 列表可能因权限、进程退出或目标内核限制不可读；记录失败来源。

```sh
# TARGET：已验证 target_proc/target_pid；pmap 是可选工具
cat "${target_proc}/maps"
if command -v pmap >/dev/null 2>&1; then pmap -x "$target_pid" | tail -30; else printf '%s\n' 'pmap unavailable'; fi

if [ -r "${target_proc}/fd" ] && fd_listing=$(ls "${target_proc}/fd" 2>/dev/null); then
  fd_count=$(printf '%s\n' "$fd_listing" | awk 'NF { count++ } END { print count+0 }')
else
  fd_count=unavailable
fi
unset fd_listing
printf 'fd_count=%s\n' "$fd_count"
grep -i 'open files' "${target_proc}/limits"
ls -l "${target_proc}/fd" | head -30
```

映射数量、fd 总数和单次 RSS 读数都是快照；要将增长与内核事件、cgroup 记账和同一工作负载时间窗对应。需要趋势时，使用共享有界 sampler；不要在未查明类别前宣布泄漏。

## 网络状态

```sh
# TARGET：需要 iproute2 的 ss/ip；选择实际链路并记录目标接口名
ss -s
ss -tan | awk 'NR > 1 { count[$1]++ } END { for (state in count) print state, count[state] }'
ss -tan state time-wait | wc -l
ss -tan state close-wait | wc -l
ip -s link show
```

`CLOSE_WAIT` 表示对端 FIN 已到且本端尚未关闭 socket；再查所属进程、socket 持续时间和清理路径。队列或接口统计异常需要按网络层证据继续，不由应用使用某个框架决定诊断归属。

## 视频、GPU 与显示

这些命令需要相应目标工具、设备节点、驱动/debugfs 和权限。先检查 TARGET 实际枚举出的设备/拓扑，再对目标真实节点运行；命令或数据源不可用时注明原因。

```sh
# TARGET：媒体工具可选；先用枚举结果确定拓扑和真实 video node
media-ctl -p
v4l2-ctl --list-devices
modetest -c -p
```

```sh
# TARGET：可选 GPU/Qt 信息；glob 匹配不到或接口不可读时记为 unavailable
for freq_file in /sys/class/devfreq/*.gpu/cur_freq; do
  [ -r "$freq_file" ] || continue
  printf '%s=' "$freq_file"
  cat "$freq_file"
done
command -v eglinfo >/dev/null 2>&1 && eglinfo | grep -i renderer
printf 'QT_QPA_PLATFORM=%s\n' "${QT_QPA_PLATFORM:-unavailable}"
```

确认是否为软件渲染要结合实际 EGL/DRM/QPA 后端和运行日志。HOST 的环境变量、GPU 或 `/proc` 不是 TARGET 证据。

## 存储健康

先在 TARGET 确认块设备、驱动与器件类型。以下 eMMC 生命周期字段依赖实际 sysfs 节点；仅对存在且可读的目标设备输出。

```sh
# TARGET：读取实际存在的 eMMC life_time 节点
found=0
for life_file in /sys/block/mmcblk*/device/life_time; do
  [ -r "$life_file" ] || continue
  printf '%s=' "$life_file"
  cat "$life_file"
  found=1
done
if [ "$found" -eq 0 ]; then printf '%s\n' 'eMMC life_time unavailable'; fi
cat /proc/mdstat
```

`smartctl` 只适用于目标实际提供且支持 SMART 的设备；先确认工具和设备，不使用臆造的设备名。器件字段含义和寿命等级按目标驱动及器件手册解释。

## 热区、CPU 频率与长跑采样

读取 thermal zone 时使用共享 [process-sampling.md](../../embedded-debug-workflow/references/process-sampling.md)，保留 zone ID、驱动 `type` 与原始温度值。标准 thermal sysfs `temp` 单位为 millidegree Celsius；未知传感器不作具体归因，不能默认 thermal zone 0 是 CPU 温度。CPU cpufreq 节点也按目标实际存在的路径读取；缺少节点不是零频率结论。

长跑进程 RSS、load average 和 thermal 的唯一示例在共享参考中。它有固定采样上限、只输出到终端、不解析 `top` 列位置、不覆盖日志文件；如需保存输出，应在 HOST 选择新的唯一目录并记录目标来源与采集时间。

## Oops 日志导出与符号化

### 可选 TARGET 日志导出

仅当 HOST 已配置并授权访问正确的 TARGET SSH alias，且目标上的 `dmesg -T` 可用、当前凭证有读取权限时使用。该块在 **HOST** 运行；alias 必须来自已有 SSH 配置且代表已核验的目标。`ssh`/`mktemp` 缺失、认证或远端命令失败都表示导出 unavailable；失败时可能保留不完整文件，不能当成完整日志。输出放入新建私有目录，不覆盖已有日志。

```sh
(
# HOST：需要已配置且授权的 TARGET SSH alias、OpenSSH client、mktemp 和写权限
if ! command -v ssh >/dev/null 2>&1 || ! command -v mktemp >/dev/null 2>&1; then
  printf '%s\n' 'HOST ssh or mktemp unavailable' >&2
  exit 127
fi
printf '%s' 'Verified TARGET SSH alias: '
IFS= read -r target_ssh_alias || { printf '%s\n' 'TARGET alias unavailable' >&2; exit 2; }
case "$target_ssh_alias" in ''|-*|*[!A-Za-z0-9_.-]*)
  printf '%s\n' 'use a configured alias containing only letters, digits, dot, underscore, or hyphen' >&2
  exit 2
  ;;
esac
umask 077
capture_dir=$(mktemp -d "${TMPDIR:-/tmp}/oops-capture.XXXXXX") || {
  printf '%s\n' 'could not create a new HOST capture directory' >&2
  exit 2
}
if ssh "$target_ssh_alias" 'dmesg -T' > "${capture_dir}/dmesg.txt"; then
  printf 'TARGET log saved under new HOST directory: %s\n' "$capture_dir"
else
  printf 'TARGET dmesg export failed or was partial; inspect only as incomplete: %s\n' "$capture_dir" >&2
  exit 1
fi
)
```

如果目标不支持 `dmesg -T`，需要另一种采集方式，或目标日志读取权限不可用，记录具体限制并使用已存在的、来源可核验的目标日志；不要用 HOST 的 `dmesg` 替代。

### HOST 离线符号化

需要 TARGET 运行构建对应的未 strip `vmlinux`、带 `CONFIG_DEBUG_INFO` 的调试数据、匹配模块，以及同一构建的内核源码树；模块栈帧还需匹配模块符号。先从已核验构建记录中取得这些真实路径。`decode_stacktrace.sh` 在 HOST 执行，失败或缺少源码/符号时报告未解析帧。

```sh
(
# HOST：输入实际匹配的目标构建文件路径；不是 TARGET 命令
printf '%s' 'Matching HOST kernel source tree: '
IFS= read -r kernel_tree || { printf '%s\n' 'kernel source path unavailable' >&2; exit 2; }
printf '%s' 'Matching unstripped vmlinux: '
IFS= read -r vmlinux_path || { printf '%s\n' 'vmlinux path unavailable' >&2; exit 2; }
printf '%s' 'Matching module directory (enter none if stack has no module frames): '
IFS= read -r module_dir || { printf '%s\n' 'module path input unavailable' >&2; exit 2; }
printf '%s' 'Verified TARGET Oops log path on HOST: '
IFS= read -r oops_log || { printf '%s\n' 'Oops log path unavailable' >&2; exit 2; }
if [ ! -x "${kernel_tree}/scripts/decode_stacktrace.sh" ] || [ ! -r "$vmlinux_path" ] || [ ! -r "$oops_log" ]; then
  printf '%s\n' 'matching decoder, vmlinux, or Oops log is unavailable' >&2
  exit 2
fi
if [ -n "$module_dir" ] && [ ! -d "$module_dir" ]; then
  printf '%s\n' 'matching module directory is unavailable' >&2
  exit 2
fi
if [ -n "$module_dir" ]; then
  "${kernel_tree}/scripts/decode_stacktrace.sh" "$vmlinux_path" "$kernel_tree" "$module_dir" < "$oops_log"
else
  "${kernel_tree}/scripts/decode_stacktrace.sh" "$vmlinux_path" "$kernel_tree" < "$oops_log"
fi
)
```

`System.map` can help identify symbols but does not provide source lines. Account for runtime relocation/KASLR using the target's actual offset and matching decode tools; do not calculate source locations from arbitrary address subtraction.
