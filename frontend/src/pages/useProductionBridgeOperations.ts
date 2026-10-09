import { useContext, useRef, useSyncExternalStore } from "react";
import { ReviewDraftContext } from "../features/authoring/ReviewDraftContext";
import type { ProjectDraftQuiescence } from "../features/authoring/projectDraftQuiescence";

function createOperations(quiescence?: ProjectDraftQuiescence) {
  const pending = new Map<string, { ticket: object; unregister: () => void }>();
  const epochs = new Map<string, number>();
  const listeners = new Set<() => void>();
  let revision = 0;
  const notify = () => { revision += 1; listeners.forEach(listener => listener()); };
  const available = (projectId: string) => !pending.has(projectId) && !quiescence?.isClosing(projectId)
    && (!quiescence || quiescence.canWrite(projectId));
  return {
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    snapshot: () => revision,
    busy: (projectId: string) => pending.has(projectId),
    epoch: (projectId: string) => epochs.get(projectId) ?? 0,
    available,
    owns: (projectId: string, ticket: object) => pending.get(projectId)?.ticket === ticket,
    begin(projectId: string) {
      if (!available(projectId)) return;
      const ticket = {};
      // This writer belongs to the admitted promise, not a component mount.
      const unregister = quiescence?.register(projectId, `production_bridge_pending:${crypto.randomUUID()}`, async () => {
        throw new Error("投产提案审阅操作未完成；请等待该操作结束后关闭项目。");
      }) ?? (() => undefined);
      pending.set(projectId, { ticket, unregister }); notify();
      return ticket;
    },
    finish(projectId: string, ticket: object, invalidateReads: boolean) {
      const operation = pending.get(projectId);
      if (operation?.ticket !== ticket) return;
      if (invalidateReads) epochs.set(projectId, (epochs.get(projectId) ?? 0) + 1);
      operation.unregister(); pending.delete(projectId); notify();
    },
  };
}
type Operations = ReturnType<typeof createOperations>;
const projectOwners = new WeakMap<ProjectDraftQuiescence, Operations>();

/** Share pending occupancy across mounts; discard response authority separately. */
export function useProductionBridgeOperations() {
  const context = useContext(ReviewDraftContext);
  const local = useRef<Operations | undefined>(undefined);
  if (!local.current) local.current = createOperations();
  let operations = local.current;
  if (context) {
    let shared = projectOwners.get(context.quiescence);
    if (!shared) { shared = createOperations(context.quiescence); projectOwners.set(context.quiescence, shared); }
    operations = shared;
  }
  useSyncExternalStore(operations.subscribe, operations.snapshot);
  return operations;
}
