/** A failed send response can follow a durable export/queue acknowledgement. */
export async function reconcileFailedSend<T>(send: () => Promise<T>, refresh: () => Promise<void>): Promise<T> {
  try {
    return await send();
  } catch (error) {
    // Read the persisted handoff without resending. Keep the dispatch warning
    // even if this read also fails: it carries the unknown/queued retry boundary.
    try { await refresh(); } catch { /* The original dispatch error remains authoritative. */ }
    throw error;
  }
}
