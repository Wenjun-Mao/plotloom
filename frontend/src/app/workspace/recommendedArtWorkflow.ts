import type { ArtWorkflowObservation } from "./ReviewWorkflowReadContext";
import { reviewWorkflowFailureText } from "./recommendedReviewFailure";

/** Art text acceptance and optional reference images remain separate operations. */
export function artWorkflowNextText(read: ArtWorkflowObservation | undefined): { text: string } {
  if (!read || read.status === "loading") return { text: "正在读取当前美术状态；读取完成后显示具体下一步。" };
  if (read.status === "failed" || !read.state) return { text: "美术状态读取失败。点击本页「重试加载美术参考」；暂不能确认当前美术设定。" };
  if (read.busy) return { text: "正在处理美术任务，请等待完成；不要重复准备或确认。" };
  if (read.error) return { text: reviewWorkflowFailureText(read.error) };
  const state = read.state;
  if (read.retainedDraft) return { text: "保留了基于旧版本的美术草稿。点击「舍弃美术草稿」或「用当前版本替换草稿」后，再审阅当前内容；旧草稿不能直接确认。" };
  if (state.status === "stale") return { text: "美术依据已变化。先处理本页创作依据提示，再重新准备并确认；已有设定和图片仍保留。" };
  if (state.status === "reopened") return { text: "美术修订已打开。点击「查看/编辑 art.json（稳定地点和道具 ID 不可替换）」，审阅修改后点击「保存重新打开的美术」。" };
  if (state.candidate?.status === "ready") return { text: "美术候选已返回。审阅地点、道具及原始报告，确认无误后点击「确认使用此美术提案」；不会自动生成参考图片。" };
  if (state.candidate?.status === "prepared") return { text: "美术任务已准备，尚未交付。按任务区发送状态继续发送或等待结果，再点击「立即检查」；收到候选后才能审阅并确认。" };
  if (state.acceptedReviewState.status === "current" && state.acceptedArt) return { text: "地点与道具设定已确认。点击「继续：剧本」；参考图片可在本页单独制作，这项确认不会自动生成图片或影片。" };
  if (state.acceptedReviewState.status === "retained") return { text: "已有美术设定仅保留供参考，并非当前确认。先处理本页创作依据提示，再准备当前版本。" };
  return { text: read.renderStyle ? "美术风格已选择。点击「准备美术设定任务」，再发送给文字创作助手；这一步只准备文字设定任务，不生成图片。" : "当前没有美术候选。先选择「美术风格」，再点击「准备美术设定任务」；收到地点与道具设定后审阅并确认，不会自动生成图片。" };
}
