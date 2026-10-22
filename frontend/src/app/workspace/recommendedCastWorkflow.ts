import type { CastWorkflowObservation } from "./ReviewWorkflowReadContext";
import { reviewWorkflowFailureText } from "./recommendedReviewFailure";

/** Role text approval does not select or generate appearance images. */
export function castWorkflowNextText(read: CastWorkflowObservation | undefined): { text: string } {
  if (!read || read.status === "loading") return { text: "正在读取当前角色设定；读取完成后显示具体下一步。" };
  if (read.status === "failed" || !read.state) return { text: "角色设定读取失败。点击本页「重试加载角色设定」；暂不能确认当前角色状态。" };
  if (read.busy) return { text: "正在处理角色任务，请等待完成；不要重复准备或确认。" };
  if (read.error) return { text: reviewWorkflowFailureText(read.error) };
  if (read.retainedDraft) return { text: "保留角色草稿的版本已变化。先复制需要保留的内容，再点击「丢弃保留草稿」；旧草稿不能直接确认。" };
  const state = read.state;
  if (state.status === "stale") return { text: "角色创作依据需要更新。先处理本页创作依据提示，再重新准备并确认；原设定与图片仍保留。" };
  if (state.status === "reopened" || state.candidate?.status === "ready") {
    if (!read.designValid) return { text: "角色设定的必填设计内容尚未完整。先按表单提示填写「性格特点」与「外观」，再审阅并确认。" };
    return { text: state.status === "reopened" ? "角色修订已打开。审阅修改后点击「保存角色修改」，或点击「取消编辑」；取消不会确认新内容。" : "角色候选已返回。审阅角色文字和原始报告，确认无误后点击「确认使用此角色设定」；外观参考图片需另行制作。" };
  }
  if (state.candidate?.status === "prepared") return { text: "角色任务已准备，尚未交付。按任务区发送状态继续发送或等待结果，再点击「立即检查」；收到候选后才能审阅并确认。" };
  if (state.status === "accepted" && state.acceptedReviewState.status === "current" && state.acceptedCast) return { text: "角色文字已确认。点击「继续：美术参考」整理地点与道具；角色外观图片可在本页单独制作，这项确认不会自动生成图片。" };
  if (state.acceptedReviewState.status === "retained") return { text: "已有角色设定仅保留供参考，并非当前确认。先处理本页创作依据提示，再准备当前版本。" };
  return { text: read.renderStyle ? "角色图像风格已选择。点击「准备角色设定任务」，再发送给文字创作助手；这一步只准备角色文字任务，不生成图片。" : "当前没有角色候选。先选择「角色图像风格」，再点击「准备角色设定任务」；收到角色文字后审阅并确认，不会自动生成图片。" };
}
