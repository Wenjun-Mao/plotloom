import { useCallback, useEffect, useRef, useState } from "react";
import type { DraftConflictState } from "./useProjectAuthoringPersistence";
import type { WorkspaceOperation } from "./contracts";
import type { WorkspaceSession } from "./useWorkspaceSession";

type ConflictReloadSession = Pick<WorkspaceSession,
  "project" | "capture" | "isCurrent" | "refreshCurrentRoute" | "reloadCanonicalProject" | "registerNavigationCleanup"
>;
type ReloadOwner = { conflict: DraftConflictState; operation: WorkspaceOperation };

/** A read acknowledgement belongs to both one route and one retained conflict. */
export function useDraftConflictReload(input: {
  conflict: DraftConflictState | undefined;
  session: ConflictReloadSession;
  onLoaded: (conflict: DraftConflictState) => void;
}) {
  const latest = useRef(input);
  latest.current = input;
  const owner = useRef<ReloadOwner | undefined>(undefined);
  const [reloading, setReloading] = useState(false);
  const cancel = useCallback(() => { owner.current = undefined; setReloading(false); }, []);
  useEffect(() => input.session.registerNavigationCleanup(cancel), [cancel, input.session.registerNavigationCleanup]);
  useEffect(() => {
    if (owner.current && owner.current.conflict !== input.conflict) cancel();
  }, [cancel, input.conflict]);
  useEffect(() => () => { owner.current = undefined; }, []);

  const reload = useCallback(async (): Promise<boolean> => {
    const source = latest.current;
    const conflict = source.conflict, projectId = source.session.project.id;
    if (!conflict || !projectId || conflict.serverReloaded || owner.current) return false;
    const epoch = source.session.refreshCurrentRoute();
    const pending: ReloadOwner = { conflict, operation: source.session.capture() };
    owner.current = pending;
    setReloading(true);
    try {
      const result = await source.session.reloadCanonicalProject(projectId, epoch);
      if (result !== "loaded" || owner.current !== pending || latest.current.conflict !== conflict
        || !source.session.isCurrent(pending.operation)) return false;
      source.onLoaded(conflict);
      return true;
    } finally {
      if (owner.current === pending) cancel();
    }
  }, [cancel]);

  return { reload, reloading, isPending: () => Boolean(owner.current) };
}
