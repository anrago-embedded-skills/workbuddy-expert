# Socket API 与 TCP 帧实现

> 仅在检查或修改应用 socket 选项、发送/接收循环或帧解析器时读取。单纯判读 Send-Q、接口计数或连接状态时使用网络取证速查表即可。

## 每个 socket 的缓冲区与选项

先在同一负载下记录队列、应用处理耗时和内存基线。只有证据表明单 socket 缓冲限制是瓶颈时才评估 `SO_RCVBUF` / `SO_SNDBUF`；目标内核参数和实际 socket 值见 [kernel-network-tuning.md](kernel-network-tuning.md)。写入选项会立即改变该 socket 的运行行为，数值必须来自测量并处于目标限制内，不能照抄通用推荐值。

```c
// C 代码片段，不是完整函数。requested_bytes 必须来自测量并符合目标限制。
int requested_bytes = measured_socket_buffer_bytes;
if (setsockopt(fd, SOL_SOCKET, SO_RCVBUF,
               &requested_bytes, sizeof(requested_bytes)) < 0) {
    /* 保留 errno 并处理失败 */
}

int effective_bytes = 0;
socklen_t effective_len = sizeof(effective_bytes);
if (getsockopt(fd, SOL_SOCKET, SO_RCVBUF,
               &effective_bytes, &effective_len) < 0) {
    /* 保留 errno 并处理失败 */
}

// 修改单个 socket 状态；启用前测量延迟和包开销。
int enabled = 1;
if (setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &enabled, sizeof(enabled)) < 0) {
    /* 保留 errno 并处理失败 */
}
```

Linux 的 socket 缓冲区记账行为依实现而异；常见内核会将 `SO_RCVBUF` / `SO_SNDBUF` 请求值翻倍后通过 `getsockopt()` 返回。应核对目标内核的实际结果，不能假定请求值等于生效值。`TCP_NODELAY` 会为该 socket 禁用 Nagle，可能降低部分小写入延迟，同时增加包开销；启用前先测量。

不要用增大缓冲区来掩盖持续增长的 Recv-Q、消费过慢或应用停止读取。内核上限或 TCP 自动调优范围不表示某连接实际使用了对应内存。在相同且有界的负载下比较 socket 生效值、队列、延迟和内存。

## TCP 字节流与帧边界

TCP 保证字节顺序，不保留 `send()` 或 `recv()` 调用边界。一次读取可能只拿到部分 header/payload，也可能一次读到多次写入的数据。应用必须定义明确的帧规则：固定长度、经过转义的分隔符、有上限的长度前缀或 TLV。二进制长度前缀必须定义字节序，并在分配内存前检查最大帧长。

```c
// C 代码片段。recv_full 应在 EINTR/EAGAIN 或截止时间到达时保留部分进度。
uint32_t wire_length = 0;
enum io_result r = recv_full(fd, &wire_length, sizeof(wire_length), deadline);
if (r == IO_EOF) goto close_connection;
if (r == IO_TIMEOUT) goto preserve_or_discard_partial_frame_by_policy;
if (r != IO_COMPLETE) goto handle_socket_error;

uint32_t frame_length = ntohl(wire_length);
if (frame_length > MAX_FRAME_BYTES) goto protocol_error;
uint8_t *frame = NULL;
if (frame_length == 0) {
    if (!zero_length_frames_are_valid) goto protocol_error;
} else {
    frame = malloc(frame_length);
    if (frame == NULL) goto allocation_error;
    r = recv_full(fd, frame, frame_length, deadline);
    if (r != IO_COMPLETE) {
        free(frame);
        goto close_or_resume_by_policy;
    }
}
process_complete_frame(frame, frame_length);  // 仅当长度为零时 helper 才接受 NULL
free(frame);
```

以上名称是应用辅助函数的契约示例，不是 Linux API。辅助函数必须在超时时保留或按策略丢弃部分进度，适当地重试 `EINTR`，并区分 EOF、`EAGAIN`/`EWOULDBLOCK` 与其他错误。`recv()` 返回零表示对端有序关闭；正数短读属于正常情况。未完成帧状态要绑定到连接代次，避免旧 socket 的字节补全新连接的帧。

发送路径也必须推进正数短写的偏移。非阻塞 socket 遇到 `EAGAIN`/`EWOULDBLOCK` 时保留尚未发送的后缀，处理 `EINTR` 并遵守截止时间。部分写入成功不代表整条应用消息已发送；TCP 确认也不能证明对端应用已经处理消息。

帧解析器应在分配前拒绝超过固定应用上限的长度，检查字节序和整数转换，并在错误、EOF、连接重置等每条路径释放缓冲区。在主机字节流夹具中测试 header/payload 的切分边界及 timeout、EOF、中断和重置；这不能验证目标网络或驱动。

参考：[Linux `socket(7)`](https://man7.org/linux/man-pages/man7/socket.7.html)、[Linux `tcp(7)`](https://man7.org/linux/man-pages/man7/tcp.7.html)、[Linux `recv(2)`](https://man7.org/linux/man-pages/man2/recv.2.html)。
