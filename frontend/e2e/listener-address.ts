type ListenerProcess = {
  child: { exitCode: number | null };
  label: string;
  output: () => string;
};

export type ListenerRole = "backend" | "frontend" | "provider";
const receiptPrefix = "PLOTLOOM_E2E_LISTENER ";

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
