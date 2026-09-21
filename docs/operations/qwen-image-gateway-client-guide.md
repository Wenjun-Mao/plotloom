# Qwen-Image-2.1 网关：同事 API 使用指南

这是 Spark 上仅供团队通过 Tailscale 调用的内部**图片**生成 API。它只提供
文生图与单参考图编辑；不是任意 SGLang 代理，也不支持多图编辑、任意采样参数或
任意尺寸。视频请使用独立的 [H3 API 使用指南](minimax-h3-gateway-client-guide.md)。

本文只提供 **Bruno** 示例。部署、保留期、故障恢复与维护请看
[Qwen-Image 网关运维手册](qwen-image-gateway-manual.md)。

## 1. 连接、认证与共享队列

当前 Tailscale 基地址：

```text
http://100.64.35.71:8090
```

在 Bruno 的私密环境变量中设置（不要把真实 Key 提交到 Bruno YAML）：

```text
H3_GATEWAY_BEARER=<向团队取得当前 Key>
```

除了 `GET /health` 外，所有接口都使用：

```yaml
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

```yaml
info:
  name: Qwen Image - Health
  type: http
http:
  method: GET
  url: http://100.64.35.71:8090/health
```

H3 视频和 Qwen 图片共用一个持久化 FIFO。`queuedJobs` 表示等待数量；任何时刻
最多一条 H3 或 Qwen 推理实际运行。创建成功只表示任务已持久化排队，并不表示图片
已经生成。

## 2. 选择画布与透明背景

每个请求都必须传入一个精确 `resolution`。网关不会为了适配而裁切、补边或缩放输出；
下载的 PNG 尺寸必定与选择的画布一致。

| 方向 | `resolution` | 输出尺寸 | 常用场景 |
| --- | --- | ---: | --- |
| 方形 | `1024x1024` | 1024 × 1024 | 概念图、独立角色图 |
| 横版 | `832x480` | 832 × 480 | 快速横版迭代 |
| 横版 | `960x544` | 960 × 544 | 标准横版 |
| 横版 | `1280x704` | 1280 × 704 | 高分辨率横版 |
| 竖版 | `576x1024` | 576 × 1024 | 快速手机竖版迭代 |
| 竖版 | `608x1088` | 608 × 1088 | 标准手机竖版 |
| 竖版 | `704x1280` | 704 × 1280 | 高分辨率手机竖版 |

`backgroundMode` 可省略，默认 `opaque`：

| 值 | 含义 |
| --- | --- |
| `opaque` | 普通不透明 PNG |
| `transparent` | 要求 Qwen 生成真实 PNG alpha，用于独立角色或物件。它不是网关后处理抠图；没有真实透明像素时任务会失败。 |

`seed` 可省略。服务器会生成随机 seed，并在创建和状态响应中返回实际使用值。不能传
`quality`、`durationSeconds`、`profileId`、多图字段或底层模型参数。

## 3. 接口一览

| 方法 | 用途 |
| --- | --- |
| `GET /health` | 检查网关、H3、Qwen、已审核画布与共享队列；无需 Bearer |
| `POST /v1/image-jobs/from-text` | 文生一张 PNG |
| `POST /v1/image-jobs/from-image` | 使用唯一参考图编辑一张 PNG |
| `GET /v1/image-jobs/{id}` | 查询状态、实际 seed、画布与生成计时 |
| `GET /v1/image-jobs/{id}/output` | 下载完成 PNG |
| `POST /v1/image-jobs/{id}/cancel` | 仅取消仍为 `queued` 的任务 |

图片任务 ID 以 `img_` 开头。发送后 Bruno 超时不要盲目重试：任务可能已经入队；
先用已知 ID 查询状态。

## 4. Bruno：文生图（可直接测试）

下面的请求不需要图片 URL 或本地文件，可直接验证你是否有权限和网关是否可用：

```yaml
info:
  name: Qwen Image - Text to image portrait
  type: http
http:
  method: POST
  url: http://100.64.35.71:8090/v1/image-jobs/from-text
  headers:
    - name: Content-Type
      value: application/json
  body:
    type: json
    data: |-
      {
        "prompt": "电影感写实肖像，一名宇航员站在月球观测站内，柔和侧光，细节清晰，无可见文字。",
        "resolution": "576x1024",
        "backgroundMode": "opaque"
      }
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

响应会立即返回类似下列字段：

```json
{
  "id": "img_…",
  "status": "queued",
  "resolution": "576x1024",
  "backgroundMode": "opaque",
  "seed": 123456,
  "outputReady": false
}
```

## 5. Bruno：单参考图编辑

使用 `POST http://100.64.35.71:8090/v1/image-jobs/from-image`。在 Bruno 选择
**Body → Multipart Form**，不要手写 `Content-Type`：

| 字段 | 类型 | 值 |
| --- | --- | --- |
| `image` | File | 必填；唯一参考图，JPEG、PNG 或 WebP，最多 20 MiB / 3,000 万像素 |
| `prompt` | Text | 必填；清楚说明保留什么、修改什么 |
| `resolution` | Text | 必填；上表任一精确值 |
| `seed` | Text | 可选正整数；省略则服务器生成 |
| `backgroundMode` | Text | 可选；`opaque` 或 `transparent` |

也可以发送 JSON，使用同样的 `prompt`、`resolution`、`seed`、`backgroundMode` 加
一个可下载的 `sourceUrl`。一次请求不能混用 URL 与文件，也不能提供第二张参考图。
参考图无需与输出具有相同像素尺寸；输出仍严格使用 `resolution`。请在 prompt 中说明
希望保留的主体和构图，避免把 Qwen 的重新构图能力误认为像素级保真承诺。

## 6. Bruno：查询、下载与取消

将 `img_替换为任务ID` 换成创建响应中的 `id`：

```yaml
info:
  name: Qwen Image - Check job
  type: http
http:
  method: GET
  url: http://100.64.35.71:8090/v1/image-jobs/img_替换为任务ID
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

只在 `status: succeeded` 且 `outputReady: true` 时下载：

```yaml
info:
  name: Qwen Image - Download output
  type: http
http:
  method: GET
  url: http://100.64.35.71:8090/v1/image-jobs/img_替换为任务ID/output
auth:
  type: bearer
  token: "{{H3_GATEWAY_BEARER}}"
```

状态响应包含 `outputWidth`、`outputHeight`、`outputContentType`、`seed` 与
`generationElapsedMs`。该计时从网关调用 SGLang 前到收到模型响应，**不含**输入
URL 下载/解码和写入网关托管输出的时间；它是后端用时，不是精确 GPU-only 指标。

完成 PNG 保留 72 小时；任务记录与网关暂存参考图最多保留 30 天。需要长期使用的
图片必须导入 Plotloom 或自己的资产库。

## 7. 常见错误

| 错误码 | 原因与处理 |
| --- | --- |
| `request_body_invalid` / `request_fields_invalid` | JSON 格式、字段名或字段类型错误；不要混用 JSON 与 multipart。 |
| `request_invalid` | 请求包含该路由不接受的字段，例如 `quality`、多图字段或 `profileId`。 |
| `image_resolution_not_supported` | 只使用上表七个精确 `resolution` 值。 |
| `image_file_required` | multipart 编辑缺少 `image`。 |
| `source_url_invalid` / `source_url_fetch_failed` | `sourceUrl` 不是可下载 http(s) 图片，或 Spark 无法访问。 |
| `qwen_image_unavailable` | SGLang 未就绪；稍后重试或联系运维。 |
| `qwen_image_generation_failed` / `qwen_image_response_invalid` | 模型或响应未通过网关验证；保留任务 ID 并联系运维。 |
| `qwen_image_alpha_missing` | `transparent` 请求没有产生真正透明的 PNG；改为 `opaque` 或换提示词/seed。 |
| `gateway_output_expired` | 已超过 72 小时；输出不能恢复，需要重新提交。 |
| `job_not_cancellable` | 任务已开始提交或运行；继续查询已知任务，不要重复创建。 |
