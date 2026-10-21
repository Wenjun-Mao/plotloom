# 生成网关控制台

## 同事怎么用

地址：**https://gx10-1523.tail6040ad.ts.net/dashboard/**。
使用设备必须已连接获准访问 Spark 的 Tailscale 网络。无需额外登录，
也不要把生成 API Key 填入网址、浏览器或聊天。此地址是否已上线，
以本次部署验收记录为准。

- **网关健康检查**：显示现有网关 `/health` 最近一次检查结果和时间。
  检查不可用时，不代表保留的视频被删除；仍可查看能读取的历史记录。
- **共享通道 / FIFO 队列**：H3、Qwen 图像和 Voice Lab 共用。
  「持有通道」不等于一定正在 GPU 上计算；未知结果和等待外部任务的原因码会保留。
- **生成 H3 视频**：上传首帧，或填写图片下载链接；尾帧可选，但首尾帧必须
  同为上传或同为链接。填写提示词，选择质量、分辨率和时长后点击「提交生成」。
  成功后自动打开新任务。当前控制台只提供图生视频，不提供 T2V、Qwen 生成、
  声音输入、批量任务、取消或删除按钮。
- **任务记录**：按 ID 查找，或按服务、状态筛选；默认每页 50 条。
  点击任务查看完整 ID、seed、分辨率、质量、耗时、错误码、ComfyUI ID 和输出。
- **播放 / 下载**：有原始文件且未过期时可播放、拖动进度条或下载。
  不会重编码、静音、重新生成，也不会自动选择/批准任何结果。
- **提示词**：只在点击「查看提示词」后读取，以纯文本显示。
  获准使用看板的同事可以查看这些任务详情和输出，请按内部资料处理。

## 生成选项

| 参数 | 可选值 / 行为 |
|---|---|
| 质量 | 1：V1.2 Turbo-4（默认）；2：V1.0 Turbo-4；3：V1.0 Turbo-8；8：Base-20 |
| 竖屏分辨率 | 576x1024（默认）、608x1088、704x1280 |
| 横屏分辨率 | 832x480、960x544、1280x704 |
| 时长 | 整数 5–15 秒，默认 5 秒；实际合同帧数可能让输出略长 |
| Seed | 留空随机；可在高级设置填写 0–9223372036854775807 的整数 |
| 宽高比 | 默认不匹配时拒绝；也可选居中裁剪铺满，或完整保留并补黑 |

每张图片不超过 20 MiB。URL 必须是网关可下载的 http(s) 图片链接，不是网页。
同宽高比但分辨率不同的图片会按既有网关规则缩放；不会因打开控制台改变规则。
「复用设置到生成表单」只复制提示词和参数，**不提交**，也不恢复旧图片或
源 URL；必须重新提供首帧及可选尾帧。Seed 作为十进制文本传递，避免浏览器
大整数舍入；这不改变既有生成 API 的响应合同。

提交过程中按钮暂时禁用。提交失败保留表单；如果提示「提交结果未确认」，
任务可能已创建，请先检查队列及最近记录，不要直接重试。页面不会自动重发。
重新加载页面不会重发，但未提交的表单不做持久保存。

时间采用浏览器本地时区，并显示时区标识。生成耗时从网关观测到后端接受
工作流开始，到观测完成为止，不包括前面的排队/输入下载，也不是 GPU 纯计算时间。
「请求时长」是调用参数；「合同预期时长」是冻结帧数 ÷ 帧率，例如
15 秒请求对应 362 帧 / 24fps，约 15.083 秒。看板不重新测量文件时长。

输出仍按原规则保留 **72 小时**，记录按现有 **30 天**规则清理。
过期文件不会因为打开看板而续期。文件过期、缺失、未生成、读取失败分别显示；
刷新不会重新提交任务。浏览器已下载的文件不受服务端过期删除控制。

## 运维边界

源码属于 `services/minimax_h3_gateway/src/plotloom_h3_gateway/dashboard/`。
独立容器 `plotloom-h3-dashboard` 仅绑定 `127.0.0.1:8091`，通过 Tailscale Serve
提供私有 HTTPS。它只挂载专用的网关 key 文件，不挂载完整网关 `.env`、Docker socket 或 GPU，
现有网关数据目录只读挂载到 `/data`。数据库采用只读连接，不初始化、迁移、
清理、恢复或直接派发任务；无需新数据库。提交只转发到固定的现有 H3 接口；
由网关执行所有写入和 FIFO 派发。既有 8090 API 和 bearer 鉴权不变。
获准访问控制台的 Tailscale 成员现在也可以创建 H3 任务，不只是查看记录。
凭据不进入页面、URL、浏览器存储、数据库或日志；POST 要求精确同源和自定义请求头。

部署前准备专用文件 `/home/wjmao/services/plotloom-h3-dashboard/gateway_key`，
内容仅为现有 `H3_API_KEY` 的值，属主为运行容器的 UID1000，权限0600。
不复制整个环境文件，不轮换 API Key。通过只读挂载在容器内
`/run/secrets/gateway_key` 读取；临时 multipart 文件使用限64MiB的 `/tmp` tmpfs。
容器没有 key 配置时仍可用作只读看板，生成表单禁用。

从部署 release 根目录执行：

```sh
docker compose -p plotloom-h3-dashboard -f services/minimax_h3_gateway/dashboard-compose.yml build dashboard
docker compose -p plotloom-h3-dashboard -f services/minimax_h3_gateway/dashboard-compose.yml up -d --no-deps dashboard
docker inspect --format '{{.State.Status}} {{.State.Health.Status}}' plotloom-h3-dashboard
docker logs --tail 50 plotloom-h3-dashboard
tailscale serve status --json
```

HTTPS 路径的实际已验证配置、部署 release 位置和镜像 digest 记录在
[生成控制台验收记录](../../../docs/verification/2026-10-21-h3-dashboard-generation.md)。
使用后台持久 Serve 配置；不要启用 Funnel，也不要把 `/v1` 生成接口或整个
输出目录通过 Serve 发布。仅保留 `/dashboard/` 入口、资源及单一受保护提交接口。
HTTPS 管理员配置步骤仍与前次相同；未通过实际 HTTPS 验证前不能宣称已上线。

部署前等待共享通道、队列和 ComfyUI 队列都空闲；不强行停止同事的任务。
只启动/重启看板，不重启网关、ComfyUI、Qwen 或 Voice Lab。
镜像从仓库 `uv.lock` 安装锁定依赖。只读目录必须包含实际数据库及可能的
`-wal`/`-shm` 文件；不要复制运行中的单个数据库或使用 `immutable=1`。

回滚只停止看板容器并关闭本次增加的 `/dashboard` Serve handler：

```sh
docker compose -p plotloom-h3-dashboard -f services/minimax_h3_gateway/dashboard-compose.yml stop dashboard
```

关闭 Serve handler 的确切命令见验收记录。不要使用 `tailscale serve reset`，
不要删除数据库、输出文件或通道保留记录。

## 验证入口

```sh
uv run --locked pytest -q tests/services/minimax_h3_gateway
node --test tests/services/minimax_h3_gateway/test_dashboard*_ui.mjs
uv run --locked ruff check services/minimax_h3_gateway/src/plotloom_h3_gateway/dashboard tests/services/minimax_h3_gateway/test_dashboard*.py
```

用保留文件或测试夹具验证真实浏览器播放、拖动、下载、刷新和状态轮询。
页面不会自动播放；轮询不替换当前视频元素。不把软件解码通过当成所有浏览器
必定播放成功，也不把看板上线当成同事反馈的问题已经修复。
