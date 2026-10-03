import type { ImageJob } from "../../../types";

export function shotImageJobs(jobs: ImageJob[], shotId?: string): ImageJob[] {
  if (!shotId) return jobs;
  return jobs.filter(job => job.request.frozenSnapshot?.shot?.id === shotId);
}
