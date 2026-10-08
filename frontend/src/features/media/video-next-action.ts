import type { VideoJob } from "../../types";

/** Match playback admission; a retained historical selection is not playable. */
export function isCurrentVideoSelection(job: VideoJob): boolean {
  return job.state === "ingested" && job.lifecycleStatus === "active" && job.inputStatus === "current" && job.current && job.selected
    && Boolean(job.playbackSegment?.current && job.playbackSegment.selected);
}

export function videoNextAction(jobs: readonly VideoJob[], authoredDurationUnits?: number): string {
  if (jobs.some(job => job.lifecycleStatus === "archived")) {
    return "项目已归档：原片与片段证据仍保留，可查看核验通过的预览。准备、审阅、选用和故事播放已停用；如需继续制作，请在项目目录恢复项目后重新核对。";
  }
  if (jobs.some(job => isCurrentVideoSelection(job)
    && (authoredDurationUnits === undefined || job.playbackSegment?.authoredDurationUnits === authoredDurationUnits))) {
    return "当前镜头已有用于故事的片段；可在下方检查路径预览。";
  }
  if (authoredDurationUnits !== undefined && jobs.some(isCurrentVideoSelection)) {
    return "已选择片段的时长与当前镜头不一致。请重新准备并审核匹配的片段；旧选择不会进入故事播放。";
  }
  const reviewable = jobs.filter(job => job.state === "ingested" && job.current && job.reviews.at(-1)?.decision !== "reject");
  if (reviewable.some(job => job.segments?.some(segment => segment.current))) {
    return "下一步：听看待审片段，再明确确认用于故事。";
  }
  if (reviewable.length) return "下一步：从原片选择连续帧，准备播放片段。";
  if (jobs.some(job => job.state === "ingested" && job.inputStatus === "invalid")) {
    return "原片的冻结输入证据未通过核验，不能用于制作。请查看技术详情核实；不会自动生成或选用新视频。";
  }
  if (jobs.some(job => job.state === "ingested" && job.inputStatus === "stale")) {
    return "原片的冻结输入已与当前分镜、关键帧或参考设定不一致。保留的片段仍可查看，但旧选择不会进入故事播放；请核对变更后重新准备视频。";
  }
  if (jobs.some(job => job.state === "ingested" && job.reviews.at(-1)?.decision === "reject")) {
    return "原片已被拒绝，旧审阅记录与核验通过的片段仍可查看。继续使用前须明确重新开放审阅，再核对并选用片段。";
  }
  if (jobs.some(job => job.state === "ingested")) {
    return "原片已保留，但没有可用于当前镜头的片段。请核对审阅与选择状态；旧选择不会进入故事播放。";
  }
  return "下一步：展开准备区，检查关键帧与视频请求。";
}
