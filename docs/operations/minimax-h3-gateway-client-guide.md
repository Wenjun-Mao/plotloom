# MiniMax-H3 网关：同事 API 使用指南

这是一个在 Spark 上运行、仅供团队通过 Tailscale 使用的内部 API：输入一张
关键帧和动作提示词，生成约 5 秒的 MiniMax-H3 视频。它不是公开服务，也不是
任意 ComfyUI 工作流的代理。

本文面向调用者。部署、模型和运维变更请看
[H3 网关运维手册](minimax-h3-gateway-manual.md)。

## 1. 连接与鉴权

先连接团队的 Tailscale 网络。当前网关基地址为：

```text
http://100.64.35.71:8090
```

Bearer Key 请通过团队约定的私密渠道取得；不要把它写入 URL、提交到仓库、截图
或贴进共享聊天记录。以下示例将它保存在当前 shell 的环境变量中：

```sh
export H3_GATEWAY_BASE_URL='http://100.64.35.71:8090'
export H3_GATEWAY_API_KEY='向团队取得当前 Key'
export H3_AUTH="Authorization: Bearer ${H3_GATEWAY_API_KEY}"
```

先检查服务和模型目录是否可用。`/health` 不需要 Bearer Key，且可安全分享：

```sh
curl --fail --silent --show-error "${H3_GATEWAY_BASE_URL}/health"
```

它会返回当前 profile 列表、队列长度和固定并发数。以下表格是本文版本的目录；
实际调用前以 `/health` 返回的 `profiles` 为准。

## 2. 可选视频规格（`profileId`）

每个当前可选 profile 固定生成 124 帧、24 fps、约 5.17 秒、H.264/AAC 的 MP4。
不能在请求中自定义分辨率、时长或 ComfyUI 图。

| 方向 / 用途 | 输出尺寸 | `profileId` | 建议的同宽高比输入例子 |
| --- | ---: | --- | --- |
| 横版 · 快速试稿 | 832 × 480 | `minimax_h3_fp8_turbo4_landscape_832x480_v1` | 1664 × 960 |
| 横版 · 标准 | 960 × 544 | `minimax_h3_fp8_turbo4_landscape_960x544_v1` | 1920 × 1088 |
| 横版 · 高分辨率 | 1280 × 704 | `minimax_h3_fp8_turbo4_landscape_1280x704_v1` | 2560 × 1408 |
| 竖版 · 快速试稿 | 576 × 1024 | `minimax_h3_fp8_turbo4_portrait_576x1024_v1` | 1152 × 2048 |
| 竖版 · 标准 | 608 × 1088 | `minimax_h3_fp8_turbo4_portrait_608x1088_v1` | 1216 × 2176 |
| 竖版 · 高分辨率 | 704 × 1280 | `minimax_h3_fp8_turbo4_portrait_704x1280_v1` | 1408 × 2560 |

“同宽高比”不等于“必须相同像素数”。例如 1152 × 2048 的图片可用于
576 × 1024 profile；网关会高质量缩放到该 profile 的准确尺寸。重要的是宽高比。

`profileId` 是每个新任务的必填字段；省略它不会使用任何“旧默认值”，而是直接
返回 422。新请求只能选择上表六项之一。

### 横版还是竖版？

- 做手机全屏短视频：从 `576 × 1024` 开始；确认构图后，可升到
  `704 × 1280`。
- 做桌面、电视或 16:9 风格内容：从 `832 × 480` 开始；确认后，可升到
  `1280 × 704`。
- `960 × 544`、`608 × 1088` 是中间档。它们不是标准的 16:9 或 9:16，故关键帧
  最好按照表中的准确宽高比预先制作。

## 3. 图片输入要求与比例策略（`aspectPolicy`）

### 通用图片要求

- 支持实际解码后为 **JPEG、PNG 或 WebP** 的图片；扩展名和 HTTP 的
  `Content-Type` 不能代替内容校验。
- 单张最大 **20 MiB**、最大 **3,000 万像素**。
- 可直接上传图片 bytes，也可提供 `http://` 或 `https://` 的可下载图片 URL；
  内部/Tailnet URL 可以使用。
- `sourceUrl` 最多跟随 3 次跳转，连接超时 5 秒、读取超时 20 秒。URL 本身不会
  被网关保存。

先在图片工具中按目标 profile 制作准确画布和构图，是得到稳定画面的首选方式。
网关只负责准备输入，不能替代构图审核。

### 三种 `aspectPolicy`

| 值 | 输入比例不一致时 | 何时使用 | 主要代价 |
| --- | --- | --- | --- |
| `reject_mismatch` | 立即返回 `input_aspect_mismatch`，**不排队、不生成** | 默认且推荐；关键帧已经按目标画布制作 | 调用前必须准备匹配比例的图 |
| `contain_pad` | 等比例缩放，剩余区域补黑边；输出仍是目标尺寸 | 有意保留完整横图/竖图，且明确接受信箱黑边 | H3 可能把黑边当成画面的一部分，导致竖版扩展不稳定 |
| `cover_center_crop` | 从中央裁切后缩放到目标尺寸 | 仅在已审核“中央裁切”安全的旧工作流中使用 | 主体、字幕或边缘信息可能被裁掉 |

`reject_mismatch` 接受宽高比非常接近目标的图（误差不超过 0.001），但不要求
图片的像素尺寸刚好等于输出尺寸。比例不一致时：

- 横图做竖版并选 `contain_pad`：通常会在**上、下**出现黑边；这正是之前竖版
  测试中看到的效果。
- 竖图做横版并选 `contain_pad`：通常会在**左、右**出现黑边。
- 选 `cover_center_crop`：没有黑边，但会裁掉较长方向两端内容。
- 想让模型生成真正的竖版空间，而非把横图塞进竖画布：应先生成或编辑一张匹配
  竖版 profile 的关键帧，再用 `reject_mismatch`。

`contain_pad` 是“明确允许黑边”的开关，而不是让网关猜测应如何扩图的自动模式。

## 4. API 速查

所有 `/v1/…` 路由都需要 `Authorization: Bearer …`；只有 `/health` 不需要。

| 方法和路径 | 用途 | 是否会生成视频 |
| --- | --- | --- |
| `GET /health` | 检查服务、目录和队列 | 否 |
| `POST /v1/assets` | 上传一张图片，或从 `sourceUrl` 保存图片 | 否 |
| `POST /v1/video-jobs/from-image` | 一步：下载/上传图片并排队生成 | 是 |
| `POST /v1/video-jobs` | 两步：使用已有 `assetId` 排队生成 | 是 |
| `GET /v1/video-jobs/{id}` | 查询任务状态 | 否 |
| `GET /v1/video-jobs/{id}/output` | 下载已完成 MP4 | 否 |
| `POST /v1/video-jobs/{id}/cancel` | 取消仍处于 `queued` 的任务 | 否 |

H3 一次只生成一个视频。任务按 FIFO 排队，队列没有人为长度上限。

## 5. 最简单的一步生成：图片 URL → 视频任务

这是最适合 Bruno、脚本或一次性试验的接口。**请求成功返回 `queued` 就表示会
消耗一次 H3 生成机会**。保存返回的 `id`，后续用它查询和下载。

以下公开 Plotloom 图片可作为无敏感信息的测试源。它并非任何 profile 的精确宽高
比，因此示例刻意使用 `contain_pad`；真实项目建议换成符合目标 profile 的关键帧
并使用 `reject_mismatch`。

```sh
export H3_TEST_IMAGE_URL='https://raw.githubusercontent.com/Wenjun-Mao/plotloom/main/docs/storyboard-handbook/assets/storyboards/moon-control-room-finished-frame.png'

curl --fail --silent --show-error \
  -H "${H3_AUTH}" \
  -H 'Content-Type: application/json' \
  -d @- \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs/from-image" <<JSON
{
  "sourceUrl": "${H3_TEST_IMAGE_URL}",
  "prompt": "A quiet cinematic hold. The astronaut turns toward the window, natural breathing, subtle cabin light movement, stable camera.",
  "profileId": "minimax_h3_fp8_turbo4_landscape_832x480_v1",
  "aspectPolicy": "contain_pad",
  "seed": 42
}
JSON
```

返回为普通、闭合的任务对象：

```json
{
  "id": "h3_…",
  "status": "queued",
  "profileId": "minimax_h3_fp8_turbo4_landscape_832x480_v1",
  "aspectPolicy": "contain_pad",
  "error": null,
  "outputReady": false
}
```

一步接口不支持 `idempotencyKey`。如果客户端在发送后超时，**不要自动重试**，
因为任务可能已入队。需要可重试去重、或想从同一张关键帧生成多个版本时，请用
下一节的两步流程。

### Bruno：用 URL 生成的正确请求体

在 Bruno 中，`sourceUrl` 必须使用 JSON body，不能同时声明
`Content-Type: application/json` 又选择 `multipart-form`。这会导致
`request_body_invalid`。

```yaml
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
        "sourceUrl": "https://raw.githubusercontent.com/Wenjun-Mao/plotloom/main/docs/storyboard-handbook/assets/storyboards/moon-control-room-finished-frame.png",
        "prompt": "A quiet cinematic hold. The astronaut turns toward the window, natural breathing, subtle cabin light movement, stable camera.",
        "profileId": "minimax_h3_fp8_turbo4_landscape_832x480_v1",
        "aspectPolicy": "contain_pad",
        "seed": 42
      }
```

把 Bearer Key 放在 Bruno 的环境变量或私密认证设置中，不要写进共享 YAML 文件。

## 6. 两步流程：可复用关键帧、可安全重试

先只验证 URL 下载和图片校验（**不会**生成视频）：

```sh
curl --fail --silent --show-error \
  -H "${H3_AUTH}" \
  -H 'Content-Type: application/json' \
  -d "{\"sourceUrl\":\"${H3_TEST_IMAGE_URL}\"}" \
  "${H3_GATEWAY_BASE_URL}/v1/assets"
```

它返回 `assetId`、检测到的 `mimeType`、宽高和 SHA-256。也可以上传本地图片：

```sh
ASSET_ID=$(curl --fail --silent --show-error \
  -H "${H3_AUTH}" \
  -F 'image=@/absolute/path/to/keyframe.png;type=image/png' \
  "${H3_GATEWAY_BASE_URL}/v1/assets" | python3 -c 'import json, sys; print(json.load(sys.stdin)["assetId"])')
```

再以 `assetId` 创建任务。此接口支持稳定的 `idempotencyKey`：以相同 key 和完全
相同内容重复请求会返回同一个任务；相同 key 搭配不同内容会返回
`idempotency_conflict`。

```sh
curl --fail --silent --show-error \
  -H "${H3_AUTH}" \
  -H 'Content-Type: application/json' \
  -d "{\"assetId\":\"${ASSET_ID}\",\"prompt\":\"A calm, stable close shot.\",\"profileId\":\"minimax_h3_fp8_turbo4_portrait_576x1024_v1\",\"aspectPolicy\":\"reject_mismatch\",\"idempotencyKey\":\"replace-with-a-stable-unique-request-key\"}" \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs"
```

本地文件上传时使用 `multipart/form-data`，并让 Bruno/curl 自动添加带 boundary 的
`Content-Type`；不要手写 `application/json`。multipart 版本必须提供 `image`
文件字段，而不是 `sourceUrl`。

## 7. 查询、下载和取消

```sh
export H3_JOB_ID='粘贴返回的 h3_ 任务 ID'

# 当 status 是 queued、submitting、submitted、running 或 transfer_pending 时继续轮询。
curl --fail --silent --show-error -H "${H3_AUTH}" \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs/${H3_JOB_ID}"

# 仅当 status 为 succeeded 且 outputReady 为 true 时下载。
curl --fail --silent --show-error -H "${H3_AUTH}" \
  -o "${H3_JOB_ID}.mp4" \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs/${H3_JOB_ID}/output"

# 只能安全取消 queued 状态的任务。
curl --fail --silent --show-error -X POST -H "${H3_AUTH}" \
  "${H3_GATEWAY_BASE_URL}/v1/video-jobs/${H3_JOB_ID}/cancel"
```

完成 MP4 在网关中保留 72 小时；请下载并存入自己的长期位置。任务记录、提示词和
网关托管关键帧最多保留 30 天，随后会清除。

## 8. 常见错误

| 错误码 | 常见原因 | 下一步 |
| --- | --- | --- |
| `request_body_invalid` | JSON header 与 multipart body 混用，或 JSON 格式无效 | URL 用 JSON；文件用 multipart，且不要手写错误的 Content-Type |
| `input_aspect_mismatch` | `reject_mismatch` 收到不符合 profile 比例的图 | 预先按目标画布重做图，或在明确接受黑边/裁切时选其他策略 |
| `source_url_invalid` / `source_url_fetch_failed` | URL 非 http(s)、无法下载或超时 | 使用可直接下载的内部或公开图片 URL |
| `source_url_too_large` / `image_pixels_exceed_limit` | 超过 20 MiB 或 3,000 万像素 | 先压缩或缩小图片 |
| `image_decode_invalid` / `unsupported_image_format` | 文件不是可解码的 JPEG、PNG 或 WebP | 转换或重新导出图片 |
| `profile_not_supported` | profile ID 不存在 | 调用 `/health` 并从当前目录复制 ID |
| `one_step_idempotency_not_supported` | 一步接口携带了 `idempotencyKey` | 改用两步流程 |
| `gateway_output_expired` | 完成后的 MP4 已超过 72 小时 | 视频无法恢复；重新提交前确认是否确有必要 |

这个 URL 获取功能是可信 Tailscale 内网的 MVP，当前没有面向公网的 SSRF/主机
过滤。不要把网关暴露到不受信任网络；若有公网需求，必须先进行单独的安全设计。
