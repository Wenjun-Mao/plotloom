import type { Shot, VideoJob } from "../../types";
import { isCurrentVideoSelection, videoNextAction } from "../../features/media/video-next-action";

/** Project the media owner's completed reads; do not fetch or infer from installed shots. */
export function shotWorkflowNextText(input: {
  videoReady: boolean; videoError: boolean; mediaPhase: "loading" | "ready" | "error";
  shot?: Shot; availableShots: number; readOnly: boolean; approvalCurrent: boolean; keyframeReady: boolean;
  identityReviewed: boolean; backendEnabled: boolean | undefined; h3: boolean;
  jobs: readonly VideoJob[]; allRoutesReady: boolean;
}): string {
  if (!input.videoReady) return input.videoError
    ? "镜头视频状态未能读取。点击「重新读取镜头视频状态」，核实后再继续；保留的选择不代表当前播放资格。"
    : "正在读取镜头视频状态；读取完成前不建议进入故事播放。";
  if (input.mediaPhase === "error") return "媒体证据读取失败。展开「准备与参考 · 图片、角色、导入」，点击「重试媒体读取」，核实角色参考与关键帧后再继续。";
  if (input.mediaPhase !== "ready") return "正在读取当前镜头的媒体证据；读取完成后再判断下一步。";
  if (!input.availableShots) return "当前分镜没有镜头，不能选择或制作媒体。先返回「分镜评审」，完成分镜确认与投产安装，再打开镜头工作台。";
  if (!input.shot) return "在「当前镜头」下拉框选择一个镜头，再查看对应制作与审阅状态。";
  if (input.readOnly) return "当前镜头制作控件暂不可编辑。先核对本页的分镜草稿与只读提示，不要准备或提交新任务。";
  if (input.allRoutesReady) return "所有完整路线已有当前选定的播放片段。点击「检查交互式播放」，实际核对问题、选项与每个结局；素材选择不代表播放已验收。";
  const jobs = input.jobs;
  if (jobs.some(job => isCurrentVideoSelection(job) && job.playbackSegment?.authoredDurationUnits === input.shot!.durationUnits)) {
    return "当前镜头已有用于故事的片段，但完整路线仍缺少已选片段。用「当前镜头」切换到未完成的镜头；可在下方「故事播放」核对缺失列表。";
  }
  if (jobs.some(job => job.state === "outcome_unknown" || job.state === "dispatching")) return "视频提交结果尚未确定。查看「请求与原片」保留的请求状态，不要重新提交或另建任务。";
  if (jobs.some(job => job.state === "submitted" || job.state === "retrieve_needed")) return "当前镜头的视频请求已提交。点击对应请求的「获取结果」；获取结果不会自动审阅或用于故事。";
  if (jobs.some(job => job.state === "prepared" && job.current)) return "当前镜头的视频请求已冻结，尚未提交。核对「请求与原片」，再点击「提交一次」；不要重复准备。";
  const reviewable = jobs.filter(job => job.state === "ingested" && job.current && job.reviews.at(-1)?.decision !== "reject");
  if (reviewable.some(job => job.segments?.some(segment => segment.current))) return "点击「预览片段」，完整听看待审片段并填写审阅，再点击「确认用于故事」。这只选用当前镜头，不代表整条路线完成。";
  if (reviewable.length) return "原片已返回。点击「调整片段」，选择连续帧并点击「准备播放片段」；准备只截取预览，不会自动用于故事。";
  if (jobs.some(job => job.state === "ingested")) return videoNextAction(jobs, input.shot.durationUnits);
  if (!input.approvalCurrent) return "当前分镜没有有效批准。点击「当前镜头」旁的「前往分镜审核」，完成当前版本的分镜审核。";
  if (!input.keyframeReady) return "当前镜头缺少可用的审核关键帧。展开「准备与参考 · 图片、角色、导入」制作图片，再点击「查看关键帧」审阅并选用；图片返回不会自动成为关键帧。";
  if (!input.identityReviewed && input.shot.characterIds.length) return "当前关键帧还缺少有效的人物视觉复核。展开「准备与参考 · 图片、角色、导入」，完成「跨镜头同一人物视觉复核」并点击「记录视觉复核」。";
  if (input.backendEnabled === false) return "当前运行时的视频生成服务未配置，不能准备或提交新视频。现有关键帧与审核仍保留；先完成服务配置，再继续原片制作。";
  if (input.backendEnabled !== true) return "视频生成服务状态尚未核实，暂不建议准备新请求。";
  return input.h3
    ? "展开「准备或生成新的 MiniMax H3 原片」，核对规格与首末帧决定，再展开「审阅英文生成说明」点击「读取当前来源」。审阅并预览说明后，才能冻结原片请求。"
    : "点击「准备原片」，核对请求与关键帧，再点击「准备新视频任务（冻结当前审核关键帧）」。准备不会自动提交或选用视频。";
}
