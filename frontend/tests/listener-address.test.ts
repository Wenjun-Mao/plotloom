// @vitest-environment node
import { afterEach, expect, it, vi } from "vitest";
import { listenerOrigin, waitForListenerOrigin } from "../e2e/listener-address";

const receipt = (value: unknown) => `PLOTLOOM_E2E_LISTENER ${JSON.stringify(value)}\n`;
const valid = { role: "backend", host: "127.0.0.1", port: 35937 };
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
