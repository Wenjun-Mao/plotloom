import type { VideoJob } from "../../types";

/** Match playback admission; a retained historical selection is not playable. */
export function isCurrentVideoSelection(job: VideoJob): boolean {
  return job.state === "ingested" && job.current && job.selected
    && Boolean(job.playbackSegment?.current && job.playbackSegment.selected);
}

export function videoNextAction(jobs: readonly VideoJob[], authoredDurationUnits?: number): string {
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
  if (reviewable.length) return "下一步：从原片选择连续帧，生成待审片段。";
  if (jobs.some(job => job.state === "ingested")) {
    return "保留的原片或片段已过期、被拒绝或不再适用。请核对当前分镜与关键帧，按需重新准备视频；旧选择不会进入故事播放。";
  }
  return "下一步：展开准备区，检查关键帧与视频请求。";
}
