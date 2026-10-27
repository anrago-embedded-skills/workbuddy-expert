# 进程与传感器采样

仅在需要检查特定进程/线程状态、观察进程资源趋势或读取热区数据时加载。以下目标命令都在 **TARGET** 的同一个 shell 中运行；不要用 HOST 的 `/proc` 或 `/sys` 代替目标证据。

目标侧需要可读的 procfs 与基本 shell、`awk`、`cat`、`date`、`sleep`。`ps`、`strace`、`timeout`、`pmap` 等可选工具及参数随镜像而异；先确认目标实际提供的实现和选项。权限不足、工具/字段不存在或读取失败时，记录 `unavailable` 及原因，不把缺失当作零值或健康证据。

## 验证 PID/TID 并准备路径

调用方应先从 TARGET 证据确认 PID，并将该值作为 `TARGET_PID` 提供给执行下面代码块的 TARGET shell。需要检查特定线程时，可同时提供已从该进程任务列表确认的 `TARGET_TID`；未提供或为空时使用进程 leader 的 PID。WorkBuddy 等非交互 shell 工具应通过它们的目标命令环境传入这些值，不能依赖 stdin 提示。不要提供猜测的 PID/TID。

把下面的验证段与后续引用 `target_pid`/`target_status` 的命令放在同一个 TARGET shell 中运行。它先验证正十进制 ID，再检查 PID 在目标 `/proc` 中可读，核对 `status` 中报告的 PID，并验证所选 TID 是该进程的可读任务。验证失败时设置段返回非零并退出当前命令 shell；不会继续采样。

```sh
# TARGET：先提供证据确认的 TARGET_PID；TARGET_TID 可选，未提供时默认 PID
is_positive_decimal_id() {
  case "$1" in ''|0|0*|*[!0-9]*) return 1 ;; *) return 0 ;; esac
}

prepare_target_process() {
  unset target_pid target_tid target_proc target_status target_task target_task_status
  candidate_pid=${TARGET_PID-}
  if ! is_positive_decimal_id "$candidate_pid"; then
    printf '%s\n' 'TARGET_PID must be a positive decimal integer without leading zeroes' >&2
    return 2
  fi

  candidate_proc="/proc/${candidate_pid}"
  candidate_status="${candidate_proc}/status"
  if [ ! -r "$candidate_status" ]; then
    printf '%s\n' 'target PID status is unavailable or unreadable' >&2
    return 2
  fi
  reported_pid=$(awk '$1 == "Pid:" { print $2; found=1 } END { if (!found) exit 1 }' "$candidate_status") || {
    printf '%s\n' 'could not validate PID from target status' >&2
    return 2
  }
  if [ "$reported_pid" != "$candidate_pid" ]; then
    printf '%s\n' 'PID changed or does not match target status; re-confirm it' >&2
    return 2
  fi

  candidate_tid=${TARGET_TID-}
  if [ -z "$candidate_tid" ]; then candidate_tid=$candidate_pid; fi
  if ! is_positive_decimal_id "$candidate_tid"; then
    printf '%s\n' 'TARGET_TID must be a positive decimal integer without leading zeroes' >&2
    return 2
  fi
  candidate_task="${candidate_proc}/task/${candidate_tid}"
  candidate_task_status="${candidate_task}/status"
  if [ ! -r "$candidate_task_status" ]; then
    printf '%s\n' 'TID is not a readable task of the selected process' >&2
    return 2
  fi
  reported_tid=$(awk '$1 == "Pid:" { print $2; found=1 } END { if (!found) exit 1 }' "$candidate_task_status") || {
    printf '%s\n' 'could not validate TID from target task status' >&2
    return 2
  }
  if [ "$reported_tid" != "$candidate_tid" ]; then
    printf '%s\n' 'TID changed or does not match target task status; re-confirm it' >&2
    return 2
  fi

  target_pid=$candidate_pid
  target_tid=$candidate_tid
  target_proc=$candidate_proc
  target_status=$candidate_status
  target_task=$candidate_task
  target_task_status=$candidate_task_status
}
prepare_target_process || exit $?
```

Keep this state in the same TARGET shell for the following snippets. PID reuse and task exit remain possible during observation; re-check process identity and time if the task may restart or exit while sampling.

## Process state and bounded inspection

```sh
# TARGET: uses paths set by the validated PID/TID block above
grep -E '^(State|TracerPid|Threads|FDSize):' "$target_status"
grep -E '^(State|TracerPid):' "$target_task_status"
cat "${target_proc}/wchan"
ls -l "${target_proc}/fd"
```

`TracerPid` nonzero means a tracer is attached; it does not by itself mean the task is stopped. `State: t` is a tracing stop, `T` is a job-control stop, and `Z` is a zombie. Thread states can differ. `wchan` and blocked system calls are observations, not proof of root cause: a FIFO read may simply have no data, `waitpid()` may wait for a still-running child, and a FIFO write can wait for buffer space. Preserve relevant evidence before restart unless service recovery must take priority.

Use `strace` only if present and permitted. `timeout` syntax differs across target images; confirm its options before use. If both are available, a bounded attach is:

```sh
# TARGET: optional; requires compatible timeout and strace, plus attach permission
timeout 10s strace -f -p "$target_pid"
```

If either command or permission is unavailable, record that limitation and use already available logs or process state; do not replace it with an unbounded attach.

## Bounded resource and thermal sampling

This sampler emits at most 121 lines, five seconds apart (about ten minutes), and writes only to the current terminal. Ctrl-C stops it early. It records RSS, system load averages, and each readable thermal zone's ID, driver-reported `type`, and raw `temp` value. It does not parse `top` columns or claim that load average is CPU utilization.

```sh
# TARGET: requires the validated target_status variable from the first block
sample_thermal_zones() {
  found=0
  for zone_dir in /sys/class/thermal/thermal_zone*; do
    [ -d "$zone_dir" ] || continue
    [ -r "${zone_dir}/type" ] && [ -r "${zone_dir}/temp" ] || continue
    zone_type=$(cat "${zone_dir}/type") || continue
    zone_value=$(cat "${zone_dir}/temp") || continue
    printf '%s:%s=%s ' "${zone_dir##*/}" "$zone_type" "$zone_value"
    found=1
  done
  if [ "$found" -eq 0 ]; then printf '%s' unavailable; fi
}

sample=0
while [ "$sample" -le 120 ]; do
  if [ -r "$target_status" ]; then
    rss_kb=$(awk '$1 == "VmRSS:" { print $2; found=1 } END { if (!found) print "unavailable" }' "$target_status") || rss_kb=unavailable
  else
    rss_kb=unavailable
  fi
  if [ -r /proc/loadavg ]; then
    loadavg=$(awk '{ print $1 "/" $2 "/" $3 }' /proc/loadavg) || loadavg=unavailable
  else
    loadavg=unavailable
  fi
  thermal=$(sample_thermal_zones) || thermal=unavailable
  printf '%s rss_kb=%s loadavg_1_5_15=%s thermal_zones=%s\n' "$(date)" "$rss_kb" "$loadavg" "$thermal"
  if [ "$sample" -lt 120 ]; then sleep 5; fi
  sample=$((sample + 1))
done
```

For the standard Linux thermal sysfs ABI, `temp` is in millidegree Celsius. A zone's `type` is the driver's label; attribute it to a physical sensor only when the target BSP/driver documentation maps that label. Keep unknown sensor readings as raw zone/type/value observations. If the interface is vendor-specific or its units are unconfirmed, do not infer a temperature. Never assume `thermal_zone0` is the CPU sensor.

The sampler reports missing/unreadable RSS, load average, or all thermal zones as `unavailable`; it does not create or overwrite a log file. If persistent output is required, choose a new run-specific destination on the HOST and preserve the exact TARGET provenance; do not append to or replace an existing log. A short interval without recurrence only describes that observation window.

## Related command prerequisites

- `ps`, `pmap`, `strace`, `timeout` and `pidstat` are optional and may differ on BusyBox and vendor images. Confirm availability and supported options on TARGET before using them.
- `dmesg`, `journalctl`, procfs, sysfs, and cgroup files may be restricted by privilege, kernel configuration, or init system. A missing source is unavailable evidence, not a negative finding.
- Capture outputs with timestamp, target identity, software/kernel build, command, sampling interval and duration. Do not treat a HOST process or sensor reading as TARGET data.
