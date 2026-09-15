# MiniMax-H3 网关：同事 API 使用指南

这是 Spark 上仅供团队通过 Tailscale 调用的内部视频生成 API。它不是公开服务，
也不是任意 ComfyUI 工作流代理。调用者只能选择已审核的尺寸档位，不能指定模型、
节点或工作流。

本文只提供 **Bruno** 示例。部署和维护请看
[H3 网关运维手册](minimax-h3-gateway-manual.md)。

## 1. 连接

当前 Tailscale 基地址：

```text
http://100.64.35.71:8090
```

在 Bruno 的**私密环境变量**中设置（不要把真实 Key 提交到 Bruno YAML）：

```text
H3_GATEWAY_BEARER=<向团队取得当前 Key>
```

除 `/health` 外，所有接口使用：

```yaml
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

### Bruno：健康检查

```yaml
info:
  name: H3 - Health
  type: http
http:
  method: GET
  url: http://100.64.35.71:8090/health
```

返回的 `profiles` 是当前可用尺寸的唯一权威来源；`queuedJobs` 是等待数量，
H3 始终一次生成一条。

## 2. 可选尺寸与时长

`profileId` 必填；分辨率由 profile 固定。`durationSeconds` 可选，默认 `5`，
仅接受 **5–15 的整数秒**。H3 以 24 fps 和 `17k + 5` 的原生帧格运行，故实际
时长可能略长：5 秒请求是 124 帧，即约 5.17 秒。

| 方向 | 输出尺寸 | `profileId` |
| --- | ---: | --- |
| 横版快速 | 832 × 480 | `minimax_h3_fp8_turbo4_landscape_832x480_v1` |
| 横版标准 | 960 × 544 | `minimax_h3_fp8_turbo4_landscape_960x544_v1` |
| 横版高分 | 1280 × 704 | `minimax_h3_fp8_turbo4_landscape_1280x704_v1` |
| 竖版快速 | 576 × 1024 | `minimax_h3_fp8_turbo4_portrait_576x1024_v1` |
| 竖版标准 | 608 × 1088 | `minimax_h3_fp8_turbo4_portrait_608x1088_v1` |
| 竖版高分 | 704 × 1280 | `minimax_h3_fp8_turbo4_portrait_704x1280_v1` |

`seed` 也是可选。省略时服务器会生成随机 seed；返回的任务和状态响应都会给出
最终采用的 `seed`，方便复查。

## 3. 图片输入与 `aspectPolicy`

图片可用 JSON 的可下载 `sourceUrl` / `endSourceUrl`，或 Bruno multipart 的
`image` / `endImage` 文件。**一次请求不能混用 URL 和文件。** 每张图片支持 JPEG、
PNG、WebP，最大 20 MiB、3,000 万像素；URL 只在接收时下载，不会被保存。

上传图不必与输出尺寸像素完全一致，但应有相同的宽高比。例如 1664 × 960 与
832 × 480 都可作为横版快速的严格匹配输入。网关会统一处理到输出尺寸。

| `aspectPolicy` | 比例不同怎么办 | 使用场景 |
| --- | --- | --- |
| `reject_mismatch` | 直接拒绝，不生成 | 推荐默认；先在图片工具中完成正确构图 |
| `contain_pad` | 等比缩小并补黑边 | **明确想保留黑边**的画面；模型可能把黑边带入生成 |
| `cover_center_crop` | 中心裁切再缩放 | 已审核中央裁切安全的旧图 |

横图放到竖画布用 `contain_pad` 时通常会有上下黑边；竖图放到横画布时通常有左右
黑边。若目标是让模型生成真正的竖版空间，请先制作匹配竖版的起始图并使用
`reject_mismatch`。`contain_pad` 是允许黑边的开关，不是自动扩图功能。

## 4. 接口一览

| 方法 | 用途 |
| --- | --- |
| `GET /health` | 服务、ComfyUI、profile 与队列检查（无需 Bearer） |
| `POST /v1/video-jobs/from-image` | 起始图必填、末帧可选的 I2V |
| `POST /v1/video-jobs/from-text` | 仅探索用途的 T2V，不是 Plotloom 创作模式 |
| `GET /v1/video-jobs/{id}` | 查询状态、seed、帧数和生成计时 |
| `GET /v1/video-jobs/{id}/output` | 下载完成 MP4 |
| `POST /v1/video-jobs/{id}/cancel` | 仅取消仍为 `queued` 的任务 |

旧的 `/v1/assets` 与 `POST /v1/video-jobs` 已移除，返回 404。不存在 `assetId`
或 `idempotencyKey` 工作流。发送后若 Bruno 超时，不要盲目重试：任务可能已经入队。

## 5. Bruno：URL 起始图 + 可选末帧

JSON 方式适合同事已有可下载图片 URL。下例为 8 秒、首尾帧 I2V：

```yaml
info:
  name: H3 - Image to video from URLs
  type: http
http:
  method: POST
  url: http://100.64.35.71:8090/v1/video-jobs/from-image
  headers:
    - name: Content-Type
      value: application/json
  body:
    type: json
    data: |-
      {
        "sourceUrl": "https://example.internal/scene-start.png",
        "endSourceUrl": "https://example.internal/scene-end.png",
        "prompt": "Cinematic medium shot. The explorer crosses the cabin slowly; natural movement, stable camera, coherent lighting.",
        "profileId": "minimax_h3_fp8_turbo4_portrait_576x1024_v1",
        "aspectPolicy": "reject_mismatch",
        "seed": 42,
        "durationSeconds": 8
      }
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

省略 `endSourceUrl` 即为普通“只有起始图”的 I2V。URL 输入不要同时以
multipart 附加 `image` 或 `endImage`。

## 6. Bruno：本地起始图 + 可选末帧

在 Bruno 选择 **Body → Multipart Form**，不要手写 `Content-Type`（Bruno 会产生
正确 boundary）。

| 字段 | 类型 | 值 |
| --- | --- | --- |
| `image` | File | 必填，起始图 |
| `endImage` | File | 可选，末帧 |
| `prompt` | Text | 必填 |
| `profileId` | Text | 上表中的一项 |
| `aspectPolicy` | Text | 上表中的一项 |
| `seed` | Text | 可选整数 |
| `durationSeconds` | Text | 可选 5–15 整数 |

请求地址仍为：

```text
POST http://100.64.35.71:8090/v1/video-jobs/from-image
```

## 7. Bruno：T2V 探索

T2V 仅用于独立试验；它不进入 Plotloom 的作者工作台，也不替代审核关键帧。
此接口只能用 JSON，且**不接受** `sourceUrl`、`image`、`endImage` 或
`aspectPolicy`：

```yaml
info:
  name: H3 - Text to video exploration
  type: http
http:
  method: POST
  url: http://100.64.35.71:8090/v1/video-jobs/from-text
  headers:
    - name: Content-Type
      value: application/json
  body:
    type: json
    data: |-
      {
        "prompt": "A small lunar research station wakes before dawn. Slow camera drift, cinematic realism, subtle machinery and natural room tone.",
        "profileId": "minimax_h3_fp8_turbo4_landscape_832x480_v1",
        "durationSeconds": 5
      }
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

## 8. Bruno：查询、下载、取消

把 `h3_替换为任务ID` 改成创建响应的 `id`：

```yaml
info:
  name: H3 - Check job
  type: http
http:
  method: GET
  url: http://100.64.35.71:8090/v1/video-jobs/h3_替换为任务ID
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

响应中的：

- `requestedDurationSeconds` 是请求整数秒；`frameCount` 和 `actualDurationSeconds`
  是实际原生网格结果。
- `generationSubmittedAt` 是 ComfyUI 接受工作流后才写入的时间；
  `generationCompletedAt` 是观察到 ComfyUI 完成时写入的时间。
- `generationElapsedMs` 是这段后端等待时间，不含图片下载、比例处理和把 MP4
  移入网关管理目录的时间；不是精确 GPU-only 推理时间。
- 只有 `status: succeeded` 且 `outputReady: true` 才可下载。

```yaml
info:
  name: H3 - Download MP4
  type: http
http:
  method: GET
  url: http://100.64.35.71:8090/v1/video-jobs/h3_替换为任务ID/output
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

完成 MP4 保留 72 小时；SQLite 任务记录与网关临时图片最多保留 30 天。

## 9. 常见错误

| 错误码 | 原因与处理 |
| --- | --- |
| `request_body_invalid` / `request_fields_invalid` | JSON 与 multipart 混用、字段拼写错误、或携带已退休的 `idempotencyKey` |
| `image_file_required` | multipart I2V 缺少必填 `image` |
| `input_aspect_mismatch` | `reject_mismatch` 收到错误比例；先准备正确画布，或明确选择裁切/黑边策略 |
| `source_url_invalid` / `source_url_fetch_failed` | URL 不是可下载 http(s) 图片，或网络不可达 |
| `image_decode_invalid` / `unsupported_image_format` | 图像不是可解码 JPEG、PNG、WebP |
| `profile_not_supported` | 从 `/health` 复制当前 profile ID |
| `gateway_output_expired` | MP4 已超过 72 小时，不能恢复；确认需要后重新提交 |
