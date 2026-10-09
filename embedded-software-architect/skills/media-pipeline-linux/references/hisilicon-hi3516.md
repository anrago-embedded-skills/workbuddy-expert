# 海思 HiSilicon Hi3516 平台适配

> 海思 Hi3516 系列常见于安防IPC、视觉类设备。编解码由 **HiVCodec**（VDEC/VENC）承担，历史上也有 OSD 区域叠加等专用能力。

## 硬件加速能力

| 引擎 | 用途 | 访问方式 |
|---|---|---|
| **VDEC** | H.264/H.265 硬解 | HiVCodec API / MPP |
| **VENC** | H.264/H.265 硬编 | HiVCodec API |
| **IVE** | 图像/视频加速（部分系列） | IVE API |
| **VO** | 视频输出 | VO API |

**注意**：Hi3516 系列跨度很大（Hi3516C / Hi3516D / Hi3516E / Hi3516CV300 等），芯片能力和接口**差异明显**，必须以具体型号手册为准。

---

## 关键特征

- 海思 SDK 传统上使用 **MPP**（Media Processing Platform）命名，但**与 Rockchip MPP 是不同东西，API 不兼容**——不要混淆
- OSD（On-Screen Display）叠加是海思的传统强项，用于时钟、水印、字幕等图文叠加场景
- 部分型号有 **VDEC 通道数上限**，多路解码需确认

---

## MPP（海思版）

```c
// 海思 MPP 使用 MPI 接口，与 Rockchip MPP API 完全不同
MPI_SYS_Init();
MPI_VDEC_CreateChn(&chn);      // 创建解码通道
MPI_VDEC_SetAttr(&chn, &attr);
MPI_VDEC_Start(&chn);
```

**核心提醒**：海思 MPP 和 Rockchip MPP 同名不同物。**接口、类型定义、流程都不同**，跨平台迁移时不能直接替换。

---

## 排查要点

- 摄像头 sensor 与 Hi3516 的pipeline 配置强相关，常见问题是**sensor 驱动与主控适配不匹配**
- 视频输出（VO）的显示层序配置错误会导致黑屏或层序颠倒
- OSD 叠加区域内存不足会花屏
- 老型号社区资料多但新资料少，需依赖海思官方文档

---

## 边界与注意

- **海思 MPP ≠ Rockchip MPP**，API 完全不同，这是最容易踩的坑
- 同系列不同型号（Hi3516C/D/E）能力差异大，不要互相套用
- 本文为平台骨架，具体寄存器/接口必须查该型号官方文档
- 未在具体型号上实测的推断需标注为待验证