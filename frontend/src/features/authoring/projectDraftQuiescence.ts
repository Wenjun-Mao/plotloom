/**
 * Project-scoped draft drain coordination.
 *
 * Editors register their durable queues and already-admitted mutations. Close
 * drains one project before the server changes admission state;
 * neither timers nor write callbacks escape through window globals.
 */
export type ProjectDraftFlush = () => Promise<boolean>;
export interface ProjectCloseAttempt {
  drain(): Promise<boolean>;
  suspendWrites(): Promise<void>;
  discardUnsent(): Promise<void>;
  canCommit(): boolean;
  finish(): void;
}

export interface ProjectDraftWriterOptions {
  retainOnUnmount?: boolean;
  /** Sent non-editor operations may outlive departure; exclusive drains still join. */
  preserveForDeparture?: () => boolean | Promise<boolean>;
  locallyPreserved?: () => boolean;
  pending?: () => boolean;
  discardUnsent?: () => Promise<void>;
  suspendWrites?: () => Promise<() => void>;
}

export interface ProjectDraftQuiescence {
  register(
    projectId: string,
    writerId: string,
    flush: ProjectDraftFlush,
    options?: ProjectDraftWriterOptions,
  ): () => void;
  flush(projectId: string): Promise<boolean>;
  preserve(projectId: string): Promise<boolean>;
  reconnect(): Promise<void>;
  locallyPreserved(projectId: string): boolean;
  pending(projectId: string): boolean;
  subscribe(listener: () => void): () => void;
  snapshot(): number;
  changed(): void;
  beginClose(projectId: string): ProjectCloseAttempt;
  isClosing(projectId: string): boolean;
  setWriteAdmission(projectId: string, admitted: boolean): void;
  canWrite(projectId: string): boolean;
}

export function createProjectDraftQuiescence(): ProjectDraftQuiescence {
  const writers = new Map<string, Map<string, ProjectDraftWriterOptions & { flush: ProjectDraftFlush }>>();
  const revisions = new Map<string, number>();
  const closing = new Set<string>();
  const writeAdmission = new Map<string, boolean>();
  const listeners = new Set<() => void>();
  let version = 0;
  const changed = () => { version++; listeners.forEach(listener => listener()); };
  const canWrite = (projectId: string) => writeAdmission.get(projectId) !== false;
  const revise = (projectId: string) => { revisions.set(projectId, (revisions.get(projectId) ?? 0) + 1); changed(); };

  return {
    changed,
    async reconnect() {
      await Promise.all([...writers].filter(([id]) => canWrite(id) && !closing.has(id)).map(async ([, owners]) => { await Promise.allSettled([...owners.values()].map(owner => owner.flush())); }));
      changed();
    },
    subscribe(listener) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    snapshot: () => version,
    pending: projectId => [...writers.get(projectId)?.values() ?? []].some(writer => writer.pending?.() ?? false),
    locallyPreserved: projectId => [...writers.get(projectId)?.values() ?? []].every(writer => !writer.pending?.() || writer.locallyPreserved?.() === true),
    async preserve(projectId) {
      const admitted = [...writers.get(projectId)?.values() ?? []];
      const revision = revisions.get(projectId) ?? 0;
      const results = await Promise.all(admitted.map(async writer => {
        if (writer.preserveForDeparture) return writer.preserveForDeparture();
        try { if (await writer.flush()) return true; } catch { /* local preservation still governs departure */ }
        return writer.locallyPreserved?.() === true;
      }));
      return results.every(Boolean) && (revisions.get(projectId) ?? 0) === revision;
    },
    register(projectId, writerId, flush, options) {
      // A Close owns admission from its first drain through the server reply.
      // Editors must not register a new local buffer behind that transition.
      if (closing.has(projectId)) return () => undefined;
      let projectWriters = writers.get(projectId);
      if (!projectWriters) {
        projectWriters = new Map();
        writers.set(projectId, projectWriters);
      }
      projectWriters.set(writerId, { ...options, flush });
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
      if (!canWrite(projectId)) return false;
      const revision = revisions.get(projectId) ?? 0;
      // A writer can unregister while another writer settles. Snapshotting
      // retains the Close boundary for the writers admitted at its start.
      const results = await Promise.all(
        [...projectWriters.values()].map(async (writer) => writer.flush()),
      );
      // A late keystroke swaps its writer registration.  It is deliberately
      // not folded into an already-started Close: leave the project open with
      // its local buffer intact so the author can retry after it settles.
      return results.every(Boolean) && (revisions.get(projectId) ?? 0) === revision;
    },
    beginClose(projectId) {
      if (closing.has(projectId)) throw new Error("project close is already in progress");
      closing.add(projectId);
      let drainedRevision: number | undefined;
      let finished = false;
      let resumeWrites: (() => void)[] = [];
      return {
        async suspendWrites() {
          if (finished) throw new Error("project close is already finished");
          // Delete must wait for admitted writes without saving or discarding
          // newer typing. A rejected deletion resumes these exact queues.
          const results = await Promise.allSettled([...writers.get(projectId)?.values() ?? []].map(writer => writer.suspendWrites?.()));
          for (const result of results) if (result.status === "fulfilled" && result.value) resumeWrites.push(result.value);
          const failed = results.find(result => result.status === "rejected");
          if (failed?.status === "rejected") throw failed.reason;
        },
        async drain() {
          if (finished) return false;
          const projectWriters = writers.get(projectId);
          if (!projectWriters) {
            drainedRevision = revisions.get(projectId) ?? 0;
            return true;
          }
          if (!canWrite(projectId)) return false;
          const revision = revisions.get(projectId) ?? 0;
          const results = await Promise.all([...projectWriters.values()].map((writer) => writer.flush()));
          if (!results.every(Boolean) || (revisions.get(projectId) ?? 0) !== revision) return false;
          drainedRevision = revision;
          return true;
        },
        async discardUnsent() {
          if (finished) throw new Error("project close is already finished");
          resumeWrites = [];
          await Promise.all([...writers.get(projectId)?.values() ?? []].map(writer => writer.discardUnsent?.()));
          writers.delete(projectId);
          revise(projectId);
        },
        canCommit: () => !finished && drainedRevision !== undefined && (revisions.get(projectId) ?? 0) === drainedRevision,
        finish: () => {
          if (finished) return;
          finished = true;
          closing.delete(projectId);
          for (const resume of resumeWrites) resume();
          resumeWrites = [];
        },
      };
    },
    isClosing: (projectId) => closing.has(projectId),
    setWriteAdmission(projectId, admitted) {
      if (canWrite(projectId) === admitted) return;
      writeAdmission.set(projectId, admitted);
      revise(projectId);
    },
    canWrite,
  };
}
