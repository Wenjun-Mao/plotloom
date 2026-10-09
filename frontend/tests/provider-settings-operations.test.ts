import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { fallbackProfiles, useTextProviderProfiles } from "../src/app/workspace/useTextProviderProfiles";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root, host: HTMLDivElement, profiles: ReturnType<typeof useTextProviderProfiles>;
const setBusy = vi.fn(), setError = vi.fn();
const describeError = (error: unknown) => error instanceof Error ? error.message : String(error);
function Harness() { profiles = useTextProviderProfiles(setBusy, setError, describeError); return null; }
function deferred<T>() {
  let resolve!: (value: T) => void, reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
beforeEach(async () => {
  vi.restoreAllMocks(); vi.clearAllMocks(); sessionStorage.clear();
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  await act(async () => root.render(createElement(Harness)));
  await act(async () => { profiles.install(fallbackProfiles()); profiles.setSettingsOpen(true); });
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); });

it("guards duplicate operations and close synchronously, retaining failed input until explicit retry", async () => {
  const response = deferred<ReturnType<typeof fallbackProfiles>["profiles"][number]>();
  const update = vi.spyOn(plotloomApi, "updateTextProviderProfile").mockReturnValueOnce(response.promise);
  const draft = { ...profiles.profileDraft, displayName: "保留的修改" };
  await act(async () => { profiles.setProfileDraft(draft); profiles.setProfileDirty(true); });
  let submission!: Promise<void>;
  await act(async () => {
    submission = profiles.submitSettings();
    void profiles.submitSettings(); profiles.closeSettings();
  });
  expect(update).toHaveBeenCalledTimes(1);
  expect(profiles.settingsOpen).toBe(true); expect(profiles.settingsOperation).toBe("update");
  await act(async () => { response.reject(new Error("保存失败")); await submission; });
  expect(profiles.settingsFeedback).toEqual({ kind: "error", message: "保存失败" });
  expect(profiles.profileDraft).toEqual(draft); expect(profiles.profileDirty).toBe(true);
  expect(profiles.settingsOperation).toBe(null); expect(profiles.settingsOpen).toBe(true);
  expect(setError).toHaveBeenCalledWith(""); expect(setError).not.toHaveBeenCalledWith("保存失败");
  update.mockResolvedValue({ ...draft, revision: draft.revision + 1 });
  await act(async () => profiles.submitSettings());
  expect(update).toHaveBeenCalledTimes(2); expect(profiles.settingsFeedback).toBe(null);
  expect(profiles.settingsOpen).toBe(false); expect(profiles.profileDirty).toBe(false);
});

it("retains the acknowledged revision when reselecting the edited profile", async () => {
  const updated = { ...profiles.profileDraft, revision: 7, displayName: "已保存的配置" };
  vi.spyOn(plotloomApi, "updateTextProviderProfile").mockResolvedValue(updated);
  await act(async () => { profiles.setProfileDraft(updated); profiles.setProfileDirty(true); });
  await act(async () => profiles.select(updated.profileId));
  expect(profiles.profileDraft).toEqual(updated);
});

it("reports successful probes as local status and owns the follow-up refresh", async () => {
  const next = fallbackProfiles(), refresh = deferred<typeof next>();
  vi.spyOn(plotloomApi, "updateTextProviderProfile").mockResolvedValue(next.profiles[0]);
  vi.spyOn(plotloomApi, "probeTextProviderProfile").mockResolvedValue({
    ...next.profiles[0].readiness, state: "available", reasonCode: "readiness.models_verified",
  });
  vi.spyOn(plotloomApi, "getTextProviderProfiles").mockReturnValue(refresh.promise);
  let probe!: Promise<void>;
  await act(async () => { probe = profiles.probe(); });
  await act(async () => profiles.closeSettings());
  expect(profiles.settingsOperation).toBe("update"); expect(profiles.settingsOpen).toBe(true);
  await act(async () => { refresh.resolve(next); await probe; });
  expect(profiles.settingsFeedback).toEqual({ kind: "status", message: "后端已就绪：readiness.models_verified" });
  expect(setError.mock.calls.every(([message]) => message === "")).toBe(true);
  await act(async () => profiles.closeSettings());
  expect(profiles.settingsOpen).toBe(false);
});
