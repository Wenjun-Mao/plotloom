import type { VideoJob } from "../../types";
import { isCurrentVideoSelection } from "./video-next-action";

const retrievalErrorLabels: Record<string, string> = {
  h3_output_download_failed: "读取到已知预测，但本次下载原片失败。可点击“获取结果”继续读取同一预测。",
  h3_output_media_probe_failed: "原片已下载，但媒体探测或解码失败。可点击“获取结果”继续读取同一预测。",
  h3_output_contract_failed: "原片已下载并读取，但未通过冻结的视频输出规格核验。可点击“获取结果”继续读取同一预测。",
  h3_output_profile_mismatch: "已读取原片，但未通过冻结的视频输出规格核验。可点击“获取结果”继续读取同一预测。",
  h3_prediction_contract_failed: "H3 预测信息未通过冻结输出规格核验；尚未确认原片已下载。可点击“获取结果”继续核对同一预测。",
  h3_prediction_profile_mismatch: "H3 预测信息与冻结的视频输出规格不一致；尚未确认原片已下载。可点击“获取结果”继续核对同一预测。",
  h3_output_reference_invalid: "H3 返回的原片引用未通过安全核验，尚未开始下载。可点击“获取结果”继续核对同一预测。",
  audio_track_missing: "已读取原片，但没有检测到音轨；冻结的视频输出规格核验未通过。可点击“获取结果”继续读取同一预测。",
  h3_gateway_output_expired: "已知 H3 预测报告原片输出不可用或已过期，尚未下载。可点击“获取结果”继续核对同一预测。",
  retrieval_or_probe_failed: "获取结果未完成；这条历史记录没有保留失败阶段，无法确认是远端读取、下载还是媒体探测失败。",
  dispatch_outcome_unknown: "原视频提交结果尚未核实；请勿重复提交。",
  remote_outcome_unknown: "已有预测的远端状态尚无法确认；请勿重复提交。",
  remote_prediction_failed: "远端预测已明确报告失败。",
  restart_dispatch_outcome_unknown: "服务重启后仍无法确认原提交结果；请勿重复提交。",
  h3_gateway_credential_unavailable: "H3 网关凭据当前不可用；任务仍保留原提交状态。",
  h3_gateway_profile_unavailable: "冻结的 H3 输出规格当前不可用；任务仍保留原提交状态。",
};

const dispatchPhaseLabels: Record<string, string> = {
  keyframe_read: "读取关键帧",
  upload: "上传输入",
  request_compile: "编译请求",
  submit: "提交任务",
  submit_response_parse: "读取提交响应",
  poll: "读取远端状态",
};
const dispatchCodeLabels: Record<string, string> = {
  transport_unavailable: "传输不可用",
  http_rejected: "HTTP 请求被拒绝",
  invalid_json: "响应 JSON 无效",
  invalid_envelope: "响应格式无效",
  invalid_upload_url: "上传地址无效",
  local_precondition_failed: "本地前置条件未满足",
};

/** Show only allowlisted diagnostics; persisted values may come from older records. */
export function videoJobErrorLabel(error: string): string {
  const known = Object.prototype.hasOwnProperty.call(retrievalErrorLabels, error)
    ? retrievalErrorLabels[error]
    : undefined;
  if (known) return known;
  const dispatch = /^dispatch_(keyframe_read|upload|request_compile|submit|submit_response_parse|poll)_(transport_unavailable|http_rejected|invalid_json|invalid_envelope|invalid_upload_url|local_precondition_failed)(?:_status_(\d{3}))?$/.exec(error);
  if (dispatch) {
    const phase = dispatchPhaseLabels[dispatch[1]!];
    const code = dispatchCodeLabels[dispatch[2]!];
    const status = dispatch[3] ? `（HTTP ${dispatch[3]}）` : "";
    return `提交阶段“${phase}”报告${code}${status}；远端结果尚未核实，请勿重复提交。`;
  }
  return "任务保留了错误记录，但没有可安全展示的具体诊断。";
}

const stateLabels: Record<VideoJob["state"], string> = {
  prepared: "已准备 · 尚未提交",
  dispatching: "正在提交 · 请勿重复操作",
  submitted: "已提交 · 等待结果",
  outcome_unknown: "提交结果待核实 · 请勿重复提交",
  retrieve_needed: "结果待获取",
  ingested: "待审原片",
  discard_pending: "删除待完成",
  discarded: "已删除",
  cancelled: "已取消",
  failed: "生成未完成",
};

/** Request progress is distinct from selection and retained-media evidence. */
export function videoJobLabel(job: VideoJob): string {
  if (isCurrentVideoSelection(job)) return "已选择片段";
  if (job.state === "ingested") {
    if (!job.current) return "保留原片";
    return job.selected ? "已选原片 · 片段待确认" : "待审原片";
  }
  return stateLabels[job.state];
}
