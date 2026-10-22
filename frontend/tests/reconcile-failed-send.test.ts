import { expect, it, vi } from "vitest";
import { reconcileFailedSend } from "../src/features/specialists/reconcileFailedSend";

it("leaves success reconciliation to the caller", async () => {
  const refresh = vi.fn();
  await expect(reconcileFailedSend(async () => "queued", refresh)).resolves.toBe("queued");
  expect(refresh).not.toHaveBeenCalled();
});

it.each([false, true])("refreshes once and preserves the send error if refresh fails: %s", async (refreshFails) => {
  const warning = new Error("queued; open the existing chat, do not resend");
  const send = vi.fn().mockRejectedValue(warning);
  const refresh = vi.fn().mockImplementation(async () => { if (refreshFails) throw new Error("read failed"); });
  await expect(reconcileFailedSend(send, refresh)).rejects.toBe(warning);
  expect(send).toHaveBeenCalledTimes(1);
  expect(refresh).toHaveBeenCalledTimes(1);
});
