#!/bin/sh
# Collect a bounded, read-only embedded Linux evidence snapshot.

LC_ALL=C
export LC_ALL
umask 077
set -f

MAX_FILE_CAPTURE_BYTES=65536
FILE_READ_PROBE_BYTES=66560
MAX_LINES=120
MAX_LINE_CHARS=240
MAX_OUTPUT_BYTES=$((MAX_LINES * (MAX_LINE_CHARS + 1)))

usage_error() {
    printf '%s\n' "collect-evidence.sh: $1" >&2
    printf '%s\n' 'Usage: collect-evidence.sh --mode env|kernel|process --output NEW_DIR [--pid POSITIVE_PID] [--source-root SNAPSHOT_ROOT]' >&2
    exit 2
}

mode=
output_arg=
pid_arg=
source_root_arg=
have_mode=0
have_output=0
have_pid=0
have_source_root=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --mode)
            [ "$#" -ge 2 ] || usage_error '--mode needs a value'
            [ "$have_mode" -eq 0 ] || usage_error '--mode may be specified once'
            mode=$2
            have_mode=1
            shift 2
            ;;
        --output)
            [ "$#" -ge 2 ] || usage_error '--output needs a value'
            [ "$have_output" -eq 0 ] || usage_error '--output may be specified once'
            output_arg=$2
            have_output=1
            shift 2
            ;;
        --pid)
            [ "$#" -ge 2 ] || usage_error '--pid needs a value'
            [ "$have_pid" -eq 0 ] || usage_error '--pid may be specified once'
            pid_arg=$2
            have_pid=1
            shift 2
            ;;
        --source-root)
            [ "$#" -ge 2 ] || usage_error '--source-root needs a value'
            [ "$have_source_root" -eq 0 ] || usage_error '--source-root may be specified once'
            source_root_arg=$2
            have_source_root=1
            shift 2
            ;;
        *)
            usage_error "unsupported argument: $1"
            ;;
    esac
done

[ "$have_mode" -eq 1 ] || usage_error 'missing --mode'
[ "$have_output" -eq 1 ] || usage_error 'missing --output'
case "$mode" in
    env|kernel|process) ;;
    *) usage_error 'mode must be env, kernel, or process' ;;
esac

if [ "$mode" = process ]; then
    [ "$have_pid" -eq 1 ] || usage_error 'process mode requires --pid'
    case "$pid_arg" in
        ''|*[!0-9]*) usage_error '--pid must be a positive decimal integer' ;;
    esac
    while [ "${pid_arg#0}" != "$pid_arg" ]; do
        pid_arg=${pid_arg#0}
    done
    [ -n "$pid_arg" ] || usage_error '--pid must be greater than zero'
elif [ "$have_pid" -eq 1 ]; then
    usage_error '--pid is supported only with --mode process'
fi

# Keep output paths lexical and reject any parent traversal before creating them.
case "$output_arg" in
    '') usage_error '--output must name a new directory' ;;
esac
case "/$output_arg/" in
    */../*) usage_error '--output may not contain a .. path component' ;;
esac
case "$output_arg" in
    *[[:cntrl:]]*) usage_error 'paths containing control characters are unsupported' ;;
esac

output_dir=$output_arg
case "$output_dir" in
    /*) ;;
    *) output_dir=./$output_dir ;;
esac

if [ "$have_source_root" -eq 1 ]; then
    [ -n "$source_root_arg" ] || usage_error '--source-root needs a directory'
    case "/$source_root_arg/" in
        */../*) usage_error '--source-root may not contain a .. path component' ;;
    esac
    case "$source_root_arg" in
        *[[:cntrl:]]*) usage_error 'paths containing control characters are unsupported' ;;
    esac
    root_input=$source_root_arg
    case "$root_input" in
        /*) ;;
        *) root_input=./$root_input ;;
    esac
    source_root=$(CDPATH= cd -P "$root_input" 2>/dev/null && pwd -P) || usage_error '--source-root is not an accessible directory'
    [ "$source_root" != / ] || usage_error '--source-root may not be the host root; provide a target snapshot directory'
    source_kind=offline
else
    if ! command -v uname >/dev/null 2>&1; then
        usage_error 'live collection requires uname and a Linux target'
    fi
    live_platform=$(uname -s 2>/dev/null) || usage_error 'unable to identify the live platform'
    [ "$live_platform" = Linux ] || usage_error "live collection is unsupported on $live_platform; use --source-root for an offline snapshot"
    source_kind=live
    source_root=/
fi

for required_utility in awk wc cat mkdir rm head; do
    command -v "$required_utility" >/dev/null 2>&1 || usage_error "required utility is unavailable: $required_utility"
done

if [ -e "$output_dir" ]; then
    usage_error '--output already exists; choose a new directory'
fi
mkdir "$output_dir" 2>/dev/null || usage_error 'cannot create --output (its parent must exist and be writable)'

items_file=$output_dir/.manifest-items.tmp
summary_items_file=$output_dir/.summary-items.tmp
: > "$items_file" || usage_error 'cannot initialize manifest data'
: > "$summary_items_file" || usage_error 'cannot initialize summary data'
output_error=0

if command -v date >/dev/null 2>&1; then
    collector_time=$(date -u '+%Y-%m-%dT%H:%M:%SZ' 2>/dev/null)
else
    collector_time=
fi
[ -n "$collector_time" ] || collector_time=unavailable
date_unavailable=0
[ "$collector_time" != unavailable ] || date_unavailable=1

overall_partial=0
item_count=0

json_escape() {
    printf '%s' "$1" | awk '
        {
            if (NR > 1) printf "\\n"
            for (i = 1; i <= length($0); i++) {
                c = substr($0, i, 1)
                if (c == "\\") printf "\\\\"
                else if (c == "\"") printf "\\\""
                else if (c == "\t") printf "\\t"
                else if (c == "\r") printf "\\r"
                else printf "%s", c
            }
        }
    '
}

append_item() {
    item_name=$1
    item_source=$2
    item_output=$3
    item_status=$4
    item_detail=$5
    item_command_exit_code=${6:-null}
    if [ "$item_count" -gt 0 ]; then
        printf ',\n' >> "$items_file" || { output_error=1; return 1; }
    fi
    printf '  {"name":"%s","source":"%s","output":"%s","status":"%s","detail":"%s","command_exit_code":%s}' \
        "$(json_escape "$item_name")" \
        "$(json_escape "$item_source")" \
        "$(json_escape "$item_output")" \
        "$(json_escape "$item_status")" \
        "$(json_escape "$item_detail")" \
        "$item_command_exit_code" >> "$items_file" || { output_error=1; return 1; }
    printf '%s\t%s\t%s\t%s\n' "$item_name" "$item_status" "$item_source" "$item_output" >> "$summary_items_file" || { output_error=1; return 1; }
    item_count=$((item_count + 1))
    case "$item_status" in
        collected) ;;
        *) overall_partial=1 ;;
    esac
}

if [ "$date_unavailable" -eq 1 ]; then
    append_item collector-clock host-clock '' tool_missing 'date is unavailable; collector timestamp could not be recorded'
fi

# BEGIN os-release source selection helpers
source_path_for() {
    if [ "$source_root" = / ]; then
        source_path=/$1
    else
        source_path=$source_root/$1
    fi
}

path_has_symlink_component() {
    path_to_check=$1
    current_path=$source_root
    saved_ifs=$IFS
    IFS=/
    for path_component in $path_to_check; do
        [ -n "$path_component" ] || continue
        if [ "$current_path" = / ]; then
            current_path=/$path_component
        else
            current_path=$current_path/$path_component
        fi
        if [ -L "$current_path" ]; then
            IFS=$saved_ifs
            return 0
        fi
    done
    IFS=$saved_ifs
    return 1
}

select_live_os_release_source() {
    os_release_source=etc/os-release
    os_release_status=
    source_path_for "$os_release_source"
    if [ ! -L "$source_path" ]; then
        return 0
    fi
    if ! command -v readlink >/dev/null 2>&1; then
        os_release_status=tool_missing
        return 1
    fi
    os_release_link_target=$(readlink "$source_path" 2>/dev/null) || {
        os_release_status=unsafe_path
        return 1
    }
    case "$os_release_link_target" in
        /usr/lib/os-release|../usr/lib/os-release) os_release_source=usr/lib/os-release ;;
        *)
            os_release_status=unsafe_path
            return 1
            ;;
    esac
    if path_has_symlink_component "$os_release_source"; then
        os_release_status=unsafe_path
        return 1
    fi
    return 0
}

collect_os_release() {
    if [ "$source_kind" = live ]; then
        if select_live_os_release_source; then
            collect_file os-release "$os_release_source" os-release.txt text
        else
            case "$os_release_status" in
                tool_missing) detail='readlink is unavailable; refusing to follow the os-release symlink' ;;
                *) detail='os-release symlink does not resolve to the supported /usr/lib/os-release path' ;;
            esac
            append_item os-release etc/os-release os-release.txt "$os_release_status" "$detail"
        fi
    else
        collect_file os-release etc/os-release os-release.txt text
    fi
}
# END os-release source selection helpers

format_capture() {
    format_input=$1
    format_output=$2
    format_transform=$3
    format_byte_truncated=$4
    format_direction=$5
    format_flag=$output_dir/.capture-flag.tmp
    : > "$format_flag" || { output_error=1; capture_status=error; return 1; }

    if [ "$format_transform" = dt ]; then
        tr '\000' '\n' < "$format_input" 2>/dev/null | awk \
            -v max_lines="$MAX_LINES" -v width="$MAX_LINE_CHARS" -v flag="$format_flag" '
                {
                    if (NR > max_lines) { clipped = 1; next }
                    line = $0
                    if (length(line) > width) { clipped = 1; line = substr(line, 1, width) }
                    gsub(/\t/, " ", line)
                    gsub(/[[:cntrl:]]/, "?", line)
                    print line
                }
                END { if (clipped) print "truncated" > flag }
            ' > "$format_output"
    elif [ "$format_direction" = tail ]; then
        awk \
            -v max_lines="$MAX_LINES" -v width="$MAX_LINE_CHARS" -v flag="$format_flag" '
                {
                    line = $0
                    if (length(line) > width) { clipped = 1; line = substr(line, 1, width) }
                    gsub(/\t/, " ", line)
                    gsub(/[[:cntrl:]]/, "?", line)
                    record_count++
                    slot = ((record_count - 1) % max_lines) + 1
                    records[slot] = line
                }
                END {
                    first = record_count - max_lines + 1
                    if (first < 1) first = 1
                    for (sequence = first; sequence <= record_count; sequence++) {
                        slot = ((sequence - 1) % max_lines) + 1
                        print records[slot]
                    }
                    if (record_count > max_lines || clipped) print "truncated" > flag
                }
            ' "$format_input" > "$format_output"
    else
        awk \
            -v max_lines="$MAX_LINES" -v width="$MAX_LINE_CHARS" -v flag="$format_flag" '
                {
                    if (NR > max_lines) { clipped = 1; next }
                    line = $0
                    if (length(line) > width) { clipped = 1; line = substr(line, 1, width) }
                    gsub(/\t/, " ", line)
                    gsub(/[[:cntrl:]]/, "?", line)
                    print line
                }
                END { if (clipped) print "truncated" > flag }
            ' "$format_input" > "$format_output"
    fi

    formatting_status=$?
    if [ "$formatting_status" -ne 0 ]; then
        output_error=1
        capture_status=error
        rm -f "$format_flag"
        return
    fi
    capture_status=collected
    if [ "$format_byte_truncated" -eq 1 ] || [ -s "$format_flag" ]; then
        capture_status=truncated
    elif [ ! -s "$format_output" ]; then
        capture_status=empty
    fi
    rm -f "$format_flag"
}

collect_file() {
    item_name=$1
    relative_source=$2
    output_name=$3
    transform=$4
    capture_direction=${5:-head}
    source_path_for "$relative_source"

    if path_has_symlink_component "$relative_source"; then
        append_item "$item_name" "$relative_source" "$output_name" unsafe_path 'source path contains a symlink; offline capture does not follow it'
        return
    fi
    if [ ! -e "$source_path" ]; then
        append_item "$item_name" "$relative_source" "$output_name" missing 'source file is absent'
        return
    fi
    if [ ! -r "$source_path" ]; then
        append_item "$item_name" "$relative_source" "$output_name" permission_denied 'source file is not readable'
        return
    fi
    if [ ! -f "$source_path" ]; then
        append_item "$item_name" "$relative_source" "$output_name" error 'source is not a regular file'
        return
    fi
    if ! command -v head >/dev/null 2>&1; then
        append_item "$item_name" "$relative_source" "$output_name" tool_missing 'head -c is unavailable; byte bounds cannot be enforced'
        return
    fi
    if [ "$transform" = dt ] && ! command -v tr >/dev/null 2>&1; then
        append_item "$item_name" "$relative_source" "$output_name" tool_missing 'tr is unavailable for NUL-delimited device-tree strings'
        return
    fi
    if [ "$capture_direction" = tail ] && ! command -v tail >/dev/null 2>&1; then
        append_item "$item_name" "$relative_source" "$output_name" tool_missing 'tail -c is unavailable for bounded recent-log capture'
        return
    fi

    raw_file=
    limited_file=$output_dir/.capture-limited.tmp
    : > "$limited_file" || {
        output_error=1
        append_item "$item_name" "$relative_source" "$output_name" error 'cannot create bounded capture temporary file'
        return
    }
    if [ "$capture_direction" = tail ]; then
        source_byte_count=$(wc -c < "$source_path" 2>/dev/null)
        source_byte_count=$(printf '%s\n' "$source_byte_count" | awk '{ print $1 }')
        case "$source_byte_count" in
            ''|*[!0-9]*)
                output_error=1
                rm -f "$limited_file"
                append_item "$item_name" "$relative_source" "$output_name" error 'could not determine offline log size'
                return
                ;;
        esac
        if awk -v byte_count="$source_byte_count" -v max_bytes="$MAX_FILE_CAPTURE_BYTES" 'BEGIN { exit !(byte_count > max_bytes) }'; then
            byte_truncated=1
        else
            byte_truncated=0
        fi
        tail -c "$MAX_FILE_CAPTURE_BYTES" "$source_path" > "$limited_file" 2>/dev/null
        read_status=$?
    else
        raw_file=$output_dir/.capture-raw.tmp
        : > "$raw_file" || {
            output_error=1
            rm -f "$limited_file"
            append_item "$item_name" "$relative_source" "$output_name" error 'cannot create source capture temporary file'
            return
        }
        head -c "$FILE_READ_PROBE_BYTES" "$source_path" > "$raw_file" 2>/dev/null
        read_status=$?
        if [ "$read_status" -eq 0 ]; then
            raw_byte_count=$(wc -c < "$raw_file" 2>/dev/null)
            raw_byte_count=$(printf '%s\n' "$raw_byte_count" | awk '{ print $1 }')
            case "$raw_byte_count" in
                ''|*[!0-9]*)
                    output_error=1
                    rm -f "$raw_file" "$limited_file"
                    append_item "$item_name" "$relative_source" "$output_name" error 'could not determine bounded source size'
                    return
                    ;;
            esac
            if [ "$raw_byte_count" -gt "$MAX_FILE_CAPTURE_BYTES" ]; then
                byte_truncated=1
            else
                byte_truncated=0
            fi
            head -c "$MAX_FILE_CAPTURE_BYTES" "$raw_file" > "$limited_file" 2>/dev/null
            read_status=$?
            if [ "$read_status" -ne 0 ]; then
                output_error=1
            fi
        fi
    fi
    if [ "$read_status" -ne 0 ]; then
        [ -z "$raw_file" ] || rm -f "$raw_file"
        rm -f "$limited_file"
        append_item "$item_name" "$relative_source" "$output_name" error 'bounded source read failed'
        return
    fi

    output_path=$output_dir/$output_name
    format_capture "$limited_file" "$output_path" "$transform" "$byte_truncated" "$capture_direction"
    capture_status_local=$capture_status
    [ -z "$raw_file" ] || rm -f "$raw_file"
    rm -f "$limited_file"
    case "$capture_status_local" in
        collected) detail='captured within configured limits' ;;
        truncated) detail='capture was clipped by a byte, line, or line-width limit' ;;
        empty) detail='source file was readable but contained no data' ;;
        error) detail='text capture formatting failed' ;;
        *) detail='capture status unavailable' ;;
    esac
    append_item "$item_name" "$relative_source" "$output_name" "$capture_status_local" "$detail"
}

collect_dmesg() {
    item_name=kernel-dmesg
    output_name=kernel-dmesg.txt
    if ! command -v dmesg >/dev/null 2>&1; then
        append_item "$item_name" dmesg "$output_name" tool_missing 'dmesg is not installed'
        return
    fi
    output_path=$output_dir/$output_name
    producer_status_file=$output_dir/.dmesg-status.tmp
    stream_flag_file=$output_dir/.dmesg-truncated.tmp
    : > "$stream_flag_file" || {
        output_error=1
        append_item "$item_name" 'dmesg stdout+stderr' "$output_name" error 'cannot create dmesg stream status file'
        return
    }
    (
        dmesg 2>&1
        producer_status=$?
        printf '%s\n' "$producer_status" > "$producer_status_file"
    ) | awk \
        -v max_lines="$MAX_LINES" -v width="$MAX_LINE_CHARS" -v flag="$stream_flag_file" '
            {
                line = $0
                if (length(line) > width) { clipped = 1; line = substr(line, 1, width) }
                gsub(/\t/, " ", line)
                gsub(/[[:cntrl:]]/, "?", line)
                record_count++
                slot = ((record_count - 1) % max_lines) + 1
                records[slot] = line
            }
            END {
                first = record_count - max_lines + 1
                if (first < 1) first = 1
                for (sequence = first; sequence <= record_count; sequence++) {
                    slot = ((sequence - 1) % max_lines) + 1
                    print records[slot]
                }
                if (record_count > max_lines || clipped) print "truncated" > flag
            }
        ' > "$output_path"
    formatting_status=$?
    if [ "$formatting_status" -ne 0 ]; then
        output_error=1
        rm -f "$producer_status_file" "$stream_flag_file"
        append_item "$item_name" 'dmesg stdout+stderr' "$output_name" error 'bounded dmesg stream formatting failed'
        return
    fi

    producer_status=$(cat "$producer_status_file" 2>/dev/null)
    case "$producer_status" in
        ''|*[!0-9]*)
            output_error=1
            manifest_command_exit_code=null
            capture_status_local=error
            detail='dmesg exit status could not be recorded'
            ;;
        0)
            manifest_command_exit_code=0
            if [ ! -s "$output_path" ]; then
                capture_status_local=empty
                detail='dmesg succeeded but returned no log records'
            elif [ -s "$stream_flag_file" ]; then
                capture_status_local=truncated
                detail='latest dmesg output was clipped to the configured line and width limits'
            else
                capture_status_local=collected
                detail='latest dmesg output was captured within configured limits'
            fi
            ;;
        *)
            manifest_command_exit_code=$producer_status
            if awk 'tolower($0) ~ /(permission denied|not permitted|access denied)/ { found = 1 } END { exit found ? 0 : 1 }' "$output_path"; then
                capture_status_local=permission_denied
                detail="dmesg exited with status $producer_status; captured output indicates a permission denial"
            else
                capture_status_local=error
                detail="dmesg exited with status $producer_status; inspect the bounded output"
            fi
            ;;
    esac
    rm -f "$producer_status_file" "$stream_flag_file"
    append_item "$item_name" 'dmesg stdout+stderr' "$output_name" "$capture_status_local" "$detail" "$manifest_command_exit_code"
}

collect_device_tree_file() {
    dt_name=$1
    dt_filename=$2
    dt_proc_rel=$3
    dt_sys_rel=$4
    chosen_rel=$dt_proc_rel
    if [ "$source_kind" = live ]; then
        if ! path_has_symlink_component "$dt_sys_rel"; then
            source_path_for "$dt_sys_rel"
            if [ -e "$source_path" ]; then
                chosen_rel=$dt_sys_rel
            fi
        fi
    fi
    collect_file "$dt_name" "$chosen_rel" "$dt_filename" dt
}

case "$mode" in
    env)
        collect_file proc-version proc/version proc-version.txt text
        collect_os_release
        collect_file boot-command-line proc/cmdline proc-cmdline.txt text
        collect_file memory-summary proc/meminfo proc-meminfo.txt text
        collect_file swap-summary proc/swaps proc-swaps.txt text
        collect_device_tree_file device-tree-model device-tree-model.txt proc/device-tree/model sys/firmware/devicetree/base/model
        collect_device_tree_file device-tree-compatible device-tree-compatible.txt proc/device-tree/compatible sys/firmware/devicetree/base/compatible
        ;;
    kernel)
        if [ "$source_kind" = live ]; then
            collect_dmesg
        else
            collect_file kernel-kern-log var/log/kern.log kernel-var-log-kern.log.txt text tail
            collect_file kernel-messages-log var/log/messages kernel-var-log-messages.txt text tail
            collect_file kernel-dmesg-log var/log/dmesg kernel-var-log-dmesg.txt text tail
            collect_file kernel-last-kmsg proc/last_kmsg kernel-proc-last_kmsg.txt text tail
        fi
        ;;
    process)
        collect_file process-status "proc/$pid_arg/status" "process-$pid_arg-status.txt" text
        collect_file process-limits "proc/$pid_arg/limits" "process-$pid_arg-limits.txt" text
        collect_file process-wchan "proc/$pid_arg/wchan" "process-$pid_arg-wchan.txt" text
        collect_file process-cgroup "proc/$pid_arg/cgroup" "process-$pid_arg-cgroup.txt" text
        collect_file process-mountinfo "proc/$pid_arg/mountinfo" "process-$pid_arg-mountinfo.txt" text
        ;;
esac

[ "$output_error" -eq 0 ] || usage_error 'collection output or per-item metadata could not be written; no success manifest was emitted'

collection_status=complete
[ "$overall_partial" -eq 0 ] || collection_status=partial
source_root_json=$(json_escape "$source_root")
collector_time_json=$(json_escape "$collector_time")
pid_json=null
if [ "$mode" = process ]; then
    pid_json="\"$(json_escape "$pid_arg")\""
fi

manifest_file=$output_dir/manifest.json
write_manifest() {
    printf '{\n' || return 1
    printf '  "schema_version": 1,\n' || return 1
    printf '  "mode": "%s",\n' "$mode" || return 1
    printf '  "source_kind": "%s",\n' "$source_kind" || return 1
    printf '  "source_root": "%s",\n' "$source_root_json" || return 1
    printf '  "pid": %s,\n' "$pid_json" || return 1
    printf '  "collector_time_utc": "%s",\n' "$collector_time_json" || return 1
    printf '  "collection_status": "%s",\n' "$collection_status" || return 1
    printf '  "limits": {"max_file_capture_bytes": %s, "max_prefix_file_probe_bytes": %s, "max_output_lines": %s, "max_line_bytes": %s, "max_output_bytes": %s, "live_dmesg_input_byte_limit": null, "live_dmesg_kept_lines": %s},\n' \
        "$MAX_FILE_CAPTURE_BYTES" "$FILE_READ_PROBE_BYTES" "$MAX_LINES" "$MAX_LINE_CHARS" "$MAX_OUTPUT_BYTES" "$MAX_LINES" || return 1
    printf '  "sampling": {"atomic": false, "scope": "environment and process files use bounded prefixes; offline kernel logs retain a bounded recent tail; live dmesg is streamed from the finite kernel ring and retains the latest configured lines; process cgroup and mountinfo are captured for follow-up, not dynamically resolved"},\n' || return 1
    printf '  "items": [\n' || return 1
    cat "$items_file" || return 1
    printf '\n  ]\n' || return 1
    printf '}\n' || return 1
}

if ! write_manifest > "$manifest_file"; then
    rm -f "$manifest_file"
    usage_error 'failed to assemble manifest.json'
fi

summary_file=$output_dir/summary.txt
write_summary() {
    printf '%s\n' 'Embedded Linux evidence snapshot' || return 1
    printf 'collector_time_utc: %s\n' "$collector_time" || return 1
    printf 'mode: %s\n' "$mode" || return 1
    printf 'source_kind: %s\n' "$source_kind" || return 1
    printf 'source_root: %s\n' "$source_root" || return 1
    if [ "$mode" = process ]; then
        printf 'pid: %s\n' "$pid_arg" || return 1
    fi
    printf 'collection_status: %s\n' "$collection_status" || return 1
    printf 'limits: retained file data <= %s bytes, <= %s lines, <= %s bytes per line; output <= %s bytes\n' "$MAX_FILE_CAPTURE_BYTES" "$MAX_LINES" "$MAX_LINE_CHARS" "$MAX_OUTPUT_BYTES" || return 1
    printf '%s\n' 'Capture is non-atomic and limited to the listed files.' || return 1
    printf '%s\n' 'Missing data does not indicate a healthy target.' || return 1
    printf '%s\n' 'This snapshot cannot automatically determine OOM scope, memory leaks, or root cause.' || return 1
    printf '%s\n' 'Item status: name<TAB>status<TAB>source<TAB>output' || return 1
    cat "$summary_items_file" || return 1
}

if ! write_summary > "$summary_file"; then
    rm -f "$summary_file"
    usage_error 'failed to assemble summary.txt'
fi

rm -f "$items_file" "$summary_items_file"
printf 'collection_status=%s\nmanifest=%s\nsummary=%s\n' "$collection_status" "$manifest_file" "$summary_file"
