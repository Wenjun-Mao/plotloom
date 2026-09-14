/**
 * Project-scoped draft drain coordination.
 *
 * Editors register only their own durable write queue.  Close asks this
 * contract to drain one project before the server changes admission state;
 * neither timers nor write callbacks escape through window globals.
 */
export type ProjectDraftFlush = () => Promise<boolean>;
export interface ProjectCloseAttempt {
  drain(): Promise<boolean>;
  canCommit(): boolean;
  finish(): void;
}

export interface ProjectDraftQuiescence {
  register(
    projectId: string,
    writerId: string,
    flush: ProjectDraftFlush,
    options?: { retainOnUnmount?: boolean },
  ): () => void;
  flush(projectId: string): Promise<boolean>;
  beginClose(projectId: string): ProjectCloseAttempt;
  isClosing(projectId: string): boolean;
}

export function createProjectDraftQuiescence(): ProjectDraftQuiescence {
  const writers = new Map<string, Map<string, { flush: ProjectDraftFlush; retainOnUnmount: boolean }>>();
  const revisions = new Map<string, number>();
  const closing = new Set<string>();
  const revise = (projectId: string) =>
    revisions.set(projectId, (revisions.get(projectId) ?? 0) + 1);

  return {
    register(projectId, writerId, flush, options) {
      // A Close owns admission from its first drain through the server reply.
      // Editors must not register a new local buffer behind that transition.
      if (closing.has(projectId)) return () => undefined;
      let projectWriters = writers.get(projectId);
      if (!projectWriters) {
        projectWriters = new Map();
        writers.set(projectId, projectWriters);
      }
      projectWriters.set(writerId, { flush, retainOnUnmount: options?.retainOnUnmount === true });
      revise(projectId);
      return () => {
        const current = writers.get(projectId);
        const registered = current?.get(writerId);
        if (!current || !registered || registered.flush !== flush || registered.retainOnUnmount) return;
        current.delete(writerId);
        if (!current.size) writers.delete(projectId);
        revise(projectId);
      };
    },
    async flush(projectId) {
      const projectWriters = writers.get(projectId);
      if (!projectWriters) return true;
      const revision = revisions.get(projectId) ?? 0;
      // A writer can unregister while another writer settles. Snapshotting
      // retains the Close boundary for the writers admitted at its start.
      const results = await Promise.all(
        [...projectWriters.values()].map(async (writer) => writer.flush()),
      );
      // A late keystroke swaps its writer registration.  It is deliberately
      // not folded into an already-started Close: leave the project open with
      // its local buffer intact so the author can retry after it settles.
      return results.every(Boolean) && revisions.get(projectId) === revision;
    },
    beginClose(projectId) {
      if (closing.has(projectId)) throw new Error("project close is already in progress");
      closing.add(projectId);
      let drainedRevision: number | undefined;
      let finished = false;
      return {
        async drain() {
          const projectWriters = writers.get(projectId);
          if (!projectWriters) {
            drainedRevision = revisions.get(projectId) ?? 0;
            return true;
          }
          const revision = revisions.get(projectId) ?? 0;
          const results = await Promise.all([...projectWriters.values()].map((writer) => writer.flush()));
          if (!results.every(Boolean) || revisions.get(projectId) !== revision) return false;
          drainedRevision = revision;
          return true;
        },
        canCommit: () => drainedRevision !== undefined && revisions.get(projectId) === drainedRevision,
        finish: () => {
          if (finished) return;
          finished = true;
          closing.delete(projectId);
        },
      };
    },
    isClosing: (projectId) => closing.has(projectId),
  };
}
