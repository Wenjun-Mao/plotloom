"use strict";
(() => {
  const el = (id) => document.getElementById(id);
  let busy = false;
  const value = (key) => el(`generate-${key}`).value;
  const message = (text) => {
    el("generation-message").textContent = text;
  };
  function sourceMode() {
    const upload = el("source-mode").value === "upload";
    el("upload-inputs").hidden = !upload;
    el("url-inputs").hidden = upload;
    for (const key of ["start-file", "end-file"]) el(key).disabled = !upload;
    for (const key of ["start-url", "end-url"]) el(key).disabled = upload;
    el("start-file").required = upload;
    el("start-url").required = !upload;
  }
  function payload() {
    const fields = {
      prompt: value("prompt"),
      quality: value("quality"),
      resolution: value("resolution"),
      durationSeconds: value("duration"),
      aspectPolicy: value("aspect"),
    };
    if (value("seed").trim()) fields.seed = value("seed").trim();
    if (el("source-mode").value === "url") {
      fields.sourceUrl = el("start-url").value.trim();
      if (el("end-url").value.trim())
        fields.endSourceUrl = el("end-url").value.trim();
      return {
        body: JSON.stringify(fields),
        headers: { "Content-Type": "application/json" },
      };
    }
    const form = new FormData();
    for (const [key, item] of Object.entries(fields)) form.set(key, item);
    for (const [key, input] of [
      ["image", "start-file"],
      ["endImage", "end-file"],
    ]) {
      const file = el(input).files[0];
      if (file?.size > 20 * 1024 * 1024)
        throw Error("图片每张不能超过 20 MiB。");
      if (file) form.set(key, file);
    }
    return { body: form, headers: {} };
  }
  const errorMessages = {
    submission_not_configured: "服务端尚未配置生成凭据。",
    gateway_submission_unauthorized: "网关鉴权未通过，请联系管理员。",
    submission_origin_refused: "提交来源未通过检查，请从正式看板地址打开。",
    request_too_large: "上传内容过大。图片每张不能超过 20 MiB。",
    request_invalid: "请检查参数、图片链接、分辨率与时长。",
    input_aspect_mismatch: "图片宽高比不匹配；请更换图片或选择裁剪/补黑策略。",
  };
  el("source-mode").onchange = sourceMode;
  el("generation-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (busy) return;
    let request;
    try {
      request = payload();
    } catch (error) {
      message(error.message);
      return;
    }
    busy = true;
    el("generation-fields").disabled = true;
    message("正在提交…成功后将打开任务。请勿重复提交。");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 110000);
    try {
      const response = await fetch("/dashboard/api/generation", {
        method: "POST",
        body: request.body,
        headers: { ...request.headers, "X-Dashboard-Request": "1" },
        signal: controller.signal,
        cache: "no-store",
      });
      const result = await response.json();
      if (!response.ok) {
        if (result.error === "submission_outcome_unknown")
          throw Error("UNKNOWN");
        message(
          errorMessages[result.error] ||
            `提交被拒绝：${result.error || response.status}。请检查后再手动提交。`,
        );
        return;
      }
      if (!/^h3_[0-9a-f]{32}$/.test(result.id)) throw Error("UNKNOWN");
      message(`已提交：${result.id}。排队、生成进度与输出见下方任务详情。`);
      window.dispatchEvent(
        new CustomEvent("dashboard:submitted", { detail: result.id }),
      );
    } catch {
      message(
        "提交结果未确认，任务可能已创建。请先刷新下方队列和最近记录，勿直接重试以免重复生成。",
      );
      window.dispatchEvent(new CustomEvent("dashboard:refresh"));
    } finally {
      clearTimeout(timeout);
      busy = false;
      el("generation-fields").disabled = false;
    }
  });
  window.addEventListener("dashboard:reuse", (event) => {
    if (busy) {
      message("请等待当前提交完成，再复用其他设置。");
      return;
    }
    const job = event.detail;
    for (const [key, setting] of Object.entries({
      prompt: job.prompt,
      quality: job.quality,
      resolution: job.resolution,
      duration: job.requestedDurationSeconds,
      aspect: job.aspectPolicy,
      seed: job.seed,
    }))
      el(`generate-${key}`).value = setting ?? "";
    for (const key of ["start-file", "end-file", "start-url", "end-url"])
      el(key).value = "";
    el("generation-panel").open = true;
    el("generation-panel").scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
    message("已复用提示词和设置；请重新提供首帧（及可选尾帧）。尚未提交。");
  });
  fetch("/dashboard/api/generation", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw Error();
      return response.json();
    })
    .then((config) => {
      el("generation-fields").disabled = !config.enabled;
      message(
        config.enabled
          ? "填写后提交；使用现有共享 FIFO 队列。"
          : "服务端尚未启用生成提交。",
      );
    })
    .catch(() => message("暂时无法读取生成配置，请刷新页面。"));
})();
