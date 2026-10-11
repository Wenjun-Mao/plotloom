import type { ScriptWorkflowObservation } from "./ScriptWorkflowReadContext";

/** The active ScriptPanel owns currentness, operation state and draft protection. */
export function scriptWorkflowNextText(read: ScriptWorkflowObservation | undefined): { text: string } {
  if (!read || read.status === "loading") return { text: "正在读取当前剧本状态；读取完成后显示具体下一步。" };
  if (read.status === "failed" || !read.state) return { text: "剧本状态读取失败。点击本页「重试加载剧本」；暂不能确认当前剧本。" };
  if (read.busy) return { text: "正在处理剧本任务，请等待完成；不要重复准备或确认。" };
  if (read.dirty) return { text: "章节有未保存修改。先保存或明确舍弃章节草稿，再继续。" };
  const state = read.state;
  if (state.status === "reopened" || state.acceptedReviewState.status === "reopened") return { text: "剧本修订已打开。选择「编辑章节」，修改后点击「保存此章节，不覆盖其他章节」。" };
  if (state.status === "stale") return { text: "剧本依据已变化，保留内容不代表当前确认。先按本页来源与审阅提示处理，再重新准备或确认。" };
  if (state.candidate?.status === "ready") return { text: "剧本候选已返回。点击「查看待审阅剧本」，审阅完整分支与结局后点击「确认使用此剧本」；不会自动生成分镜或影片。" };
  if (state.candidate?.status === "prepared") return { text: "剧本任务已准备，尚未交付。按任务区发送状态继续发送或等待结果，再检查交付；收到剧本后才能审阅并确认。" };
  if (state.acceptedReviewState.status === "retained") return { text: "剧本依据已变化，保留内容不代表当前确认。先按本页来源与审阅提示处理，再重新准备或确认。" };
  if (state.acceptedReviewState.status === "current" && state.acceptedScript) return { text: "完整剧本已确认。点击「继续：分镜评审」；剧本确认不代表分镜或实际播放已通过。" };
  return { text: "当前没有剧本候选。点击「准备剧本任务」，再发送给文字创作助手；收到剧本后审阅并确认。准备任务不会自动生成剧本或影片。" };
}
