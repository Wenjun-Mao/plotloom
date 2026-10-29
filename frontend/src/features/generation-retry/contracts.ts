export type GenerationRetryStatus = {
  retryCount: number;
  automaticRetriesUsed?: number;
  automaticRetryLimit: number | null;
  currentJobId: string | null;
  currentAttemptId: string | null;
  predecessorJobIds: string[];
  state: "ready" | "running" | "retry_pending" | "exhausted" | "stopped";
  possiblePriorCost: boolean;
};
