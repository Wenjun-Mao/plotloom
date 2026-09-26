# MiniMax-H3 网关：同事 API 使用指南

这是 Spark 上仅供团队通过 Tailscale 调用的内部视频生成 API。它不是公开服务，
也不是任意 ComfyUI 工作流代理。普通视频路径只能选择已经审核过的 `quality`
与 `resolution`；独立的声线参考路径使用固定 Ref2VA 配方。调用者不能传模型
文件、节点参数或工作流。

本文只提供 **Bruno** 示例。部署和维护请看
[H3 网关运维手册](minimax-h3-gateway-manual.md)。Qwen-Image 文生图与单图编辑
使用独立的 [Qwen-Image API 使用指南](qwen-image-gateway-client-guide.md)，不要把
图片字段或画布合同混入本视频 API。

## 1. 连接与健康检查

当前 Tailscale 基地址：

```text
http://100.64.35.71:8090
```

在 Bruno 的私密环境变量中设置（不要把真实 Key 提交到 Bruno YAML）：

```text
H3_GATEWAY_BEARER=<向团队取得当前 Key>
```

除 `/health` 外，所有接口使用：

```yaml
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

```yaml
info:
  name: H3 - Health
  type: http
http:
  method: GET
  url: http://100.64.35.71:8090/health
```

`queuedJobs` 是等待数量。H3 始终一次生成一条，队列按 FIFO 顺序执行。

## 2. 选择质量、画布和时长

每个新请求都必须有 `resolution`；`quality` 可省略，省略时为 `1`。

| `quality` | 路径 | 适用预期 |
| ---: | --- | --- |
| `1` | V1.2 Turbo-4 / Euler / 6:3 | 默认、最快的日常迭代 |
| `2` | V1.0 Turbo-4 / res_multistep / 6:3 | 另一条快速候选路径 |
| `3` | V1.0 Turbo-8 / Euler / 6:3 | 较慢的中等候选路径 |
| `8` | Base-20 / res_multistep / 原生 12:3 | 较慢的质量候选路径，不使用 Turbo LoRA |

可选 `resolution` 仅为以下精确值：

| 方向 | `resolution` | 输出尺寸 |
| --- | --- | ---: |
| 横版 | `832x480` | 832 × 480 |
| 横版 | `960x544` | 960 × 544 |
| 横版 | `1280x704` | 1280 × 704 |
| 竖版 | `576x1024` | 576 × 1024 |
| 竖版 | `608x1088` | 608 × 1088 |
| 竖版 | `704x1280` | 704 × 1280 |

`durationSeconds` 可选，默认 `5`，只接受 5–15 的整数秒。H3 使用 24 fps 和
`17k + 5` 帧格，5 秒请求为 124 帧，实际约 5.17 秒。`seed` 也可省略；服务器会
生成随机值，并在创建和状态响应中返回实际 seed。

排程前可查 [H3 视频生成时间估算表](minimax-h3-generation-time-estimates.md)：
它静态列出每种 `quality`、`resolution` 和 5–15 秒组合的粗略生成时间，
**不包含排队或图片下载时间**；网关不会返回实时预计完成时间。

## 3. 图片输入与 `aspectPolicy`

I2V 可使用 JSON 的可下载 `sourceUrl` / `endSourceUrl`，或 Bruno multipart 的
`image` / `endImage`。一次请求不能混用 URL 和文件。每张图片支持 JPEG、PNG、
WebP，最大 20 MiB、3,000 万像素。

图片不需要与输出尺寸像素完全相同，但建议具有相同宽高比。例如 1664 × 960 可用
于 `832x480`。网关会规范到最终尺寸。

| `aspectPolicy` | 比例不同怎么办 | 使用场景 |
| --- | --- | --- |
| `reject_mismatch` | 拒绝 | 默认；先完成正确构图 |
| `contain_pad` | 等比缩小并补黑边 | 明确想保留黑边的画面 |
| `cover_center_crop` | 中心裁切再缩放 | 已审核中央裁切安全的图片 |

横图使用 `contain_pad` 放进竖画布时通常有上下黑边；它不是自动扩图功能。若目标
是原生竖版空间，应先准备匹配竖版的起始图并使用 `reject_mismatch`。

## 4. 接口一览

| 方法 | 用途 |
| --- | --- |
| `GET /health` | 服务、ComfyUI、质量/尺寸合同与队列检查，无需 Bearer |
| `POST /v1/video-jobs/from-image` | 起始图必填、末帧可选的 I2V |
| `POST /v1/video-jobs/from-image-with-voice` | 起始图 + 短声线参考音频；固定 Ref2VA Base-20 |
| `POST /v1/video-jobs/from-text` | 仅探索用途的 T2V，不是 Plotloom 创作模式 |
| `GET /v1/video-jobs/{id}` | 查询状态、seed、帧数和生成计时 |
| `GET /v1/video-jobs/{id}/output` | 下载完成 MP4 |
| `POST /v1/video-jobs/{id}/cancel` | 仅取消 `queued` 任务 |

没有 `profileId`、`assetId` 或 `idempotencyKey`。发送后 Bruno 超时不要盲目重试：
任务可能已经入队。

## 5. Bruno：URL 起始图与末帧 I2V

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
        "quality": 8,
        "resolution": "576x1024",
        "aspectPolicy": "reject_mismatch",
        "seed": 42,
        "durationSeconds": 8
      }
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

省略 `endSourceUrl` 即为普通起始图 I2V。省略 `quality` 时使用默认质量 1。

## 6. Bruno：本地文件 I2V

在 Bruno 选择 **Body → Multipart Form**，不要手写 `Content-Type`。

| 字段 | 类型 | 值 |
| --- | --- | --- |
| `image` | File | 必填，起始图 |
| `endImage` | File | 可选，末帧 |
| `prompt` | Text | 必填 |
| `quality` | Text | 可选；`1`、`2`、`3` 或 `8` |
| `resolution` | Text | 必填；上表任一精确值 |
| `aspectPolicy` | Text | 必填；上表任一值 |
| `seed` | Text | 可选整数 |
| `durationSeconds` | Text | 可选 5–15 整数 |

请求地址：`POST http://100.64.35.71:8090/v1/video-jobs/from-image`。

## 7. Bruno：T2V 探索

T2V 仅用于独立试验；它不进入 Plotloom 作者工作台。它只能用 JSON，且不接受图像
或 `aspectPolicy`：

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
        "quality": 1,
        "resolution": "832x480",
        "durationSeconds": 5
      }
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

## 7A. Bruno：起始图 + 声线参考（Ref2VA）

这个路径与上面的 `quality=8` **不是同一个模型**。它固定使用 Ref2VA
Base-20，返回状态为 `inputMode: image_voice`、`quality: 8`；请求中**不能**传
`quality`、末帧或 `profileId`。当前只接受 `960x544` 横版和 `576x1024`
原生竖版；`durationSeconds` 可省略（默认 5），仅接受 5–8 的整数。

音频必须是 **PCM16、单声道、32 kHz 的 WAV**，长度 1–10 秒且不超过 2 MiB。
网关不会裁剪或转码。它是人物声音音色与表演节奏的参考，**不是**要复制的
台词/声音轨；目标对白仍应明确写进 `prompt`。同一人物的声音和唇形都需要
看片人工审核，不能仅凭生成成功认定一致。

在 Bruno 新建 POST 请求到
`http://100.64.35.71:8090/v1/video-jobs/from-image-with-voice`，选择
**Body → Multipart Form**，不要手写 `Content-Type`：

| 字段 | 类型 | 值 |
| --- | --- | --- |
| `image` | File | 必填，已构图的第一帧；竖版建议真正的 576×1024 画面 |
| `voiceAudio` | File | 必填，符合上述 PCM WAV 合同的声线参考 |
| `prompt` | Text | 必填；写明谁说话、何时说、准确的目标台词和画面动作 |
| `resolution` | Text | `960x544` 或 `576x1024` |
| `aspectPolicy` | Text | 建议 `reject_mismatch`；另可显式选择第 3 节的裁切/黑边策略 |
| `seed` | Text | 可选；省略后网关随机生成并回显 |
| `durationSeconds` | Text | 可选，5–8；默认 5 |

一个可直接填入 Bruno `prompt` 的试验例子（图片与 WAV 请换成自己已审核的文件）：

```text
<Picture 1> is the exact first frame. <Audio 1> is the speaker's voice-timbre
and delivery reference, not target dialogue. One continuous cinematic shot,
locked camera, face and mouth visible. She speaks once in Mandarin within the
first second: <d>[Chinese] 一枚，只够一边。</d> No subtitles, no repeated speech.
```

也可使用 JSON 的两个可下载地址；一次请求不能同时传 URL 和文件：

```yaml
info:
  name: H3 - Image with voice reference from URLs
  type: http
http:
  method: POST
  url: http://100.64.35.71:8090/v1/video-jobs/from-image-with-voice
  headers:
    - name: Content-Type
      value: application/json
  body:
    type: json
    data: |-
      {
        "sourceUrl": "https://example.internal/reviewed-first-frame.png",
        "voiceSourceUrl": "https://example.internal/reviewed-voice-32k-mono.wav",
        "prompt": "One continuous shot from <Picture 1>. <Audio 1> is voice timbre only. She says once: <d>[Chinese] 一枚，只够一边。</d> No subtitles.",
        "resolution": "576x1024",
        "aspectPolicy": "reject_mismatch",
        "durationSeconds": 5
      }
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

创建响应额外给出一次性的 `voiceReferenceSha256`：它是提交的原始 WAV 字节的
SHA-256，供调用方比对自己的候选音频。后续普通状态不重复这个哈希，也不返回
音频、URL 或私有路径。网关只保存这个任务的参考音频，不提供声线 ID 或声线库。
Plotloom 若接入，将自己管理人物的稳定 Voice ID 和候选音频；网关 72 小时视频
与最多 30 天任务/输入清理不应作为 Plotloom 声音素材的保留政策。

## 8. 查询与下载

将 `h3_替换为任务ID` 换成创建响应的 `id`：

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

响应的 `generationElapsedMs` 从 ComfyUI 接受工作流到观察到完成，不含下载图片、
比例处理和移入网关目录。仅 `status: succeeded` 且 `outputReady: true` 可下载。

完成 MP4 保留 72 小时；SQLite 任务记录与网关上传图片最多保留 30 天。

## 9. 常见错误

| 错误码 | 原因与处理 |
| --- | --- |
| `request_body_invalid` / `request_fields_invalid` | JSON 与 multipart 混用、字段拼写错误或重复字段 |
| `request_invalid` | 请求含 `profileId`、`assetId`、`idempotencyKey` 或不属于该路由的字段 |
| `quality_not_supported` | 只可使用 `1`、`2`、`3`、`8` |
| `resolution_not_supported` | 使用上表中的精确 `resolution` |
| `image_file_required` | multipart I2V 缺少 `image` |
| `voice_file_required` / `voice_format_not_supported` | 声线参考缺失，或不是 32 kHz 单声道 PCM16 WAV |
| `voice_size_invalid` / `voice_duration_invalid` | 声线参考超出 2 MiB 或 1–10 秒 |
| `voice_resolution_not_supported` / `voice_duration_not_supported` | Ref2VA 仅支持上文两个画布与 5–8 秒 |
| `comfy_voice_profile_unavailable` | Ref2VA 模型或节点尚未就绪；请联系 Spark 运维，不要反复提交 |
| `input_aspect_mismatch` | 先准备正确画布，或明确选择裁切/黑边策略 |
| `source_url_invalid` / `source_url_fetch_failed` | URL 不是可下载 http(s) 图片，或网络不可达 |
| `gateway_output_expired` | MP4 已超过 72 小时，需要重新提交 |
