# 台词表演 API 使用指南

入口：Voice Lab `http://100.64.35.71:8897/`；网关
`http://100.64.35.71:8090`。网关请求使用现有 Bearer Key。
以下是 Bruno 的方法、URL、鉴权和 JSON Body 配置，不需要调用私有执行接口。

## 身份和表演是两个对象

- `voiceId`：在 Voice Lab 发布的永久声线，代表角色的声音身份。
- `takeId`：用该声线说一段准确台词的独立结果。重新生成获得新 ID，旧音频不变。
- 项目里的“复用测试”是临时试听；正式可复用表演请使用“台词表演”。
- 发布声线和表演音频没有自动过期时间，项目删除不会删除它们。
  网关视频/图像仍保留 72 小时，临时任务记录保留 30 天。

先在 UI 发布并复制 Voice ID，再选择它生成台词表演。页面打开不生成任务；
可查看全局排队位置、真实阶段、耗时、实际情绪强度，试听和下载。

## 1. 创建表演

Bruno：**POST** `http://100.64.35.71:8090/v1/voice-takes`，Auth 选
**Bearer Token**，Body 选 **JSON**：

```json
{
  "voiceId": "voice_<复制的32位ID>",
  "engineId": "index_base",
  "text": "等等，别打开那扇门！控制台还在报警，先把电源切断！",
  "seed": 20260929,
  "delivery": {
    "mode": "text",
    "description": "情况紧迫，果断地制止对方。语气坚定，立即行动，不恐慌、不害怕。"
  }
}
```

成功返回 `202`，立即提供 `takeId`。`voiceId` 必须已发布；不接受任意路径、
候选 ID、输入音频 URL 或隐式当前选择。`engineId` 必填；`seed` 可省略，
默认随机 32 位整数；台词为 1–200 字符的非空文本。

| 引擎 | `delivery` |
| --- | --- |
| `qwen_base` | 仅 `{"mode":"none"}`；省略时同样为 none |
| `index_base` | none、text 中文描述、manual 八维强度 |

描述不作为台词朗读。手动控制例子：

```json
{"mode":"manual","vector":[0,0.25,0,0,0,0,0,0]}
```

顺序为 快乐、愤怒、悲伤、害怕、厌恶、低落、惊讶、平静。每维 0–1，
无需总和为 1。这是具体实验的强度示例，不是通用情绪预设。不同 mode 的
字段不能混用；Qwen 接收 text/manual 会拒绝，不会悄悄忽略。

## 2. 列表和状态

Bruno **GET**：

```text
http://100.64.35.71:8090/v1/voice-takes?voiceId=voice_<ID>
http://100.64.35.71:8090/v1/voice-takes/take_<ID>
```

状态包括 queued、running、completed、failed、interrupted、deleted。
状态查询给出排队位置/真实阶段、冻结引擎和种子、请求的 delivery、实际
`executionDetails`、原生/准备后音频 hash、时长、采样率和 H3 合格标记。
`queueAhead=null` 表示还在等待跨服务登记，不是假装“下一个开始”。
`dispatchErrorCode` 表示共享调度问题，和合成结果的 `errorCode` 分开。
系统不提供虚构完成百分比或 ETA。

创建响应丢失时先查该声线的列表，不要直接再发 POST。执行回复不确定、
子进程释放无法确认时，全局队列会暂停而不是并发重试。请交管理员核实。
H3、Qwen 图像和全部声线创作/复用任务共享 FIFO；顺序以登记序号为准。

## 3. 下载并用于 H3

Bruno **GET**，保存响应为 WAV：

```text
http://100.64.35.71:8090/v1/voice-takes/take_<ID>/audio?kind=source
http://100.64.35.71:8090/v1/voice-takes/take_<ID>/audio?kind=h3
```

source 保留模型的原生 WAV；h3 为单独的 32 kHz 单声道 PCM16 副本，记录
重采样/增益。不会裁剪、拉伸或修改原始音频。只有 `h3Eligible=true` 才能
取得 h3 副本（1–10 秒、不超过 2 MiB）。不合格时仍可试听原生结果。

在现有 `POST /v1/video-jobs/from-image-with-voice` 的 multipart 请求里，将
此副本作为 **voiceAudio** 文件上传，另提供 image 和原有字段。
不要把 Take/Voice ID 放到视频请求；视频 endpoint 不自动生成/查询语音。
H3 会生成新的声轨，参考 WAV 不是精确复制或自动配音/口型保证。
Plotloom 后续须自行保存选中的音频、hash 和来源，不能依赖临时视频保留期。

## 4. 删除单个表演

Bruno **DELETE** `http://100.64.35.71:8090/v1/voice-takes/take_<ID>`，JSON：

```json
{"confirmTakeId":"take_<同一个ID>"}
```

仅终态且没有未确认执行的表演可删除。删除其托管音频，保留不可复活的
最小结果标记；不会删除 Voice ID、其他 Take 或已上传 H3 的独立输入。
不存在声音发布的删除 API，已下载到调用方的副本也不会被网关清理。
