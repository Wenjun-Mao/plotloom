# MiniMax-H3：1–9 张有序参考图 API 使用指南

适用于团队通过 Tailscale 直接调用
`POST /v1/video-jobs/from-reference-images`。输入是 **1–9 张有序静态图片、
每张图片的毫秒时间点和原始提示词**，输出是一条带原生音频的 MP4。
普通起始/末帧 I2V、单图加声线参考和 T2V 请看
[H3 总指南](minimax-h3-gateway-client-guide.md)。

合同核对日期：2026-11-16。当天只读 `/health` 返回
`referenceImagesReady: true`、`referenceMaxImages: 9`；实际调用前以服务当前响应为准。

## 1. 连接、授权和就绪

基地址为 `http://100.64.35.71:8090`。在 Bruno 私密环境中设置
`H3_GATEWAY_BEARER`；请求使用 Bearer Auth，值为 `{{H3_GATEWAY_BEARER}}`。
不要把真实 Key 写进共享请求文件。

curl 使用相同的私密环境变量，另设置非秘密的基地址：

```sh
export H3_BASE=http://100.64.35.71:8090
curl --fail-with-body "$H3_BASE/health"
```

`/health` 无需 Bearer。关注 `referenceContractVersion`、
`referenceImagesReady`、`referenceMaxImages`、`referenceResolutions` 和
`referenceDurationMs`。本路由的就绪与 `voiceReferenceReady` 分开。
就绪检查节点、模型和输入插槽合同；显存容量、实际生成时间和成片效果以实际
运行结果为准。[已有的学习运行验证](../verification/2026-11-07-h3-ordered-reference-images.md)
覆盖一次五图、277 帧请求，不代表所有九图/时长组合均已验证。

## 2. 请求字段与限制

| 字段 | 是否必填 | 合同 |
| --- | --- | --- |
| `prompt` | 是 | 1–8000 字符，原样传入 H3 |
| `resolution` | 是 | 仅 `960x544` 或 `576x1024` |
| `aspectPolicy` | 是 | 显式填写 `reject_mismatch`、`contain_pad` 或 `cover_center_crop` |
| `durationMs` | 是 | 5000–15000 的整数毫秒，例如 11300；本路由使用毫秒 |
| `seed` | 否 | 0–9223372036854775807 的整数；省略后由服务生成并回显 |
| `references` | 是 | 1–9 项有序数组，格式依 JSON URL / 本地上传方式而异 |

固定使用 **Ref2VA Base-20**，响应中的 `quality` 为 `8`。它与普通 FL2VA 的
`quality=8` 是不同模型路径。请求字段严格校验：`quality`、`durationSeconds`、
声线音频、起始/末帧字段、模型和工作流参数均不属于此路由。

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

## 3. Bruno：上传本地参考图

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

## 4. Bruno / curl：使用可下载图片 URL

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

## 5. 接收任务、核对时间并下载

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

使用创建响应的实际 `id`：

```sh
H3_JOB_ID=h3_替换为任务ID
curl --fail-with-body "$H3_BASE/v1/video-jobs/$H3_JOB_ID" \
  -H "Authorization: Bearer $H3_GATEWAY_BEARER"
```

仅 `status: succeeded` 且 `outputReady: true` 时下载：

```sh
curl --fail-with-body "$H3_BASE/v1/video-jobs/$H3_JOB_ID/output" \
  -H "Authorization: Bearer $H3_GATEWAY_BEARER" --output result.mp4
```

`POST /v1/video-jobs/{id}/cancel` 只可取消仍在 `queued` 的任务。
`outcome_unknown` 应交给运维核对现有任务，不能用重发来解决。
`generationElapsedMs` 是提交后到观察到完成的计时，不包含输入下载/准备或最终
文件移交。完成视频保留 72 小时；任务和暂存输入最多保留 30 天，请及时保存所需输出。

## 6. 常见错误

网关校验错误通常返回 `{"error":"错误码"}`。鉴权失败为 HTTP 401；
multipart 解析层的数量/大小限制也可能直接返回框架错误。

| 错误码 | 检查内容 |
| --- | --- |
| `reference_request_invalid` | 字段、类型、时间顺序或量化碰撞不合法；也包括 `quality`、`durationSeconds` 等额外字段 |
| `reference_request_fields_invalid` | 表单须恰有一个 `request` 和同名 `images` 文件字段 |
| `reference_image_count_mismatch` / `reference_image_file_required` | 文件数须等于数组项数，且 `images` 必须为 File |
| `reference_images_size_invalid` / `image_size_invalid` | 图片不能为空，合计不得超过 20 MiB |
| `source_url_too_large` | URL 下载的图片超过剩余合计字节限制 |
| `reference_image_must_be_single_still` / `reference_image_transparency_not_supported` | 去掉动画或透明像素，提供不透明单帧图片 |
| `image_decode_invalid` / `unsupported_image_format` / `image_pixels_exceed_limit` | 检查实际文件格式、损坏和像素数 |
| `input_aspect_mismatch` | 准备匹配画布的图片，或明确选择裁切/补黑边策略 |
| `source_url_fetch_failed` | 检查 Spark 对图片地址的访问及实际下载内容 |
| `comfy_reference_profile_unavailable` | 联系运维检查此路由的节点、模型和参考插槽合同 |

若状态中的参考元数据变为 `null` 或出现输入完整性错误，保留已知 ID 并交给运维
处理；已有任务的生命周期状态仍可读取。更多维护、恢复和保留规则见
[运维手册](minimax-h3-gateway-manual.md)。
