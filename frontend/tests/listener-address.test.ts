// @vitest-environment node
import { afterEach, expect, it, vi } from "vitest";
import { listenerOrigin, textRetryPrepared, waitForListenerOrigin, waitForPreparedTextRetryOrigin } from "../e2e/listener-address";

const receipt = (value: unknown) => `PLOTLOOM_E2E_LISTENER ${JSON.stringify(value)}\n`;
const valid = { role: "backend", host: "127.0.0.1", port: 35937 };
const prepared = { role: "backend", fixture: "text-retry", version: 1 };
const preparation = (value: unknown = prepared) => `PLOTLOOM_E2E_PREPARED ${JSON.stringify(value)}\n`;
afterEach(() => vi.useRealTimers());

it("reads a complete role-bound owned address, not partial output or arbitrary log URLs", () => {
  const output = receipt(valid);
  expect(listenerOrigin("Listening at http://127.0.0.1:5173\n", "backend")).toBeUndefined();
  expect(listenerOrigin(output.trimEnd(), "backend")).toBeUndefined();
  expect(listenerOrigin(`startup log\n${output}`, "backend")).toBe("http://127.0.0.1:35937");
});

it.each([
  null, { ...valid, role: "provider" }, { ...valid, host: "0.0.0.0" },
  { ...valid, port: 0 }, { ...valid, port: 65536 }, { ...valid, port: "35937" },
])("rejects invalid or wrong-role receipts: %j", value => {
  expect(() => listenerOrigin(receipt(value), "backend")).toThrow("Invalid backend listener receipt");
});

it("rejects duplicate and malformed receipts", () => {
  expect(() => listenerOrigin(receipt(valid).repeat(2), "backend")).toThrow("Multiple backend");
  expect(() => listenerOrigin("PLOTLOOM_E2E_LISTENER invalid\n", "backend")).toThrow();
});

it("waits for a chunk-complete receipt while retaining a bounded deadline", async () => {
  vi.useFakeTimers();
  let output = receipt(valid).trimEnd();
  const owned = { child: { exitCode: null }, label: "FastAPI", output: () => output };
  const pending = waitForListenerOrigin(owned, "backend", Date.now() + 100);
  output += "\n";
  await vi.advanceTimersByTimeAsync(50);
  await expect(pending).resolves.toBe("http://127.0.0.1:35937");
  output = "original failure evidence";
  const timeout = expect(waitForListenerOrigin(owned, "backend", Date.now() + 100)).rejects.toThrow("original failure evidence");
  await vi.advanceTimersByTimeAsync(100);
  await timeout;
});

it("does not accept a receipt from an exited process and keeps its output", async () => {
  await expect(waitForListenerOrigin({ child: { exitCode: 1 }, label: "FastAPI", output: () => receipt(valid) }, "backend", Date.now() + 100))
    .rejects.toThrow("exited before reporting its owned listener (code 1)");
});

it("preparation is a complete fixture-bound milestone, never a listener address", () => {
  expect(textRetryPrepared(preparation().trimEnd())).toBe(false);
  expect(textRetryPrepared(preparation())).toBe(true);
  expect(listenerOrigin(preparation(), "backend")).toBeUndefined();
  expect(textRetryPrepared(preparation() + receipt(valid))).toBe(true);
  expect(() => textRetryPrepared(receipt(valid))).toThrow("listener preceded preparation");
  expect(() => textRetryPrepared(receipt(valid) + preparation())).toThrow("listener preceded preparation");
  expect(() => textRetryPrepared(preparation().repeat(2))).toThrow("Multiple text-retry");
  expect(() => textRetryPrepared("PLOTLOOM_E2E_PREPARED invalid\n")).toThrow();
});

it.each([
  null, [], { ...prepared, role: "provider" }, { ...prepared, fixture: "other" },
  { ...prepared, version: true }, { ...prepared, version: 2 },
  { role: "backend", fixture: "text-retry" }, { ...prepared, port: 35937 },
])("refuses foreign/malformed preparation instead of granting readiness: %j", async value => {
  const owned = { child: { exitCode: null }, label: "FastAPI", output: () => preparation(value) };
  await expect(waitForPreparedTextRetryOrigin(owned, Date.now() + 45_000))
    .rejects.toThrow("Invalid text-retry preparation receipt");
});

it("allows preparation past 25s while listener acquisition remains inside overall 45s", async () => {
  vi.useFakeTimers();
  const started = Date.now();
  let output = "", settled = false;
  const owned = { child: { exitCode: null }, label: "FastAPI", output: () => output };
  const pending = waitForPreparedTextRetryOrigin(owned, started + 45_000);
  void pending.then(() => { settled = true; });
  setTimeout(() => { output = preparation(); }, 30_000);
  setTimeout(() => { output += receipt(valid); }, 40_000);
  await vi.advanceTimersByTimeAsync(35_000);
  expect(settled).toBe(false);
  await vi.advanceTimersByTimeAsync(5_000);
  await expect(pending).resolves.toBe("http://127.0.0.1:35937");
  expect(Date.now() - started).toBe(40_000);
});

it("missing preparation expires at the existing overall bound with original evidence", async () => {
  vi.useFakeTimers();
  const started = Date.now();
  const owned = { child: { exitCode: null }, label: "FastAPI", output: () => "seed still pending" };
  const result = expect(waitForPreparedTextRetryOrigin(owned, started + 45_000))
    .rejects.toThrow("preparation exceeded overall setup deadline.\nseed still pending");
  await vi.advanceTimersByTimeAsync(45_000);
  await result;
  expect(Date.now() - started).toBe(45_000);
});

it.each([[1_000, 26_000], [30_000, 45_000]])(
  "preserves listener 25s and remaining overall time after preparation at %ims", async (preparedAt, endsAt) => {
    vi.useFakeTimers();
    const started = Date.now();
    let output = "";
    const owned = { child: { exitCode: null }, label: "FastAPI", output: () => output };
    const result = expect(waitForPreparedTextRetryOrigin(owned, started + 45_000))
      .rejects.toThrow("did not report its owned backend listener");
    setTimeout(() => { output = preparation(); }, preparedAt);
    await vi.advanceTimersByTimeAsync(endsAt);
    await result;
    expect(Date.now() - started).toBe(endsAt);
  });

it.each([false, true])("process exit is never accepted before/after preparation: %s", async hasPreparation => {
  vi.useFakeTimers();
  const child = { exitCode: null as number | null };
  const owned = { child, label: "FastAPI", output: () => hasPreparation ? preparation() : "seed pending" };
  const result = expect(waitForPreparedTextRetryOrigin(owned, Date.now() + 45_000))
    .rejects.toThrow(hasPreparation ? "exited before reporting its owned listener (code 7)"
      : "exited before text-retry preparation (code 7)");
  setTimeout(() => { child.exitCode = 7; }, 50);
  await vi.advanceTimersByTimeAsync(100);
  await result;
});

it("does not accept prepared and listener receipts from an already exited owner", async () => {
  const owned = { child: { exitCode: 1 }, label: "FastAPI", output: () => preparation() + receipt(valid) };
  await expect(waitForPreparedTextRetryOrigin(owned, Date.now() + 45_000))
    .rejects.toThrow("exited before text-retry preparation (code 1)");
});

it.each([
  preparation(), preparation({ ...prepared, role: "provider" }), "PLOTLOOM_E2E_PREPARED invalid\n",
])("continues checking preparation after its first observation: %s", async laterPreparation => {
  vi.useFakeTimers();
  let output = preparation();
  const owned = { child: { exitCode: null }, label: "FastAPI", output: () => output };
  const result = expect(waitForPreparedTextRetryOrigin(owned, Date.now() + 45_000))
    .rejects.toThrow("preparation receipt failed");
  setTimeout(() => { output += laterPreparation + receipt(valid); }, 50);
  await vi.advanceTimersByTimeAsync(100);
  await result;
});

it.each(["missing", "reordered"])("refuses %s preparation in a later stdout snapshot", async change => {
  vi.useFakeTimers();
  let output = preparation();
  const owned = { child: { exitCode: null }, label: "FastAPI", output: () => output };
  const result = expect(waitForPreparedTextRetryOrigin(owned, Date.now() + 45_000))
    .rejects.toThrow(change === "missing" ? "accepted preparation is no longer observable"
      : "preparation receipt failed");
  setTimeout(() => { output = change === "missing" ? "startup output changed\n" : receipt(valid) + preparation(); }, 50);
  await vi.advanceTimersByTimeAsync(100);
  await result;
});
