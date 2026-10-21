"use strict";
const $ = (id) => document.getElementById(id);
const statusNames = {
  queued: "排队",
  submitting: "正在提交",
  submitted: "已提交",
  running: "生成中",
  transfer_pending: "输出转存中",
  succeeded: "已完成",
  failed: "失败",
  cancelled: "已取消",
  outcome_unknown: "结果未知",
};
const outputNames = {
  available: "可查看",
  expired: "输出已过期",
  missing: "文件缺失",
  unavailable: "输出不可用",
  not_ready: "尚无输出",
};
const date = (s) =>
  s ? new Date(s).toLocaleString("zh-CN", { timeZoneName: "short" }) : "—";
const duration = (ms) =>
  ms == null
    ? "—"
    : `${Math.floor(ms / 60000)} 分 ${Math.floor(ms / 1000) % 60} 秒`;
const backendName = (s) =>
  ({ h3_video: "H3 视频", qwen_image: "Qwen 图像", voice_lab: "Voice Lab" })[
    s
  ] || s;
const text = (id, value) => {
  $(id).textContent = String(value ?? "—");
};
let selected = new URL(location.href).searchParams.get("job") || "";
let cursor = "",
  history = [],
  nextCursor = null,
  epoch = 0,
  inflight = false,
  pending = false;
let controller = null,
  timer = null,
  mediaKey = "",
  delay = 5000;
let query = { search: "", backend: "", status: "" };
function resetDetail() {
  mediaKey = "";
  $("preview").replaceChildren();
  $("detail-fields").replaceChildren();
  text("detail-id", selected);
  text("frozen", "");
  text("output-note", "正在读取…");
  text("prompt", "");
  $("prompt").hidden = true;
  text("prompt-toggle", "查看提示词");
  $("download").hidden = true;
  $("reuse-settings").hidden = true;
  $("detail-error").hidden = true;
  $("detail").hidden = !selected;
  $("detail-empty").hidden = Boolean(selected);
}
async function get(path, signal) {
  const r = await fetch(path, { signal, cache: "no-store" });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${r.status}`);
  }
  return r.json();
}
function selectJob(id) {
  if (selected !== id) {
    selected = id;
    resetDetail();
  }
  const url = new URL(location.href);
  url.searchParams.set("job", id);
  window.history.pushState(null, "", url);
  invalidate();
}
function invalidate() {
  epoch++;
  controller?.abort();
  pending = true;
  clearTimeout(timer);
  refresh();
}
function renderOverview(o) {
  text("observed", `最近读取 ${date(o.observedAt)}`);
  text("health", o.gateway.status === "ok" ? "正常" : "未确认 / 不可用");
  text("health-time", `健康观测 ${date(o.gateway.observedAt)}`);
  text(
    "active",
    o.active == null ? "未确认" : o.active ? "通道已占用" : "空闲",
  );
  text("queued", o.queued == null ? "—" : `${o.queued} 条`);
  text(
    "database",
    o.database === "ok" ? "数据库可读" : `数据库不可读 · ${o.error}`,
  );
  const owner = o.queue.find((r) => r.state === "active");
  text(
    "lane-note",
    owner
      ? `${owner.owner === "voice_lab" ? "Voice Lab" : backendName(owner.kind)}${owner.error ? " · 持有原因：" + owner.error : " · 按记录持有通道"}`
      : "H3 · Qwen Image · Voice Lab 共用 FIFO",
  );
  const list = $("queue");
  list.replaceChildren();
  if (!o.queue.length) {
    const li = document.createElement("li");
    li.textContent =
      o.database === "ok"
        ? "当前没有等待或持有通道的任务。"
        : "队列状态未确认。";
    list.append(li);
  }
  for (const r of o.queue) {
    const li = document.createElement("li"),
      label = document.createElement("span");
    label.textContent = `${r.state === "active" ? "持有通道" : "等待 · 前方 " + r.queueAhead + " 条"} · ${backendName(r.kind)} · `;
    li.append(label);
    if (r.owner === "gateway") {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = r.jobId;
      b.onclick = () => selectJob(r.jobId);
      li.append(b);
    } else li.append(document.createTextNode(r.jobId));
    if (r.error) li.append(document.createTextNode(" · " + r.error));
    list.append(li);
  }
  text(
    "queue-summary",
    o.queueTruncated ? "仅显示前 100 条" : "按真实共享顺序排列",
  );
}
function renderJobs(data) {
  const body = $("jobs");
  body.replaceChildren();
  nextCursor = data.nextCursor;
  for (const j of data.jobs) {
    const row = document.createElement("tr");
    const values = [
      "",
      statusNames[j.status] || j.status,
      `${backendName(j.backend)}${j.quality == null ? "" : " · Q" + j.quality} · ${j.resolution}${j.requestedDurationSeconds ? " · " + j.requestedDurationSeconds + "秒" : ""}`,
      duration(j.generationElapsedMs),
      outputNames[j.output] || j.output,
    ];
    for (let i = 0; i < values.length; i++) {
      const cell = document.createElement("td");
      cell.textContent = values[i];
      if (i === 0) {
        const b = document.createElement("button");
        b.type = "button";
        b.textContent = j.id;
        b.onclick = () => selectJob(j.id);
        b.classList.toggle("selected", j.id === selected);
        cell.append(b);
        const small = document.createElement("small");
        small.textContent = date(j.createdAt);
        cell.append(small);
        cell.classList.toggle("current", j.id === selected);
      }
      if (i === 1) {
        const badge = document.createElement("span");
        badge.textContent = values[i];
        badge.className =
          "badge" +
          (j.status === "succeeded"
            ? " good"
            : ["failed", "outcome_unknown"].includes(j.status)
              ? " bad"
              : "");
        cell.replaceChildren(badge);
      }
      row.append(cell);
    }
    body.append(row);
  }
  $("empty").hidden = Boolean(data.jobs.length);
  $("previous").disabled = !history.length;
  $("next").disabled = !nextCursor;
  text("page", `第 ${history.length + 1} 页 · 每页 50 条`);
}
function renderDetail(j) {
  $("detail-empty").hidden = true;
  $("detail").hidden = false;
  $("detail-error").hidden = true;
  text("detail-id", j.id);
  const fields = [
    ["状态", statusNames[j.status] || j.status],
    ["服务 / 模式", `${backendName(j.backend)} / ${j.inputMode}`],
    [
      "质量 / 分辨率",
      `${j.quality == null ? "—" : j.quality} / ${j.resolution}`,
    ],
    ["裁剪策略", j.aspectPolicy],
    ["Seed", j.seed],
    [
      "请求时长",
      j.requestedDurationSeconds == null
        ? "—"
        : `${j.requestedDurationSeconds} 秒`,
    ],
    [
      "合同预期时长",
      j.expectedDurationSeconds == null
        ? "—"
        : `${j.expectedDurationSeconds.toFixed(3)} 秒 · ${j.frameCount} 帧 / ${j.fps} fps`,
    ],
    ["创建", date(j.createdAt)],
    ["后端提交", date(j.generationSubmittedAt)],
    ["完成观测", date(j.generationCompletedAt)],
    ["等待耗时", duration(j.waitingElapsedMs)],
    ["生成耗时", duration(j.generationElapsedMs)],
    ["错误码", j.error],
    ["ComfyUI ID", j.comfyPromptId],
    ["输出过期", date(j.outputExpiresAt)],
    [
      "输出大小",
      j.outputSizeBytes == null
        ? "—"
        : `${(j.outputSizeBytes / 1048576).toFixed(2)} MiB`,
    ],
    ["SHA256（记录）", j.outputSha256],
  ];
  const dl = $("detail-fields");
  dl.replaceChildren();
  for (const [k, v] of fields) {
    const dt = document.createElement("dt"),
      dd = document.createElement("dd");
    dt.textContent = k;
    dd.textContent = v ?? "—";
    dl.append(dt, dd);
  }
  text("frozen", JSON.stringify(j.frozenSettings, null, 2));
  $("reuse-settings").hidden =
    j.backend !== "h3_video" || j.inputMode !== "image";
  $("reuse-settings").onclick = async () => {
    const id = j.id;
    $("reuse-settings").disabled = true;
    try {
      const data = await get(
        `/dashboard/api/jobs/${encodeURIComponent(id)}/prompt`,
      );
      if (id === selected)
        window.dispatchEvent(
          new CustomEvent("dashboard:reuse", {
            detail: { ...j, prompt: data.prompt },
          }),
        );
    } catch (error) {
      if (id === selected) {
        $("detail-error").hidden = false;
        text("detail-error", `复用设置失败：${error.message}`);
      }
    } finally {
      $("reuse-settings").disabled = false;
    }
  };
  const key = `${j.id}:${j.output}`;
  if (key !== mediaKey) {
    $("preview").replaceChildren();
    mediaKey = key;
    if (j.output === "available") {
      const media = document.createElement(
        j.backend === "h3_video" ? "video" : "img",
      );
      media.src = `/dashboard/media/${encodeURIComponent(j.id)}`;
      if (media instanceof HTMLVideoElement) {
        media.controls = true;
        media.preload = "metadata";
        media.playsInline = true;
      } else media.alt = "生成图像原始输出";
      media.addEventListener("error", () =>
        text("output-note", "浏览器无法读取或播放此输出；可下载原始文件检查。"),
      );
      $("preview").append(media);
    }
  }
  text("output-note", outputNames[j.output] || j.output);
  $("download").hidden = j.output !== "available";
  $("download").href =
    `/dashboard/media/${encodeURIComponent(j.id)}?download=true`;
}
async function refresh() {
  if (inflight) {
    pending = true;
    return;
  }
  if (document.hidden) return;
  inflight = true;
  pending = false;
  const own = epoch,
    id = selected;
  controller = new AbortController();
  const timeout = setTimeout(() => controller?.abort(), 12000);
  const signal = controller.signal;
  try {
    const params = new URLSearchParams({ ...query, cursor });
    const [overview, jobs, detail] = await Promise.all([
      get("/dashboard/api/overview", signal),
      get(`/dashboard/api/jobs?${params}`, signal),
      id
        ? get(`/dashboard/api/jobs/${encodeURIComponent(id)}`, signal).catch(
            (e) => ({ detailError: e.message }),
          )
        : null,
    ]);
    if (own !== epoch) return;
    renderOverview(overview);
    renderJobs(jobs);
    if (detail?.detailError) {
      $("detail").hidden = false;
      $("detail-empty").hidden = true;
      $("detail-error").hidden = false;
      text("detail-error", `无法读取所选任务：${detail.detailError}`);
      $("preview").replaceChildren();
      mediaKey = "";
      $("download").hidden = true;
    } else if (detail) renderDetail(detail);
    else {
      $("detail").hidden = true;
      $("detail-empty").hidden = false;
    }
    $("error").hidden = true;
    delay = 5000;
  } catch (e) {
    if (own === epoch) {
      text(
        "error",
        `读取失败，当前显示可能已过时：${e.name === "AbortError" ? "请求超时" : e.message}`,
      );
      $("error").hidden = false;
      delay = Math.min(delay * 2, 30000);
    }
  } finally {
    clearTimeout(timeout);
    inflight = false;
    if (!document.hidden) timer = setTimeout(refresh, pending ? 0 : delay);
  }
}
$("filters").addEventListener("submit", (e) => {
  e.preventDefault();
  query = {
    search: $("search").value.trim(),
    backend: $("backend").value,
    status: $("status").value,
  };
  cursor = "";
  history = [];
  invalidate();
});
$("refresh").onclick = invalidate;
$("next").onclick = () => {
  if (nextCursor) {
    history.push(cursor);
    cursor = nextCursor;
    invalidate();
  }
};
$("previous").onclick = () => {
  if (history.length) {
    cursor = history.pop();
    invalidate();
  }
};
$("copy").onclick = async () => {
  try {
    await navigator.clipboard.writeText(selected);
    text("copy", "已复制");
    setTimeout(() => text("copy", "复制任务 ID"), 1500);
  } catch {
    text("copy", "复制失败，请选中 ID 手动复制");
  }
};
$("prompt-toggle").onclick = async () => {
  if (!$("prompt").hidden) {
    $("prompt").hidden = true;
    text("prompt-toggle", "查看提示词");
    return;
  }
  const id = selected;
  $("prompt").hidden = false;
  text("prompt", "正在读取…");
  text("prompt-toggle", "隐藏提示词");
  try {
    const d = await get(`/dashboard/api/jobs/${encodeURIComponent(id)}/prompt`);
    if (id === selected) text("prompt", d.prompt);
  } catch (e) {
    if (id === selected) text("prompt", `读取失败：${e.message}`);
  }
};
document.addEventListener("visibilitychange", () => {
  clearTimeout(timer);
  if (!document.hidden) invalidate();
});
window.addEventListener("dashboard:submitted", (event) => {
  query = { search: "", backend: "", status: "" };
  for (const key of ["search", "backend", "status"]) $(key).value = "";
  cursor = "";
  history = [];
  selectJob(event.detail);
});
window.addEventListener("dashboard:refresh", invalidate);
window.addEventListener("popstate", () => {
  selected = new URL(location.href).searchParams.get("job") || "";
  resetDetail();
  invalidate();
});
refresh();
