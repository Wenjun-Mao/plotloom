import type { BridgeWorkflowObservation, StoryboardWorkflowObservation } from "./ReviewWorkflowReadContext";
import { reviewWorkflowFailureText } from "./recommendedReviewFailure";
import { bridgeCut } from "../../production-bridge-handoff";

/** Observe the two existing owners; approval, projection and media remain separate. */
export function storyboardWorkflowNextText(read?: StoryboardWorkflowObservation, bridge?: BridgeWorkflowObservation): { text: string } {
  if (!read || read.status === "loading") return { text: "正在读取当前分镜评审状态；读取完成后显示具体下一步。" };
  if (read.status === "failed" || !read.state) return { text: "分镜评审状态读取失败。点击本页「重试加载分镜评审」；暂不能确认或投产。" };
  if (read.busy) return { text: "正在处理分镜评审任务，请等待完成；不要重复准备或确认。" };
  if (read.error) return { text: reviewWorkflowFailureText(read.error) };
  const state = read.state;
  if (state.status === "stale") return { text: "分镜评审依据已变化。按本页来源提示处理；旧方案保留，不代表当前确认。" };
  if (state.candidate?.status === "ready") return { text: "分镜候选已返回。点击「查看待审阅分镜」，审阅动作、镜头与时长后点击「确认此分镜评审方案」；不会自动建立正式镜头或生成媒体。" };
  if (state.candidate?.status === "prepared") return { text: "分镜任务已准备，尚未交付。按任务区发送状态继续发送或等待结果，再检查交付；收到分镜后才能审阅并确认。" };
  if (state.acceptedReviewState.status === "retained") return { text: "已确认分镜仅作为保留证据。先按本页来源提示处理，再准备并审阅当前方案。" };
  if (state.acceptedReviewState.status === "current" && state.acceptedReview) return bridgeNextText(bridge);
  return { text: "当前没有分镜候选。点击「准备分镜任务」，再发送给文字创作助手；收到分镜后审阅并确认。准备不会自动生成图片或影片。" };
}

function bridgeNextText(read?: BridgeWorkflowObservation): { text: string } {
  if (!read || read.status === "loading") return { text: "分镜方案已确认。正在读取对应投产提案；确认分镜本身不会建立正式镜头或生成媒体。" };
  if (read.status === "failed" || !read.state) return { text: "投产提案读取失败。点击下方投产提案区「重试加载」；保留内容暂不能确认。" };
  if (read.busy) return { text: "正在处理投产提案，请等待完成；不要重复准备、发送或确认。" };
  if (read.error) return { text: "投产提案操作未完成。先查看下方错误说明，再继续；不要重复发送任务。" };
  if (read.dirty) return { text: "投产提案有未保存编辑。完成「戏剧意图整包审阅」与「逐项审阅内容的呈现方式」，分别保存后再确认投产。" };
  if (read.blocked) return { text: "投产提案暂不可操作。请先核对本页分镜确认状态与提案来源提示。" };
  const state = read.state, proposal = state.proposal, job = state.intentJob;
  if (state.status === "accepted" && state.installation?.status === "current" && !state.installation.staleReasons.length) return { text: read.canonicalReady
    ? read.canOpenShot && state.installation.cuts.some(cut => bridgeCut(cut) !== undefined)
      ? "投产提案已确认，场景与镜头数据已建立。点击下方「继续：打开第一个镜头」；逐镜头批准、参考图、关键帧与影片仍需单独制作和审核。"
      : "投产提案已确认。点击左侧「创作工作台」，选择需拍摄节点的「制作」标签，查看已建立的镜头；实际媒体仍需单独制作和审核。"
    : "投产已确认，正在核对正式镜头数据；请等待刷新完成，不要重复确认。" };
  if (job?.transport === "text_api" && ["queued", "dispatched", "outcome_unknown"].includes(job.status)) return { text: job.status === "queued"
    ? state.intentGeneration.status === "available" ? "API 戏剧意图任务正在排队。点击「继续排队任务」继续原任务；不要另建重复任务。"
      : "API 戏剧意图任务正在排队，但当前 API 不可用。打开「生成助手设置」核对配置，再继续原任务；不要另建重复任务。"
    : "API 戏剧意图任务尚未完成。查看下方推断状态，等待或核对原任务；不要另建重复任务。" };
  if (job?.transport === "codex_native" && (["dispatched", "outcome_unknown"].includes(job.status) || job.status === "cancelled" && !job.responseHash && state.nativeIntentTask?.state !== "prepared")) return { text: "戏剧意图任务仍待核对。点击「检查原任务交付」，检查同一任务；不要重新发送或准备替代任务。" };
  if (job?.transport === "codex_native" && job.status === "queued" && state.nativeIntentTask?.state === "prepared") return { text: state.status === "stale"
    ? "戏剧意图任务的提案来源已变化，不能发送旧任务。点击「取消 Codex 意图任务」，再按当前来源重新准备提案。"
    : state.nativeIntentGeneration.status === "available" ? "戏剧意图任务已冻结，尚未发送。点击「发送给 Codex 文字助手」；交付后仍需审阅并保存整包。"
      : "戏剧意图任务已冻结，但当前 Codex 文字助手不可用。打开「生成助手设置」核对助手配置；不要重复准备或发送。" };
  if (!proposal || state.status === "stale" || state.status === "accepted") {
    if (state.preparation.status === "unavailable") return { text: "分镜方案已确认，但当前不能准备投产提案。展开下方「提案准备诊断」，处理其中实际阻碍；已有内容和媒体保留。" };
    return { text: `分镜方案已确认。点击下方「${state.installation ? "准备重建提案" : proposal ? "重新准备投产提案" : "准备投产提案"}」；提案仍需独立审阅和确认，不会生成媒体。` };
  }
  if (proposal.intentPackage.reviewState !== "author_saved") return { text: proposal.intentPackage.reviewState === "model_suggested"
    ? "戏剧意图建议已返回。审阅「戏剧意图整包审阅」中的全部条目后点击「保存戏剧意图整包」；保存建议不代表已投产。"
    : state.nativeIntentGeneration.status === "available" ? "投产提案已准备。点击「准备 Codex 戏剧意图任务」，再单独发送；也可在「戏剧意图整包审阅」填写并保存作者意图。"
      : "投产提案已准备。填写「戏剧意图整包审阅」的全部作者意图，再点击「保存戏剧意图整包」。" };
  if (!proposal.presentation.reviewed) return { text: "戏剧意图已保存。完成「逐项审阅内容的呈现方式」，勾选已逐项审阅后点击「保存呈现方式审阅」。" };
  if (!proposal.installable) return { text: "意图与呈现方式已审阅。按投产提案区的具体冲突提示处理；暂不能点击「确认投产提案」。" };
  return { text: "投产提案已完成审阅。点击「确认投产提案」建立正式场景与镜头；不会自动批准镜头或生成图片、影片。" };
}
