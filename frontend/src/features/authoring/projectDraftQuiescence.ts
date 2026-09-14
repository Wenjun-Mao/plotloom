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
  register(projectId: string, writerId: string, flush: ProjectDraftFlush): () => void;
  flush(projectId: string): Promise<boolean>;
  beginClose(projectId: string): ProjectCloseAttempt;
}

export function createProjectDraftQuiescence(): ProjectDraftQuiescence {
  const writers = new Map<string, Map<string, ProjectDraftFlush>>();
  const revisions = new Map<string, number>();
  const revise = (projectId: string) =>
    revisions.set(projectId, (revisions.get(projectId) ?? 0) + 1);

  return {
    register(projectId, writerId, flush) {
      let projectWriters = writers.get(projectId);
      if (!projectWriters) {
        projectWriters = new Map();
        writers.set(projectId, projectWriters);
      }
      projectWriters.set(writerId, flush);
      revise(projectId);
      return () => {
        const current = writers.get(projectId);
        if (!current || current.get(writerId) !== flush) return;
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
        [...projectWriters.values()].map(async (writer) => writer()),
      );
      // A late keystroke swaps its writer registration.  It is deliberately
      // not folded into an already-started Close: leave the project open with
      // its local buffer intact so the author can retry after it settles.
      return results.every(Boolean) && revisions.get(projectId) === revision;
    },
    beginClose(projectId) {
      let drainedRevision: number | undefined;
      return {
        async drain() {
          const projectWriters = writers.get(projectId);
          if (!projectWriters) {
            drainedRevision = revisions.get(projectId) ?? 0;
            return true;
          }
          const revision = revisions.get(projectId) ?? 0;
          const results = await Promise.all([...projectWriters.values()].map((writer) => writer()));
          if (!results.every(Boolean) || revisions.get(projectId) !== revision) return false;
          drainedRevision = revision;
          return true;
        },
        canCommit: () => drainedRevision !== undefined && revisions.get(projectId) === drainedRevision,
        finish: () => undefined,
      };
    },
  };
}
