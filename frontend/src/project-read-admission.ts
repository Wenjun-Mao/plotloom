export type ProjectReadTicket = { complete: () => void; cancel: () => void };
type ReadScope = string | null;

/** Own this client's reads; the server remains authoritative for lease safety. */
export class ProjectReadAdmission {
  private readonly reads = new Set<{ scope: ReadScope; settled: Promise<boolean> }>();
  private readonly pauses = new Map<string, { released: Promise<void>; release: () => void }>();

  async acquire(scope: ReadScope, signal?: AbortSignal): Promise<ProjectReadTicket> {
    while (true) {
      signal?.throwIfAborted();
      const blocked = scope === null ? [...this.pauses.values()] : [this.pauses.get(scope)].filter(Boolean);
      if (!blocked.length) break;
      await this.wait(Promise.all(blocked.map(pause => pause!.released)), signal);
    }
    // Register before returning the ticket or starting its transport.
    let settle!: (complete: boolean) => void, finished = false;
    const read = { scope, settled: new Promise<boolean>(resolve => { settle = resolve; }) };
    this.reads.add(read);
    const finish = (complete: boolean) => { if (finished) return; finished = true; this.reads.delete(read); settle(complete); };
    return { complete: () => finish(true), cancel: () => finish(false) };
  }
  async run<T>(scope: ReadScope, operation: () => Promise<T>, signal?: AbortSignal): Promise<T> {
    const ticket = await this.acquire(scope, signal);
    try { const result = await operation(); ticket.complete(); return result; }
    catch (reason) { ticket.cancel(); throw reason; }
  }
  suspend(projectId: string) {
    if (this.pauses.has(projectId)) throw new Error("项目读取已经暂停。");
    let release!: () => void;
    const pause = { released: new Promise<void>(resolve => { release = resolve; }), release: () => release() };
    this.pauses.set(projectId, pause);
    const admitted = [...this.reads].filter(read => read.scope === null || read.scope === projectId);
    let resumed = false;
    return {
      settle: async (timeoutMs = 30_000) => {
        let timer!: ReturnType<typeof setTimeout>;
        try {
          const completed = await Promise.race([
            Promise.all(admitted.map(read => read.settled)).then(results => results.every(Boolean)),
            new Promise<false>(resolve => { timer = setTimeout(() => resolve(false), timeoutMs); }),
          ]);
          return completed && !resumed;
        } finally { clearTimeout(timer); }
      },
      resume: () => { if (resumed) return; resumed = true; this.pauses.delete(projectId); pause.release(); },
    };
  }
  private async wait(pending: Promise<unknown>, signal?: AbortSignal) {
    if (!signal) { await pending; return; }
    signal.throwIfAborted();
    let abort!: () => void;
    const aborted = new Promise<never>((_, reject) => { abort = () => reject(signal.reason); signal.addEventListener("abort", abort, { once: true }); });
    try { await Promise.race([pending, aborted]); }
    finally { signal.removeEventListener("abort", abort); }
  }
}

export function projectReadScope(path: string): ReadScope | undefined {
  if (/^\/projects(?:\?|$)/.test(path)) return null;
  const match = /^\/projects\/([^/?]+)/.exec(path);
  return match ? decodeURIComponent(match[1]) : undefined;
}
