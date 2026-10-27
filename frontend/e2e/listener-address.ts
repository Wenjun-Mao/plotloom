type ListenerProcess = {
  child: { exitCode: number | null };
  label: string;
  output: () => string;
};

export type ListenerRole = "backend" | "frontend" | "provider";
const receiptPrefix = "PLOTLOOM_E2E_LISTENER ";
const textRetryPreparedPrefix = "PLOTLOOM_E2E_PREPARED ";

/** A receipt describes an already-bound socket, not an available port probe. */
export function listenerOrigin(output: string, role: ListenerRole): string | undefined {
  const lines = output.split("\n").slice(0, -1).filter(line => line.startsWith(receiptPrefix));
  if (!lines.length) return undefined;
  if (lines.length !== 1) throw new Error(`Multiple ${role} listener receipts.`);
  const receipt = JSON.parse(lines[0].slice(receiptPrefix.length));
  if (!receipt || typeof receipt !== "object" || receipt.role !== role || receipt.host !== "127.0.0.1"
    || !Number.isInteger(receipt.port) || receipt.port < 1 || receipt.port > 65535) {
    throw new Error(`Invalid ${role} listener receipt: ${lines[0]}`);
  }
  return `http://${receipt.host}:${receipt.port}`;
}

export async function waitForListenerOrigin(process: ListenerProcess, role: ListenerRole, deadline: number): Promise<string> {
  while (Date.now() < deadline) {
    if (process.child.exitCode !== null) {
      throw new Error(`${process.label} exited before reporting its owned listener (code ${process.child.exitCode}).\n${process.output()}`);
    }
    try {
      const origin = listenerOrigin(process.output(), role);
      if (origin) return origin;
    } catch (error) {
      throw new Error(`${process.label} listener receipt failed: ${String(error)}\n${process.output()}`);
    }
    await new Promise(resolve => setTimeout(resolve, Math.min(50, Math.max(1, deadline - Date.now()))));
  }
  throw new Error(`${process.label} did not report its owned ${role} listener.\n${process.output()}`);
}

/** A text-retry seed is preparation, never an address/readiness assertion. */
export function textRetryPrepared(output: string): boolean {
  const lines = output.split("\n").slice(0, -1);
  const preparations = lines.filter(line => line.startsWith(textRetryPreparedPrefix));
  if (preparations.length > 1) throw new Error("Multiple text-retry preparation receipts.");
  if (!preparations.length) {
    if (lines.some(line => line.startsWith(receiptPrefix))) {
      throw new Error("Text-retry listener preceded preparation.");
    }
    return false;
  }
  const prepared = JSON.parse(preparations[0].slice(textRetryPreparedPrefix.length));
  if (!prepared || typeof prepared !== "object" || Array.isArray(prepared)
    || Object.keys(prepared).sort().join(",") !== "fixture,role,version"
    || prepared.fixture !== "text-retry" || prepared.role !== "backend" || prepared.version !== 1) {
    throw new Error("Invalid text-retry preparation receipt.");
  }
  const firstListener = lines.findIndex(line => line.startsWith(receiptPrefix));
  if (firstListener !== -1 && firstListener < lines.indexOf(preparations[0])) {
    throw new Error("Text-retry listener preceded preparation.");
  }
  return true;
}

/** Preserve the fixture's overall bound; start its existing 25s only after prep. */
export async function waitForPreparedTextRetryOrigin(process: ListenerProcess, setupDeadline: number): Promise<string> {
  let listenerDeadline: number | undefined;
  while (Date.now() < (listenerDeadline ?? setupDeadline)) {
    if (process.child.exitCode !== null) {
      const phase = listenerDeadline === undefined ? "text-retry preparation" : "reporting its owned listener";
      throw new Error(`${process.label} exited before ${phase} (code ${process.child.exitCode}).\n${process.output()}`);
    }
    const output = process.output(), observedAt = Date.now();
    let prepared: boolean;
    try {
      prepared = textRetryPrepared(output);
    } catch (error) {
      throw new Error(`${process.label} preparation receipt failed: ${String(error)}\n${output}`);
    }
    if (prepared) {
      listenerDeadline ??= Math.min(setupDeadline, observedAt + 25_000);
      try {
        const origin = listenerOrigin(output, "backend");
        if (origin) return origin;
      } catch (error) {
        throw new Error(`${process.label} listener receipt failed: ${String(error)}\n${output}`);
      }
    } else if (listenerDeadline !== undefined) {
      throw new Error(`${process.label} accepted preparation is no longer observable.\n${output}`);
    }
    const deadline = listenerDeadline ?? setupDeadline;
    await new Promise(resolve => setTimeout(resolve, Math.min(50, Math.max(1, deadline - Date.now()))));
  }
  if (listenerDeadline !== undefined) throw new Error(`${process.label} did not report its owned backend listener.\n${process.output()}`);
  throw new Error(`${process.label} text-retry preparation exceeded overall setup deadline.\n${process.output()}`);
}
