import { useCallback, useEffect, useRef, useState } from "react";
import { plotloomApi } from "../../api";
import { defaultProviderSettings } from "../../demo";
import { providerSessionKeys } from "../../session-key";
import type { ProviderSettings, TextBackendReadiness, TextProviderProfileConfiguration, TextProviderProfilesResponse, TextProviderProfileView } from "../../types";

function defaultProfile(): TextProviderProfileView {
  const configuration: TextProviderProfileConfiguration = { profileSchemaVersion: 2, profileId: "default", profileVersion: 0, profileHash: "", textProvider: defaultProviderSettings.textProvider || "openai-compatible", textBaseUrl: defaultProviderSettings.textBaseUrl || "", textModel: defaultProviderSettings.textModel || "", textAuthMode: defaultProviderSettings.textAuthMode, textCapabilities: { ...defaultProviderSettings.textCapabilities, chatTemplateKwargs: false }, textContextWindowTokens: defaultProviderSettings.textContextWindowTokens, textMaxOutputTokens: defaultProviderSettings.textMaxOutputTokens, textTemperature: defaultProviderSettings.textTemperature, textMaxConcurrency: defaultProviderSettings.textMaxConcurrency, textConnectTimeoutSeconds: defaultProviderSettings.textConnectTimeoutSeconds, textAttemptTimeoutSeconds: defaultProviderSettings.textAttemptTimeoutSeconds, redirectPolicy: "no_follow", requestExtension: "none", reasoningMode: "provider_default", extractionPolicy: { allowJsonFence: false, allowLeadingThinkBlock: false }, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 4096, storyboard: 4096 }, maxSemanticCorrections: 2, presetId: "custom", presetVersion: "1" };
  return { profileId: "default", displayName: "Default", configuration, revision: 0, enabled: true, availabilityRevision: 0, adapterId: "openai_compatible", adapterVersion: "1", createdAt: "", updatedAt: "", serverKeyAvailable: false, readiness: { profileId: "default", profileRevision: 0, state: "unverified", reasonCode: "readiness.not_checked", observedAt: null } };
}

function legacyProfile(settings: ProviderSettings): TextProviderProfileView {
  const fallback = defaultProfile();
  return { ...fallback, displayName: settings.profileId || fallback.displayName, revision: settings.revision, updatedAt: settings.updatedAt || "", serverKeyAvailable: settings.textKeyAvailable, configuration: { ...fallback.configuration, textProvider: settings.textProvider || fallback.configuration.textProvider, textBaseUrl: settings.textBaseUrl || fallback.configuration.textBaseUrl, textModel: settings.textModel || fallback.configuration.textModel, textAuthMode: settings.textAuthMode, textCapabilities: { ...settings.textCapabilities, chatTemplateKwargs: false }, textContextWindowTokens: settings.textContextWindowTokens, textMaxOutputTokens: settings.textMaxOutputTokens, textTemperature: settings.textTemperature, textMaxConcurrency: settings.textMaxConcurrency, textConnectTimeoutSeconds: settings.textConnectTimeoutSeconds, textAttemptTimeoutSeconds: settings.textAttemptTimeoutSeconds, redirectPolicy: settings.redirectPolicy } };
}

export function fallbackProfiles(): TextProviderProfilesResponse {
  return { profiles: [defaultProfile()], activeProfileId: "default", selectionRevision: 0, trustedAdapters: [{ adapterId: "openai_compatible", adapterVersion: "1" }], presets: { compatible_v1: { presetId: "compatible_v1", presetVersion: "1", requestExtension: "none", reasoningMode: "provider_default", textContextWindowTokens: 32768, textMaxOutputTokens: 8192, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 4096, storyboard: 4096 }, textAttemptTimeoutSeconds: 300, maxSemanticCorrections: 2 }, quality_reasoning_v1: { presetId: "quality_reasoning_v1", presetVersion: "1", requestExtension: "chat_template_kwargs", reasoningMode: "enabled", textContextWindowTokens: 131072, textMaxOutputTokens: 32768, stageMaxOutputTokens: { story_bible: 32768, story_graph: 32768, scene_beats: 32768, storyboard: 32768 }, textAttemptTimeoutSeconds: 900, maxSemanticCorrections: 2 }, final_only_v1: { presetId: "final_only_v1", presetVersion: "1", requestExtension: "chat_template_kwargs", reasoningMode: "disabled", textContextWindowTokens: 32768, textMaxOutputTokens: 16384, stageMaxOutputTokens: { story_bible: 8192, story_graph: 8192, scene_beats: 8192, storyboard: 8192 }, textAttemptTimeoutSeconds: 600, maxSemanticCorrections: 2 } } };
}

export function normalizeProfileCatalog(next: TextProviderProfilesResponse): TextProviderProfilesResponse {
  return { ...next, profiles: next.profiles.map((profile) => ({ ...profile, readiness: profile.readiness || { profileId: profile.profileId, profileRevision: profile.revision, state: profile.enabled === false ? "disabled" : "unverified", reasonCode: profile.enabled === false ? "readiness.profile_disabled" : "readiness.not_checked", observedAt: null } })) };
}

export function useTextProviderProfiles(setBusy: (busy: boolean) => void, setError: (message: string) => void, describeError: (error: unknown) => string) {
  const [profiles, setProfiles] = useState<TextProviderProfilesResponse>(fallbackProfiles);
  const [selectedProfileId, setSelectedProfileId] = useState("default");
  const [profileDraft, setProfileDraft] = useState<TextProviderProfileView>(defaultProfile);
  const [profileDirty, setProfileDirty] = useState(false);
  const [sessionKey, setSessionKey] = useState(() => providerSessionKeys.read("default"));
  const [settingsOpen, setSettingsOpen] = useState(false);
  const loaded = useRef(false);
  const catalog = useRef<TextProviderProfilesResponse>(fallbackProfiles());
  useEffect(() => { catalog.current = profiles; }, [profiles]);
  const install = useCallback((next: TextProviderProfilesResponse, selectedId = next.activeProfileId) => {
    const normalized = normalizeProfileCatalog(next);
    const selected = normalized.profiles.find((profile) => profile.profileId === selectedId) || normalized.profiles[0];
    if (!selected) return;
    loaded.current = true; catalog.current = normalized;
    setProfiles(normalized); setSelectedProfileId(selected.profileId); setProfileDraft(selected); setSessionKey(providerSessionKeys.read(selected.profileId)); setProfileDirty(false);
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
    setSettingsOpen(true);
    try { await refresh(); } catch { try { const fallback = fallbackProfiles(); fallback.profiles[0] = legacyProfile(await plotloomApi.getProviderSettings()); install(fallback); } catch { /* Offline form remains available. */ } }
  }, [install, refresh]);
  const select = useCallback(async (profileId: string) => { setBusy(true); setError(""); try { if (profileDirty) await saveCurrent(); const selected = profiles.profiles.find((profile) => profile.profileId === profileId); if (!selected) return; setSelectedProfileId(profileId); setProfileDraft(selected); setSessionKey(providerSessionKeys.read(profileId)); setProfileDirty(false); } catch (error) { setError(describeError(error)); } finally { setBusy(false); } }, [describeError, profileDirty, profiles.profiles, saveCurrent, setBusy, setError]);
  const create = useCallback(async (copy = false) => { const profileId = window.prompt("新 Profile ID（小写字母、数字、下划线）", "")?.trim(); if (!profileId) return; const displayName = window.prompt("显示名称", profileId)?.trim(); if (!displayName) return; setBusy(true); setError(""); try { const source = profileDirty ? await saveCurrent() : profileDraft; const created = await plotloomApi.createTextProviderProfile(copy ? { profileId, displayName, copyFromProfileId: source.profileId } : { profileId, displayName, configuration: { ...source.configuration, profileId, profileVersion: 0, profileHash: "", presetId: "custom" }, adapterId: source.adapterId, adapterVersion: source.adapterVersion }); setProfiles((current) => ({ ...current, profiles: [...current.profiles, created] })); setSelectedProfileId(created.profileId); setProfileDraft(created); setSessionKey(providerSessionKeys.read(created.profileId)); setProfileDirty(false); } catch (error) { setError(describeError(error)); } finally { setBusy(false); } }, [describeError, profileDirty, profileDraft, saveCurrent, setBusy, setError]);
  const activate = useCallback(async () => { setBusy(true); setError(""); try { if (profileDirty) await saveCurrent(); await plotloomApi.activateTextProviderProfile(profileDraft.profileId, profiles.selectionRevision); await refresh(); } catch (error) { setError(describeError(error)); } finally { setBusy(false); } }, [describeError, profileDirty, profileDraft.profileId, profiles.selectionRevision, refresh, saveCurrent, setBusy, setError]);
  const setAvailability = useCallback(async () => { setBusy(true); setError(""); try { const updated = await plotloomApi.setTextProviderProfileAvailability(profileDraft.profileId, profileDraft.availabilityRevision, profileDraft.enabled === false); setProfiles((current) => { const next = { ...current, profiles: current.profiles.map((profile) => profile.profileId === updated.profileId ? { ...profile, enabled: updated.enabled, availabilityRevision: updated.availabilityRevision } : profile) }; catalog.current = next; return next; }); setProfileDraft((current) => current.profileId === updated.profileId ? { ...current, enabled: updated.enabled, availabilityRevision: updated.availabilityRevision } : current); } catch (error) { setError(describeError(error)); } finally { setBusy(false); } }, [describeError, profileDraft, setBusy, setError]);
  const remove = useCallback(async () => { if (profileDraft.profileId === profiles.activeProfileId) { setError("请先激活另一个 Profile，再删除当前活动 Profile。"); return; } setBusy(true); setError(""); try { await plotloomApi.deleteTextProviderProfile(profileDraft.profileId, profileDraft.revision); providerSessionKeys.clear(profileDraft.profileId); install(await plotloomApi.getTextProviderProfiles()); } catch (error) { setError(describeError(error)); } finally { setBusy(false); } }, [describeError, install, profileDraft, profiles.activeProfileId, setBusy, setError]);
  const probe = useCallback(async () => { setBusy(true); setError(""); try { const saved = await saveCurrent(); const result = await plotloomApi.probeTextProviderProfile(saved.profileId, saved.configuration.textAuthMode === "bearer"); await refresh(); setError(result.state === "available" ? `后端已就绪：${result.reasonCode}` : `后端状态：${result.state} · ${result.reasonCode}`); } catch (error) { setError(describeError(error)); } finally { setBusy(false); } }, [describeError, refresh, saveCurrent, setBusy, setError]);
  const openFrozen = useCallback(async (profileId: string) => { setSettingsOpen(true); try { const next = loaded.current ? catalog.current : await refresh(); const selected = next.profiles.find((profile) => profile.profileId === profileId); if (!selected) { setError(`冻结 Profile ${profileId} 已不存在；该运行不能换用其他 Profile。`); return; } setSelectedProfileId(profileId); setProfileDraft(selected); setSessionKey(providerSessionKeys.read(profileId)); setProfileDirty(false); } catch (error) { setError(`无法读取冻结 Profile ${profileId}：${describeError(error)}`); } }, [describeError, refresh, setError]);
  const ensureFrozenCredential = useCallback(async (run: { providerSnapshot: Record<string, unknown> }) => { if (run.providerSnapshot.textAuthMode === "none") return true; const profileId = String(run.providerSnapshot.profileId || "default"); const next = loaded.current ? catalog.current : await refresh(); const profile = next.profiles.find((candidate) => candidate.profileId === profileId); if (profile?.serverKeyAvailable || providerSessionKeys.read(profileId)) return true; await openFrozen(profileId); setError(`运行冻结在 Profile ${profileId}；请为这个 Profile 补充当前标签页 Key 后再继续。不会自动切换模型。`); return false; }, [openFrozen, refresh, setError]);
  return { profiles, selectedProfileId, profileDraft, profileDirty, sessionKey, settingsOpen, setSettingsOpen, setProfileDraft, setSessionKey, setProfileDirty, loaded, catalog, install, refresh, save, saveCurrent, openSettings, select, create, activate, setAvailability, remove, probe, openFrozen, ensureFrozenCredential };
}
