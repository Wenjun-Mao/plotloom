# MiniMax-H3 网关：同事 API 使用指南

这是 Spark 上仅供团队通过 Tailscale 调用的内部视频生成 API。它不是公开服务，
也不是任意 ComfyUI 工作流代理。普通视频路径只能选择已经审核过的 `quality`
与 `resolution`；声线参考与有序多图两条路径使用各自固定的 Ref2VA 合同。调用者不能传模型
文件、节点参数或工作流。

本文提供 **Bruno 和 curl** 示例；第 7B 节完整介绍 1–9 张有序参考图。部署和维护请看
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

curl 示例使用 shell 环境中的 `H3_GATEWAY_BEARER`，需从受保护的私密环境提供；
Bruno 的变量不会自动成为 shell 变量。另设置非秘密的基地址：

```sh
export H3_BASE=http://100.64.35.71:8090
curl --fail-with-body "$H3_BASE/health"
```


## 2. 选择质量、画布和时长

普通 FL2VA 请求必须有 `resolution`；`quality` 可省略，省略时为 `1`。
两种 Ref2VA 路径使用第 7A、7B 节的独立字段与尺寸合同。

选择输入方式：起始/末帧用第 5、6 节；第一帧加声线 WAV 用第 7A 节；
有序的 1–9 张图与毫秒时间点用第 7B 节；纯文本探索用第 7 节。

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
| `reject_mismatch` | 拒绝 | 普通 I2V 默认；先完成正确构图。多图路由须显式填写 |
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
| `POST /v1/video-jobs/from-reference-images` | 1–9 张有序静态参考图 + 毫秒时间点；固定 Ref2VA Base-20 |
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
音频、URL 或私有路径。视频接口只接收此任务的 WAV，不解析 Voice ID 或 Take ID。
现在可先用独立的 [台词表演 API](../../services/qwen3_tts_voice_lab/docs/voice-takes-client-guide.md)
生成、试听并下载 H3 WAV；再作为 `voiceAudio` 上传。声线和表演由 Voice Lab
长期保存，重新生成不覆盖旧结果；全部生成共享 FIFO。
Plotloom 若接入，将自己管理人物的稳定选择和保留副本；网关 72 小时视频
与最多 30 天任务/输入清理不应作为 Plotloom 声音素材的保留政策。

## 7B. 有序参考图与时间点（Ref2VA）

请求地址为 `POST /v1/video-jobs/from-reference-images`，接受 **1–9 张有序
静态图片、每张图片的毫秒时间点和原始提示词**，可选再提供 **1–3 个角色声线 WAV**，输出带原生音频的 MP4。
使用第 1 节的基地址和 Bearer；本节完整覆盖本地上传、URL 和时间 readback。

`/health` 无需 Bearer。关注 `referenceContractVersion`、
`referenceImagesReady`、`referenceMaxImages`、`referenceResolutions` 和
`referenceDurationMs`。可选声线另看 `referenceAudioReady`、`referenceMaxAudios`、
`referenceAudioContractVersion` 和 `referenceAudioFormat`；它不改变图片分支的就绪。
就绪检查节点、模型和输入插槽合同；显存容量、实际生成时间和成片效果以实际
运行结果为准。[已有的学习运行验证](../verification/2026-11-07-h3-ordered-reference-images.md)
覆盖一次五图、277 帧请求，不代表所有九图/时长组合均已验证。

### 7B.1. 请求字段与限制

| 字段 | 是否必填 | 合同 |
| --- | --- | --- |
| `prompt` | 是 | 1–8000 字符，原样传入 H3 |
| `resolution` | 是 | 仅 `960x544` 或 `576x1024` |
| `aspectPolicy` | 是 | 显式填写 `reject_mismatch`、`contain_pad` 或 `cover_center_crop` |
| `durationMs` | 是 | 5000–15000 的整数毫秒，例如 11300；本路由使用毫秒 |
| `seed` | 否 | 0–9223372036854775807 的整数；省略后由服务生成并回显 |
| `references` | 是 | 1–9 项有序数组，格式依 JSON URL / 本地上传方式而异 |
| `audioReferences` | 否 | 0–3 项角色声线；省略或 `[]` 保持原图片模式，`null` 拒绝；见 7B.5 |

固定使用 **Ref2VA Base-20**，响应中的 `quality` 为 `8`。它与普通 FL2VA 的
`quality=8` 是不同模型路径。请求字段严格校验：`quality`、`durationSeconds`、
旧路由的 `voiceAudio`、起始/末帧字段、模型和工作流参数均不属于此路由。

图片需满足：

- JPEG、PNG 或 WebP，每张为不透明单帧；透明像素和动画会被拒绝。
- 全部原始图片**合计不超过 20 MiB**；每张最多 3000 万像素。
- 需要保留完整构图时可显式选择 `contain_pad`，服务会等比缩放并补黑边。
  `cover_center_crop` 会中心裁切；`reject_mismatch` 要求输入宽高比与目标匹配。
  比例按 EXIF 方向修正后的图片计算，允许的绝对比例差为 0.001。

顺序对应 `<Picture 1>`、`<Picture 2>`……。每张图进入相应的参考编码槽位，
并在自己的时间点提供一帧画面引导，因此应为每张图指定它要引导的画面与时间。
文件名不决定顺序。需要切镜时，还应在 `prompt` 中明确描述切镜；实际成片以
输出为准。

每项 `atMs` 为非负整数毫秒，第一项必须为 `0`，后续严格递增且小于
`durationMs`。服务按最近的 24 fps 帧取整，恰好半帧向上取整；取整后仍须
各占不同的递增帧。例如 `0` 和 `1` ms 都会落在第 0 帧，会被拒绝。
总长度向上吸附到原生 `17k+5` 帧格，播放时长可能长于请求时长。
取整后的每个 `frameIndex` 还必须小于实际 `frameCount`。例如请求 5166 ms、
参考时间 5165 ms 虽早于请求结束，却会落到第 124 帧，而输出只有 124 帧
（索引 0–123），因此也会被拒绝。

### 7B.2. Bruno / curl：上传本地参考图

新建 POST，请求地址：

```text
http://100.64.35.71:8090/v1/video-jobs/from-reference-images
```

选择 **Body → Multipart Form**。以下例子有五张图片：

| 字段名 | 类型 | 内容 |
| --- | --- | --- |
| `request` | Text | 下面完整的 JSON，只填一个字段 |
| `images` | File | 第 1 张图片 |
| `images` | File | 第 2 张图片 |
| `images` | File | 第 3 张图片 |
| `images` | File | 第 4 张图片 |
| `images` | File | 第 5 张图片 |

所有文件字段都叫 **`images`**，按与 `references` 相同的顺序排列。
Bruno 自动生成带 boundary 的 `Content-Type`。提示词、时间和其他参数全部放进
`request`，而不是额外的表单字段。上传模式的每项参考信息只填写 `atMs`：

```json
{
  "prompt": "<Picture 1> establishes the room. Follow <Picture 2>, <Picture 3>, <Picture 4>, then <Picture 5>. Natural motion and room tone.",
  "resolution": "960x544",
  "aspectPolicy": "contain_pad",
  "durationMs": 11300,
  "seed": 42,
  "references": [
    {"atMs": 0},
    {"atMs": 2500},
    {"atMs": 4500},
    {"atMs": 6800},
    {"atMs": 9000}
  ]
}
```

一张图时只留首项 `atMs: 0` 和一个文件；增加到九张时，为每个新增文件增加一项
合法时间。数组项数和文件数必须相同，表单字段仍重复使用 `images`。

将上述 JSON 保存为 `reference-upload.json`，等价 curl 为：

```sh
curl --fail-with-body "$H3_BASE/v1/video-jobs/from-reference-images" \
  -H "Authorization: Bearer $H3_GATEWAY_BEARER" \
  --form-string "request=$(cat reference-upload.json)" \
  -F 'images=@1.png;type=image/png' \
  -F 'images=@2.png;type=image/png' \
  -F 'images=@3.png;type=image/png' \
  -F 'images=@4.png;type=image/png' \
  -F 'images=@5.png;type=image/png'
```

示例文件名、图片和提示词需换成实际素材；这段命令会创建真实任务。

### 7B.3. Bruno / curl：可下载图片 URL

使用相同 POST 地址，Bruno 选择 JSON Body。每个数组项同时给出 `sourceUrl`
和 `atMs`，不附加上传文件。URL 必须是 Spark 能下载的绝对 HTTP(S) 地址，
最多 2048 字符；它不是你电脑上的文件路径。替换下面的占位 URL：

```json
{
  "prompt": "<Picture 1> establishes the room. Follow <Picture 2>, <Picture 3>, <Picture 4>, then <Picture 5>. Natural motion and room tone.",
  "resolution": "960x544",
  "aspectPolicy": "contain_pad",
  "durationMs": 11300,
  "seed": 42,
  "references": [
    {"sourceUrl": "https://example.internal/1.png", "atMs": 0},
    {"sourceUrl": "https://example.internal/2.png", "atMs": 2500},
    {"sourceUrl": "https://example.internal/3.png", "atMs": 4500},
    {"sourceUrl": "https://example.internal/4.png", "atMs": 6800},
    {"sourceUrl": "https://example.internal/5.png", "atMs": 9000}
  ]
}
```

保存为 `reference-urls.json`：

```sh
curl --fail-with-body "$H3_BASE/v1/video-jobs/from-reference-images" \
  -H "Authorization: Bearer $H3_GATEWAY_BEARER" \
  -H 'Content-Type: application/json' \
  --data-binary @reference-urls.json
```

URL 在接纳请求时下载，图片合计仍限 20 MiB；URL 本身不进入持久化的执行快照。

### 7B.4. 接收任务与时间 readback

接纳成功返回 **HTTP 202** 和任务 `id`。保存这个 ID：创建任务没有幂等键，
超时后直接重复 POST 可能创建第二个任务。若尚未收到 ID，应先联系运维核对；
已有 ID 时只查询该任务。

响应及后续 GET 保留普通任务字段，并增加：

| 字段 | 含义 |
| --- | --- |
| `inputMode` | `reference_images` |
| `referenceContractVersion` | 参考图合同版本，当前为 `1` |
| `requestedDurationMs` | 原始请求毫秒数 |
| `promptSha256` | 原始 UTF-8 提示词的 SHA-256 |
| `references` | 有序的 `index`、`atMs`、`frameIndex`、`effectiveTimeSeconds`、`sourceSha256`、`preparedSha256` |

本例 `requestedDurationSeconds` 为 `11.3`，`frameCount` 为 `277`，
`actualDurationSeconds` 为 `277 / 24 ≈ 11.541667`：

| 图片 | `atMs` | `frameIndex` | `effectiveTimeSeconds`（约） |
| --- | ---: | ---: | ---: |
| 1 | 0 | 0 | 0 |
| 2 | 2500 | 60 | 2.5 |
| 3 | 4500 | 108 | 4.5 |
| 4 | 6800 | 163 | 6.791667 |
| 5 | 9000 | 216 | 9 |

后续使用第 8 节的共享查询、下载与取消接口。参考元数据若为 `null` 或出现输入
完整性错误，保留已知任务 ID 并联系运维；生命周期状态仍可读取。

### 7B.5. 可选的多角色声线

同一请求可增加 `audioReferences`。每项 `speaker` 是调用方自定且唯一的
非空标签（1–128 字符，不带首尾空白/控制字符）。第 1 项对应 `<Audio 1>`，
第 2、3 项依此类推。标签用于追溯；**提示词仍须明确写出哪个角色使用哪个
`<Audio n>`**。网关不改写提示词，也不强制模型正确分配角色声音。

每个 WAV 必须为 **PCM16、单声道、32 kHz、1–10 秒、最多 2 MiB**，
最多三份合计 6 MiB，与图片的 20 MiB 限制分开。不会自动裁剪、重采样、
丢弃或合并参考。使用稳定的单角色声音片段，跨请求复用同一文件。
可下载 Voice Lab 已有的 H3 合格 WAV，再作为本请求文件；这里不接收 Voice/Take ID。

在第 7B.2 节的 `request` JSON 中增加：

```json
{"audioReferences": [{"speaker":"角色甲"},{"speaker":"角色乙"}]}
```

Bruno 的 Multipart Form 中，保留一个 `request` 文本及原有多个 `images`
文件，再按上述数组顺序添加两个同名 `audios` File 字段。声线不带 `atMs`。
例如完整上传请求可写成（`request-with-audio.json` 包含原有全部必填字段）：

```sh
curl --fail-with-body -sS \
  -H "Authorization: Bearer $H3_GATEWAY_BEARER" \
  -F 'request=<request-with-audio.json;type=application/json' \
  -F 'images=@reference-1.png' \
  -F 'images=@reference-2.png' \
  -F 'audios=@character-a.wav;type=audio/wav' \
  -F 'audios=@character-b.wav;type=audio/wav' \
  http://100.64.35.71:8090/v1/video-jobs/from-reference-images
```

元数据示例（台词与角色映射应换成实际创作内容）：

```json
{
  "prompt": "<Picture 1> establishes the scene. The woman uses <Audio 1>; the man uses <Audio 2>. The woman says <d>[Chinese] 窗户已经关好了。</d> The man replies <d>[Chinese] 那我们现在出发。</d>",
  "resolution": "960x544",
  "aspectPolicy": "contain_pad",
  "durationMs": 8000,
  "references": [{"atMs":0},{"atMs":4000}],
  "audioReferences": [{"speaker":"角色甲"},{"speaker":"角色乙"}]
}
```

URL 模式保留第 7B.3 节的图片 `sourceUrl`，每个声线项改为
`{"speaker":"角色甲","sourceUrl":"https://your-private-source/character-a.wav"}`。
一次请求统一使用 URL 或上传模式；上传元数据不能夹带 `sourceUrl`。
鉴权规则与图片 URL 相同，网关不会将 Bearer 转发给源服务器。

音频请求的创建/GET 额外返回 `referenceAudioContractVersion:1` 和有序
`audioReferences`，每项含 `index`、`speaker`、`sourceSha256`、
`preparedSha256`、`sourceSizeBytes`、`durationMs`。原始与规范 WAV 头的 hash
可能不同；不回显 URL、私有文件名或音频字节。看板任务详情也展示这份映射。
图片模式不新增这些响应字段，提示词、图片顺序和时间取整规则均不变。

参考音频用于引导新生成的声音，不是精确复制、配音或跨镜头声线一致性的保证。
[当前验证](../verification/2026-11-16-h3-optional-reference-audio.md)已通过两个三图/三声线的 8 秒请求，以及一个九图/三声线的 5 秒请求；不代表所有最大时长组合。实际声线身份与台词分配尚未完成听感判断。

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

等价 curl（`H3_JOB_ID` 使用创建响应的实际 `id`）：

```sh
H3_JOB_ID=h3_替换为任务ID
curl --fail-with-body "$H3_BASE/v1/video-jobs/$H3_JOB_ID" \
  -H "Authorization: Bearer $H3_GATEWAY_BEARER"
```

`POST /v1/video-jobs/{id}/cancel` 只可取消仍在 `queued` 的任务。
`outcome_unknown` 应联系运维核对现有任务，不要重发创建请求。

响应的 `generationElapsedMs` 从 ComfyUI 接受工作流到观察到完成，不含下载图片、
比例处理和移入网关目录。仅 `status: succeeded` 且 `outputReady: true` 可下载。

下载示例（`H3_JOB_ID` 使用创建响应的 `id`）：

```sh
curl --fail-with-body "$H3_BASE/v1/video-jobs/$H3_JOB_ID/output" \
  -H "Authorization: Bearer $H3_GATEWAY_BEARER" --output result.mp4
```

完成 MP4 保留 72 小时；SQLite 任务记录与网关上传图片最多保留 30 天。

## 9. 常见错误

网关校验错误通常返回 `{"error":"错误码"}`；鉴权失败为 HTTP 401。
multipart 解析层的数量/大小限制也可能直接返回框架错误。

| 错误码 | 原因与处理 |
| --- | --- |
| `request_body_invalid` / `request_fields_invalid` | JSON 与 multipart 混用、字段拼写错误或重复字段 |
| `request_invalid` | 请求含 `profileId`、`assetId`、`idempotencyKey` 或不属于该路由的字段 |
| `quality_not_supported` | 普通 FL2VA 只可使用 `1`、`2`、`3`、`8`；多图请求不传 `quality` |
| `resolution_not_supported` | 使用上表中的精确 `resolution` |
| `image_file_required` | multipart I2V 缺少 `image` |
| `reference_audio_count_mismatch` / `reference_request_invalid` | 多角色声线文件与元数据数量不匹配，或标签/字段不合法 |
| `reference_audio_integrity_mismatch` / `reference_audio_snapshot_mismatch` | 已接纳声线的文件或映射与冻结记录不一致；保留任务 ID，联系运维 |
| `voice_file_required` / `voice_format_not_supported` | 声线参考缺失，或不是 32 kHz 单声道 PCM16 WAV |
| `voice_size_invalid` / `voice_duration_invalid` | 声线参考超出 2 MiB 或 1–10 秒 |
| `voice_resolution_not_supported` / `voice_duration_not_supported` | 单图加声线路由仅支持上文两个画布与 5–8 秒；多图使用 5000–15000 ms |
| `comfy_voice_profile_unavailable` | Ref2VA 模型或节点尚未就绪；请联系 Spark 运维，不要反复提交 |
| `reference_request_invalid` | 多图字段、类型、时间或量化帧越界/碰撞不合法；也包括 `quality`、`durationSeconds` 等额外字段 |
| `reference_request_fields_invalid` | 多图表单须恰有一个 `request` 和同名 `images` 文件字段 |
| `reference_image_count_mismatch` / `reference_image_file_required` | 文件数须等于参考数组项数，且 `images` 必须为 File |
| `reference_images_size_invalid` / `image_size_invalid` | 多图输入不能为空，全部参考图合计不得超过 20 MiB |
| `source_url_too_large` | URL 下载的图片超过剩余合计字节限制 |
| `image_decode_invalid` / `unsupported_image_format` / `image_pixels_exceed_limit` | 检查实际文件格式、损坏和像素数 |
| `reference_image_must_be_single_still` / `reference_image_transparency_not_supported` | 需要不透明的单帧图片 |
| `comfy_reference_profile_unavailable` | 有序参考图的模型/节点合同不可用，请联系运维 |
| `input_aspect_mismatch` | 先准备正确画布，或明确选择裁切/黑边策略 |
| `source_url_invalid` / `source_url_fetch_failed` | URL 不是可下载 http(s) 图片，或网络不可达 |
| `gateway_output_expired` | MP4 已超过 72 小时，需要重新提交 |
