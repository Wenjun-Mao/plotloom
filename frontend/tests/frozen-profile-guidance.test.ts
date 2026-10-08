import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { plotloomApi } from "../src/api";
import { providerSessionKeys } from "../src/session-key";
import { fallbackProfiles, useTextProviderProfiles } from "../src/app/workspace/useTextProviderProfiles";
import { frozenRunCredentialMessage } from "../src/app/workspace/frozenRunGuidance";
import { SettingsDialog } from "../src/app/workspace/WorkspaceViews";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement, root: Root, profiles: ReturnType<typeof useTextProviderProfiles>;
const setBusy = vi.fn(), setError = vi.fn();
const frozenRun = { providerSnapshot: { profileId: "frozen", textAuthMode: "bearer" } };
function Harness() { profiles = useTextProviderProfiles(setBusy, setError, String); return null; }
function catalog(serverKey = false) {
  const base = fallbackProfiles(), active = { ...base.profiles[0], serverKeyAvailable: true };
  const frozen = { ...active, profileId: "frozen", serverKeyAvailable: serverKey, configuration: { ...active.configuration, profileId: "frozen" } };
  return { ...base, profiles: [active, frozen] };
}
beforeEach(async () => {
  sessionStorage.clear(); vi.restoreAllMocks(); vi.clearAllMocks();
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(plotloomApi, "getTextProviderProfiles").mockResolvedValue(catalog());
  vi.spyOn(plotloomApi, "getProviderSettings"); vi.spyOn(plotloomApi, "resumeRun");
  vi.spyOn(plotloomApi, "repairWorkUnit"); vi.spyOn(plotloomApi, "activateTextProviderProfile");
  vi.spyOn(plotloomApi, "updateTextProviderProfile");
  await act(async () => root.render(createElement(Harness)));
});
afterEach(async () => {
  expect(plotloomApi.getProviderSettings).not.toHaveBeenCalled();
  expect(plotloomApi.resumeRun).not.toHaveBeenCalled(); expect(plotloomApi.repairWorkUnit).not.toHaveBeenCalled();
  expect(plotloomApi.activateTextProviderProfile).not.toHaveBeenCalled(); expect(plotloomApi.updateTextProviderProfile).not.toHaveBeenCalled();
  await act(async () => root.unmount()); host.remove();
});

it("opens only the frozen profile and gives action-neutral key guidance for Resume or repair", async () => {
  providerSessionKeys.write("default", "unrelated-tab-key");
  await act(async () => { expect(await profiles.ensureFrozenCredential(frozenRun)).toBe(false); });
  expect(profiles.settingsOpen).toBe(true); expect(profiles.selectedProfileId).toBe("frozen"); expect(profiles.sessionKey).toBe("");
  expect(setError).toHaveBeenLastCalledWith(frozenRunCredentialMessage("frozen", "missing-key"));
  expect(setError.mock.lastCall?.[0]).toContain("保存密钥不会自动运行任务");
  expect(setError.mock.lastCall?.[0]).not.toContain("继续运行");
});

it("does not borrow either the active profile's key or an orphaned key when the frozen profile is gone", async () => {
  vi.mocked(plotloomApi.getTextProviderProfiles).mockResolvedValue(fallbackProfiles());
  providerSessionKeys.write("frozen", "orphaned-tab-key");
  await act(async () => { profiles.setSettingsOpen(true); });
  await act(async () => { expect(await profiles.ensureFrozenCredential(frozenRun)).toBe(false); });
  expect(profiles.settingsOpen).toBe(false);
  expect(setError).toHaveBeenLastCalledWith(frozenRunCredentialMessage("frozen", "missing-profile"));
  expect(setError.mock.lastCall?.[0]).not.toContain("补充当前标签页密钥");
});

it.each(["ensure", "open"])("keeps %s catalog-read failure distinct and closes an unrelated settings form", async action => {
  vi.mocked(plotloomApi.getTextProviderProfiles).mockRejectedValue(new Error("catalog unavailable"));
  await act(async () => { profiles.setSettingsOpen(true); });
  await act(async () => { expect(await (action === "ensure" ? profiles.ensureFrozenCredential(frozenRun) : profiles.openFrozen("frozen"))).toBe(false); });
  expect(profiles.settingsOpen).toBe(false); expect(profiles.loaded.current).toBe(false);
  expect(setError).toHaveBeenLastCalledWith(frozenRunCredentialMessage("frozen", "read-failed", "Error: catalog unavailable"));
  expect(setError.mock.lastCall?.[0]).toContain("未发出新的执行请求");
  expect(setError.mock.lastCall?.[0]).toContain("请刷新页面后重试读取");
  expect(setError.mock.lastCall?.[0]).not.toContain("没有继续运行");
});

it.each(["server", "tab"])("accepts an exact frozen %s key without opening settings or dispatching", async source => {
  vi.mocked(plotloomApi.getTextProviderProfiles).mockResolvedValue(catalog(source === "server"));
  if (source === "tab") providerSessionKeys.write("frozen", "exact-tab-key");
  await act(async () => { expect(await profiles.ensureFrozenCredential(frozenRun)).toBe(true); });
  expect(profiles.settingsOpen).toBe(false); expect(setError).not.toHaveBeenCalled();
});

it("does not read profiles or demand a key for a frozen unauthenticated run", async () => {
  await act(async () => { expect(await profiles.ensureFrozenCredential({ providerSnapshot: { profileId: "frozen", textAuthMode: "none" } })).toBe(true); });
  expect(plotloomApi.getTextProviderProfiles).not.toHaveBeenCalled(); expect(setError).not.toHaveBeenCalled();
});

it("does not manufacture a settings profile after a catalog failure", async () => {
  vi.mocked(plotloomApi.getTextProviderProfiles).mockRejectedValue(new Error("catalog unavailable"));
  await act(async () => profiles.openSettings());
  expect(profiles.settingsOpen).toBe(false); expect(profiles.loaded.current).toBe(false);
  expect(setError.mock.lastCall?.[0]).toContain("无法读取模型配置，请重试");
});

it("preserves exact server readiness and adapter choices through installation and rendering", async () => {
  const next = catalog();
  next.trustedAdapters = [{ adapterId: "server-owned", adapterVersion: "7" }];
  const readiness = { ...next.profiles[1].readiness, state: "disabled" as const, reasonCode: "readiness.profile_disabled", observedAt: "2026-10-08T00:00:00Z" };
  next.profiles[1] = { ...next.profiles[1], enabled: false, adapterId: "server-owned", adapterVersion: "7", readiness };
  await act(async () => profiles.install(next, "frozen"));
  expect(profiles.catalog.current).toBe(next); expect(profiles.profileDraft.readiness).toBe(readiness);
  await act(async () => root.render(createElement(SettingsDialog, {
    profiles: next, selectedProfileId: "frozen", draft: next.profiles[1], sessionKey: "", busy: false,
    onDraft: vi.fn(), onSessionKey: vi.fn(), onSelect: vi.fn(), onCreate: vi.fn(), onCopy: vi.fn(),
    onDelete: vi.fn(), onActivate: vi.fn(), onAvailability: vi.fn(), onProbe: vi.fn(), onClose: vi.fn(), onSave: vi.fn(),
  })));
  const adapters = [...host.querySelectorAll("select")].find(select => select.value === "server-owned@7")!;
  expect([...adapters.options].map(option => option.value)).toEqual(["server-owned@7"]);
  expect(host.textContent).toContain("readiness.profile_disabled");
  const editorLabel = [...host.querySelectorAll("label")].find(label => label.textContent?.startsWith("当前编辑的模型配置"))!;
  expect(editorLabel.querySelector("select")?.value).toBe("frozen");
  expect(editorLabel.textContent).toContain("default · 当前使用");
  expect(editorLabel.textContent).not.toContain("活动 Profile");
});
