type ReadinessProcess = {
  child: { exitCode: number | null };
  label: string;
  output: () => string;
};

/** A pending socket must not bypass the owner's readiness deadline and diagnostics. */
export async function pollHttpReadiness(url: string, process: ReadinessProcess, deadline: number): Promise<void> {
  let lastResponse = "", lastRequestError = "";
  while (Date.now() < deadline) {
    if (process.child.exitCode !== null) {
      throw new Error(`${process.label} exited before becoming ready (code ${process.child.exitCode}).\n${process.output()}`);
    }
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(Math.max(1, deadline - Date.now())) });
      if (response.ok) return;
      lastResponse = `${response.status} ${response.statusText}`;
      lastRequestError = "";
    } catch (error) {
      lastRequestError = error instanceof Error ? error.message : String(error);
    }
    const remaining = deadline - Date.now();
    if (remaining > 0) await new Promise(resolve => setTimeout(resolve, Math.min(100, remaining)));
  }
  const observations = [lastResponse && `last HTTP response: ${lastResponse}`, lastRequestError && `last request error: ${lastRequestError}`].filter(Boolean).join("; ");
  throw new Error(`${process.label} did not become ready at ${url}: ${observations}\n${process.output()}`);
}
