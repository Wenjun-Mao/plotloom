import type { VideoJob } from "../../types";

/** Invalid persisted evidence stays raw; this guard only permits safe display reads. */
export function frozenVideoSnapshot(job: VideoJob): Record<string, unknown> | null {
  return job.snapshot !== null && typeof job.snapshot === "object" && !Array.isArray(job.snapshot)
    ? job.snapshot as Record<string, unknown> : null;
}
