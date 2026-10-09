import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import { defaultProviderSettings } from "../../demo";
import { providerSessionKeys } from "../../session-key";
import type { TextBackendReadiness, TextProviderProfileConfiguration, TextProviderProfilesResponse, TextProviderProfileView } from "../../types";
import { frozenRunCredentialMessage } from "./frozenRunGuidance";

export type SettingsFeedback = { kind: "error" | "status"; message: string };

function defaultProfile(): TextProviderProfileView {
  const configuration: TextProviderProfileConfiguration = { profileSchemaVersion: 2, profileId: "default", profileVersion: 0, profileHash: "", textProvider: defaultProviderSettings.textProvider || "openai-compatible", textBaseUrl: defaultProviderSettings.textBaseUrl || "", textModel: defaultProviderSettings.textModel || "", textAuthMode: defaultProviderSettings.textAuthMode, textCapabilities: { ...defaultProviderSettings.textCapabilities, chatTemplateKwargs: false }, textContextWindowTokens: defaultProviderSettings.textContextWindowTokens, textMaxOutputTokens: defaultProviderSettings.textMaxOutputTokens, textTemperature: defaultProviderSettings.textTemperature, textMaxConcurrency: defaultProviderSettings.textMaxConcurrency, textConnectTimeoutSeconds: defaultProviderSettings.textConnectTimeoutSeconds, textAttemptTimeoutSeconds: defaultProviderSettings.textAttemptTimeoutSeconds, redirectPolicy: "no_follow", requestExtension: "none", reasoningMode: "provider_default", extractionPolicy: { allowJsonFence: false, allowLeadingThinkBlock: false }, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 4096, storyboard: 4096 }, maxSemanticCorrections: 2, presetId: "custom", presetVersion: "1" };
  return { profileId: "default", displayName: "Default", configuration, revision: 0, enabled: true, availabilityRevision: 0, adapterId: "openai_compatible", adapterVersion: "1", createdAt: "", updatedAt: "", serverKeyAvailable: false, readiness: { profileId: "default", profileRevision: 0, state: "unverified", reasonCode: "readiness.not_checked", observedAt: null } };
}

export function fallbackProfiles(): TextProviderProfilesResponse {
  return { profiles: [defaultProfile()], activeProfileId: "default", selectionRevision: 0, trustedAdapters: [{ adapterId: "openai_compatible", adapterVersion: "1" }], presets: { compatible_v1: { presetId: "compatible_v1", presetVersion: "1", requestExtension: "none", reasoningMode: "provider_default", textContextWindowTokens: 32768, textMaxOutputTokens: 8192, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 4096, storyboard: 4096 }, textAttemptTimeoutSeconds: 300, maxSemanticCorrections: 2 }, quality_reasoning_v1: { presetId: "quality_reasoning_v1", presetVersion: "1", requestExtension: "chat_template_kwargs", reasoningMode: "enabled", textContextWindowTokens: 131072, textMaxOutputTokens: 32768, stageMaxOutputTokens: { story_bible: 32768, story_graph: 32768, scene_beats: 32768, storyboard: 32768 }, textAttemptTimeoutSeconds: 900, maxSemanticCorrections: 2 }, final_only_v1: { presetId: "final_only_v1", presetVersion: "1", requestExtension: "chat_template_kwargs", reasoningMode: "disabled", textContextWindowTokens: 32768, textMaxOutputTokens: 16384, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 8192, storyboard: 8192 }, textAttemptTimeoutSeconds: 600, maxSemanticCorrections: 2 } } };
}

export function useTextProviderProfiles(setBusy: (busy: boolean) => void, setError: (message: string) => void, describeError: (error: unknown) => string) {
  const [profiles, setProfiles] = useState<TextProviderProfilesResponse>(fallbackProfiles);
  const [selectedProfileId, setSelectedProfileId] = useState("default");
  const [profileDraft, setProfileDraft] = useState<TextProviderProfileView>(defaultProfile);
  const [profileDirty, setProfileDirty] = useState(false);
  const [sessionKey, setSessionKey] = useState(() => providerSessionKeys.read("default"));
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsFeedback, setSettingsFeedback] = useState<SettingsFeedback | null>(null);
  const [settingsOperation, setSettingsOperation] = useState<"update" | "availability" | null>(null);
  const settingsPending = useRef(false);
  const runSettings = useCallback(async (work: () => Promise<void>, operation: "update" | "availability" = "update") => {
    if (settingsPending.current) return;
    settingsPending.current = true;
    setSettingsOperation(operation); setBusy(true); setError(""); setSettingsFeedback(null);
    try { await work(); }
    catch (error) { setSettingsFeedback({ kind: "error", message: describeError(error) }); }
    finally { settingsPending.current = false; setSettingsOperation(null); setBusy(false); }
  }, [describeError, setBusy, setError]);
  const closeSettings = useCallback(() => {
    if (!settingsPending.current) setSettingsOpen(false);
  }, []);
  const loaded = useRef(false);
  const catalog = useRef<TextProviderProfilesResponse>(fallbackProfiles());
  useEffect(() => { catalog.current = profiles; }, [profiles]);
  const install = useCallback((next: TextProviderProfilesResponse, selectedId = next.activeProfileId) => {
    const selected = next.profiles.find((profile) => profile.profileId === selectedId) || next.profiles[0];
    if (!selected) return;
    loaded.current = true; catalog.current = next;
    setProfiles(next); setSelectedProfileId(selected.profileId); setProfileDraft(selected); setSessionKey(providerSessionKeys.read(selected.profileId)); setProfileDirty(false);
  }, []);
  const refresh = useCallback(async (signal?: AbortSignal) => {
    const next = await plotloomApi.getTextProviderProfiles(signal);
    install(next);
    return next;
  }, [install]);
  const save = useCallback(async (draft: TextProviderProfileView, key: string) => {
    if (draft.configuration.textAuthMode === "bearer") providerSessionKeys.write(draft.profileId, key); else providerSessionKeys.clear(draft.profileId);
    const saved = await plotloomApi.updateTextProviderProfile(draft.profileId, draft.revision, draft.displayName, draft.configuration, draft.adapterId, draft.adapterVersion);
    setProfiles((current) => ({ ...current, profiles: current.profiles.map((profile) => profile.profileId === saved.profileId ? saved : profile) }));
    if (saved.profileId === selectedProfileId) { setProfileDraft(saved); setSessionKey(saved.configuration.textAuthMode === "bearer" ? providerSessionKeys.read(saved.profileId) : ""); }
    setProfileDirty(false); return saved;
  }, [selectedProfileId]);
  const saveCurrent = useCallback(() => save(profileDraft, sessionKey), [profileDraft, save, sessionKey]);
  const openSettings = useCallback(async () => {
    if (settingsPending.current) return;
    setSettingsOpen(false); setSettingsFeedback(null); setError("");
    try { await refresh(); setSettingsOpen(true); }
    catch (error) { setError(`无法读取模型配置，请重试。${describeError(error)}`); }
  }, [describeError, refresh, setError]);
  const submitSettings = useCallback(() => runSettings(async () => {
    await saveCurrent(); setSettingsOpen(false);
  }), [runSettings, saveCurrent]);
  const select = useCallback((profileId: string) => runSettings(async () => {
    // Read the catalog after saving: selecting the same profile must not restore
    // the pre-save revision over the acknowledged response.
    const saved = profileDirty ? await saveCurrent() : undefined;
    const selected = saved?.profileId === profileId ? saved : profiles.profiles.find(profile => profile.profileId === profileId);
    if (!selected) return;
    setSelectedProfileId(profileId); setProfileDraft(selected);
    setSessionKey(providerSessionKeys.read(profileId)); setProfileDirty(false);
  }), [profileDirty, profiles.profiles, runSettings, saveCurrent]);
  const create = useCallback(async (copy = false) => {
    if (settingsPending.current) return;
    const profileId = window.prompt("新配置标识（小写字母、数字、下划线）", "")?.trim();
    if (!profileId) return;
    const displayName = window.prompt("显示名称", profileId)?.trim();
    if (!displayName) return;
    await runSettings(async () => {
      const source = profileDirty ? await saveCurrent() : profileDraft;
      const created = await plotloomApi.createTextProviderProfile(copy
        ? { profileId, displayName, copyFromProfileId: source.profileId }
        : { profileId, displayName, configuration: { ...source.configuration, profileId, profileVersion: 0, profileHash: "", presetId: "custom" }, adapterId: source.adapterId, adapterVersion: source.adapterVersion });
      setProfiles(current => ({ ...current, profiles: [...current.profiles, created] }));
      setSelectedProfileId(created.profileId); setProfileDraft(created);
      setSessionKey(providerSessionKeys.read(created.profileId)); setProfileDirty(false);
    });
  }, [profileDirty, profileDraft, runSettings, saveCurrent]);
  const activate = useCallback(() => runSettings(async () => {
    if (profileDirty) await saveCurrent();
    await plotloomApi.activateTextProviderProfile(profileDraft.profileId, profiles.selectionRevision);
    await refresh();
  }), [profileDirty, profileDraft.profileId, profiles.selectionRevision, refresh, runSettings, saveCurrent]);
  const setAvailability = useCallback(() => runSettings(async () => {
    const updated = await plotloomApi.setTextProviderProfileAvailability(profileDraft.profileId, profileDraft.availabilityRevision, profileDraft.enabled === false);
    setProfiles(current => {
      const next = { ...current, profiles: current.profiles.map(profile => profile.profileId === updated.profileId
        ? { ...profile, enabled: updated.enabled, availabilityRevision: updated.availabilityRevision } : profile) };
      catalog.current = next; return next;
    });
    // Availability owns only these two fields; edits typed while it runs survive.
    setProfileDraft(current => current.profileId === updated.profileId
      ? { ...current, enabled: updated.enabled, availabilityRevision: updated.availabilityRevision } : current);
  }, "availability"), [profileDraft, runSettings]);
  const remove = useCallback(() => runSettings(async () => {
    if (profileDraft.profileId === profiles.activeProfileId) throw new Error("请先使用另一份配置，再删除当前使用的配置。");
    await plotloomApi.deleteTextProviderProfile(profileDraft.profileId, profileDraft.revision);
    providerSessionKeys.clear(profileDraft.profileId);
    install(await plotloomApi.getTextProviderProfiles());
  }), [install, profileDraft, profiles.activeProfileId, runSettings]);
  const probe = useCallback(() => runSettings(async () => {
    const saved = await saveCurrent();
    const result = await plotloomApi.probeTextProviderProfile(saved.profileId, saved.configuration.textAuthMode === "bearer");
    await refresh();
    setSettingsFeedback({ kind: "status", message: result.state === "available"
      ? `后端已就绪：${result.reasonCode}` : `后端状态：${result.state} · ${result.reasonCode}` });
  }), [refresh, runSettings, saveCurrent]);
  const openFrozen = useCallback(async (profileId: string): Promise<boolean> => {
    if (settingsPending.current) return false;
    setSettingsOpen(false); setSettingsFeedback(null);
    try {
      const next = loaded.current ? catalog.current : await refresh();
      const selected = next.profiles.find((profile) => profile.profileId === profileId);
      if (!selected) { setError(frozenRunCredentialMessage(profileId, "missing-profile")); return false; }
      setSelectedProfileId(profileId); setProfileDraft(selected); setSessionKey(providerSessionKeys.read(profileId)); setProfileDirty(false); setSettingsOpen(true);
      return true;
    } catch (error) { setError(frozenRunCredentialMessage(profileId, "read-failed", describeError(error))); return false; }
  }, [describeError, refresh, setError]);
  const ensureFrozenCredential = useCallback(async (run: { providerSnapshot: Record<string, unknown> }): Promise<boolean> => {
    if (run.providerSnapshot.textAuthMode === "none") return true;
    const profileId = String(run.providerSnapshot.profileId || "default");
    try {
      const next = loaded.current ? catalog.current : await refresh();
      const profile = next.profiles.find((candidate) => candidate.profileId === profileId);
      if (!profile) { setSettingsOpen(false); setError(frozenRunCredentialMessage(profileId, "missing-profile")); return false; }
      if (profile.serverKeyAvailable || providerSessionKeys.read(profileId)) return true;
      if (await openFrozen(profileId)) setError(frozenRunCredentialMessage(profileId, "missing-key"));
      return false;
    } catch (error) { setSettingsOpen(false); setError(frozenRunCredentialMessage(profileId, "read-failed", describeError(error))); return false; }
  }, [describeError, openFrozen, refresh, setError]);
  return { profiles, selectedProfileId, profileDraft, profileDirty, sessionKey, settingsOpen, settingsFeedback, settingsOperation, submitSettings, closeSettings, setSettingsOpen, setProfileDraft, setSessionKey, setProfileDirty, loaded, catalog, install, refresh, save, saveCurrent, openSettings, select, create, activate, setAvailability, remove, probe, openFrozen, ensureFrozenCredential };
}
