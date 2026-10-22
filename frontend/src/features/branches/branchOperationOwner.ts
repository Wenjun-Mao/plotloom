import type { ProjectDraftQuiescence } from "../authoring/projectDraftQuiescence";

export interface BranchOperationSnapshot {
  pending: boolean;
  version: number;
  error: string;
  unconfirmed: boolean;
}
export interface BranchOperationOwner {
  snapshot(projectId: string): BranchOperationSnapshot;
  subscribe(projectId: string, listener: () => void): () => void;
  run(projectId: string, operation: () => Promise<unknown>): Promise<boolean>;
  acknowledgeRead(projectId: string, version: number): void;
}
interface Entry {
  state: BranchOperationSnapshot;
  listeners: Set<() => void>;
  flight?: Promise<boolean>;
  registered: boolean;
}

/** Sent branch mutations belong to the workspace, not the mounted Source page. */
export function createBranchOperationOwner(quiescence: ProjectDraftQuiescence): BranchOperationOwner {
  const entries = new Map<string, Entry>();
  const entryFor = (projectId: string): Entry => {
    let entry = entries.get(projectId);
    if (!entry) {
      entry = { state: { pending: false, version: 0, error: "", unconfirmed: false }, listeners: new Set(), registered: false };
      entries.set(projectId, entry);
    }
    return entry;
  };
  const publish = (entry: Entry, patch: Partial<BranchOperationSnapshot>) => {
    entry.state = { ...entry.state, ...patch };
    for (const listener of entry.listeners) listener();
  };
  const settled = async (entry: Entry) => {
    // Lifecycle suspends reads before draining. Join the sent POST only;
    // waiting for its projection GET here would deadlock behind that suspension.
    if (entry.flight) await entry.flight;
    return !entry.state.unconfirmed;
  };
  const joinOrRefuse = async (entry: Entry) => {
    if (!await settled(entry)) throw new Error("分支建议操作结果尚未确认；请先重新读取建议任务，再关闭、删除或创建快照。");
  };
  return {
    snapshot: projectId => entryFor(projectId).state,
    subscribe(projectId, listener) {
      const entry = entryFor(projectId);
      entry.listeners.add(listener);
      return () => { entry.listeners.delete(listener); };
    },
    acknowledgeRead(projectId, version) {
      const entry = entryFor(projectId);
      if (!entry.state.pending && entry.state.version === version && entry.state.unconfirmed) publish(entry, { unconfirmed: false });
    },
    async run(projectId, operation) {
      const entry = entryFor(projectId);
      if (entry.state.pending || entry.state.unconfirmed || quiescence.isClosing(projectId) || !quiescence.canWrite(projectId)) return false;
      if (!entry.registered) {
        quiescence.register(projectId, "branch_operations", async () => { await joinOrRefuse(entry); return true; }, {
          retainOnUnmount: true,
          discardUnsent: async () => { await joinOrRefuse(entry); entry.registered = false; },
          suspendWrites: async () => { await joinOrRefuse(entry); return () => undefined; },
        });
        entry.registered = true;
      }
      const flight = Promise.resolve().then(operation).then(
        () => { publish(entry, { pending: false, version: entry.state.version + 1, unconfirmed: false }); return true; },
        reason => {
          publish(entry, { pending: false, version: entry.state.version + 1, unconfirmed: true,
            error: reason instanceof Error ? reason.message : "剧情分支建议操作未能确认，请重新读取任务。" });
          return false;
        },
      );
      entry.flight = flight;
      // A subscriber can begin lifecycle drainage synchronously on notification.
      publish(entry, { pending: true, error: "" });
      try { return await flight; }
      finally { if (entry.flight === flight) entry.flight = undefined; }
    },
  };
}
