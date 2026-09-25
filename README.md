# Plotloom · 叙织

Plotloom 是一个本地优先、以显式数据合同驱动的“故事输入 → 结构 → 场景节拍 → 分镜 → 媒体任务”工作台。它把生成过程中的提示词、响应、验证失败、修复链路和版本依赖保留下来，而不是只保存最终画面。

这是一个全新的独立仓库。运行时只包含 Plotloom 自己的 Python 包、React 前端、提示词模板、数据库迁移和测试；不依赖 Narrative Forge V1，也不读取其项目数据。

## 本地启动

需要 Python 3.10+、[uv](https://docs.astral.sh/uv/) 和 Node.js 22+。

```sh
uv sync --all-groups
npm --prefix frontend ci
npm --prefix frontend run build
uv run plotloom
```

打开 <http://127.0.0.1:8775/v2/>。默认端口是 `8775`；本地端口被占用时会依次尝试后续 19 个端口。托管环境提供的 `PORT` 始终优先，且不会自动换端口。

前后端分开开发时：

```sh
# 终端 1
uv run plotloom

# 终端 2
npm --prefix frontend run dev
```

Vite 默认使用 `5173`，并把 `/api/v2` 代理到 `127.0.0.1:8775`。可用 `PLOTLOOM_API_ORIGIN` 指向其他后端。

## 配置与密钥

把 [`.env.example`](.env.example) 复制为 `.env`。Plotloom 只会在源码工作区加载仓库根目录的 `.env`，并且现有主机环境变量优先；修改后需要重启服务器。安装后的 wheel 不会从当前工作目录搜索 `.env`。

服务器 API key 来自环境变量或 `.env`。浏览器里输入的临时 key 只保存在当前标签页的 `sessionStorage`，不会进入项目、数据库、日志或供应商设置。公开的供应商、模型、认证模式、文本能力和超时可以持久化为服务器管理的受信任**文本** profile；每次文本运行会冻结其公开的 ID、版本和哈希。图像和视频仍使用各自的全局公开设置，不能由文本 profile 选择或覆盖。

受信任文本 profile 可使用 HTTP 或 HTTPS 根地址，因而可连接本机、LAN 或 Tailscale 上的 OpenAI-compatible `llama-server`。根地址不得含 URL 凭据、query 或 fragment，且 Plotloom 不会跟随供应商重定向。`*_AUTH_MODE=none` 适用于不需要密钥的本地服务，并且不会发送 `Authorization`；`bearer` 则需要服务器 key 或当前标签页临时 key。媒体任务只能使用已保存的全局媒体 provider、模型、认证与根地址，不能由请求覆盖。

`TEXT_MODEL` 应填写该服务 `/models` 返回的精确公开 ID。Plotloom 会把它冻结进运行计划，不会为了“看起来能跑”而静默换成列表中的第一个模型。

应用没有内置身份认证。远程部署必须保持私有，或在 Plotloom 外部加认证层。

### 私有 MiniMax-H3 视频端点

完整的部署、维护、故障恢复和已验证边界见
[MiniMax-H3 gateway operator and maintainer manual](docs/operations/minimax-h3-gateway-manual.md)。

Spark 上的 H3 使用一个带 bearer key 的私有网关，ComfyUI 本身只监听
`127.0.0.1`。在 `.env` 中填写网关的 Tailscale `VIDEO_BASE_URL`、
`VIDEO_MODEL_API_KEY`，并严格设置：

```dotenv
PLOTLOOM_ENABLE_H3_GATEWAY=true
VIDEO_PROVIDER=minimax_h3_gateway
VIDEO_MODEL=minimax_h3_gateway_catalog_v7
```

H3 提供受审核的横竖屏档位；默认是 576×1024，另有 832×480、960×544、
1280×704、608×1088 与 704×1280。Plotloom 新请求明确提供开发用质量 1
与制作审核候选质量 8，初始选择为质量 8；支持 5–15 整数秒请求，并以 24 fps 的
`17k+5` 帧格向上吸附（5 秒 124 帧，8 秒 192 帧，15 秒 362 帧）。请求时长
不是最终播放时长；现有已审核播放片段路径仍限于其六/八秒来源合同。工作台默认要求关键帧与目标档位同宽高比，绝不会无提示拉伸或加黑边；如作者
有意保留横幅构图，可显式选择“允许黑边画布”。该选择只会冻结 `contain_pad` 输入
模式，仍须通过关键帧、溯源、profile、输出尺寸、角色与人工审核检查。实际下载的
文件也必须匹配冻结 profile，不能因“能播放”就被采用。H3 使用本地网关的队列容量，
不占用历史 Atlas Wan 的付费 100 秒额度；但仍会冻结关键帧、角色引用、审批、seed
和 adapter 版本。AAC 轨道不等于对白已通过，候选必须由人回放审核。
不要把 Spark 网关公开到互联网。

### 私有 Qwen-Image-2.1 图片端点

Qwen-Image-2.1 是与 H3 共用 Spark 网关 FIFO 的本地图片后端，但它有独立的
图片合同和维护边界。运维与恢复见
[Qwen-Image gateway operator and maintainer manual](docs/operations/qwen-image-gateway-manual.md)，
同事调用见中文 [Qwen-Image API 使用指南](docs/operations/qwen-image-gateway-client-guide.md)，
复现实机安装见
[Qwen-Image-2.1 Spark reproducible setup](services/minimax_h3_gateway/docs/qwen-image-spark-setup.md)。

Qwen 只接受经过验证的七个精确画布：`1024x1024`、横版
`832x480` / `960x544` / `1280x704`，以及竖版
`576x1024` / `608x1088` / `704x1280`。它提供文生一张 PNG 和单参考图编辑；
不提供多图编辑、任意尺寸或浏览器直连 SGLang。`transparent` 请求要求模型交付
真正的 PNG alpha，网关不会做抠图后处理。图片输出也只在网关中保留 72 小时，
任务与暂存输入最多保留 30 天；选中的资产应导入 Plotloom。

## 验证

```sh
uv run pytest -q
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
git diff --exit-code -- src/plotloom/static
npm --prefix frontend run test:e2e
uv build --wheel
uv run python scripts/smoke_installed_wheel.py dist
```

对已保存文本 profile 的真实四阶段验收与 secret-free 回执，见
[conformance runner](docs/conformance.md)。M1.5 只有在两个所需 profile
在 `--qualify-m15` 严格模式下各完成 3 次原子安装、各至少 10/12
阶段首轮通过后才可标记完成；较小批次只算诊断 probe。

更完整的开发说明见 [docs/development.md](docs/development.md)，当前交付进度见 [roadmap entrypoint](docs/roadmap/README.md)，旧[能力矩阵](docs/roadmap/archive/superseded/2026-09-02-capability-matrix.md)仅作历史证据；架构与研究资料索引见 [docs/README.md](docs/README.md)，而 Spark 的 H3/Qwen 文档入口见 [generation operations index](docs/operations/README.md)。

## 版本边界

产品、包、CLI、配置和浏览器身份已经统一为 Plotloom。首个独立基线暂时保留 `/api/v2`、`/v2/` 和 `v2_*` 数据表，因为它们代表经过验证的 API／schema 合同版本，而不是 V1 运行时依赖。详见 [ADR 0010](docs/adr/0010-plotloom-clean-repository.md)。
