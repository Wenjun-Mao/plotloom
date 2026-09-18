import type { VideoBackend, VideoBackendProfile } from "../types";

export const MINIMAX_H3_ADAPTER_ID = "minimax_h3_gateway";

export function isMiniMaxH3Backend(backend: VideoBackend | null): boolean {
  return backend?.enabled === true && backend.adapterId === MINIMAX_H3_ADAPTER_ID;
}

export function h3Profiles(backend: VideoBackend | null): VideoBackendProfile[] {
  return backend?.profiles ?? [];
}

export function selectedH3Profile(backend: VideoBackend | null, profileId: string): VideoBackendProfile | undefined {
  return h3Profiles(backend).find((profile) => profile.id === profileId);
}

export function h3QualifiedDurations(backend: VideoBackend | null): number[] {
  const values = backend?.qualifiedDurationSeconds;
  return values?.filter((value) => value === 5 || value === 8) ?? [5];
}

export function MiniMaxH3Summary({ backend, profile }: { backend: VideoBackend; profile?: VideoBackendProfile }) {
  const current = profile ?? selectedH3Profile(backend, backend.defaultProfileId ?? "");
  return <p>MiniMax H3 本地候选：{current ? `${current.label} / 约 ${(current.frameCount / current.fps).toFixed(2)} 秒 / 原生音频` : "正在读取已审核 profile"}。由私有网关容量控制；不会计入 Wan 付费秒数，也不会自动重试或降级。</p>;
}

export function MiniMaxH3ProfileField({ profiles, value, onChange, disabled }: {
  profiles: VideoBackendProfile[]; value: string; onChange: (value: string) => void; disabled: boolean;
}) {
  return <label><span>H3 输出 Profile（必选）</span><select aria-label="H3 输出 Profile（必选）" value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
    {profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.label}</option>)}
  </select><small>尺寸为固定、审核过的 multiples-of-32 profile；高分辨率不自动表示创作质量已验收。</small></label>;
}

export function MiniMaxH3DurationField({ values, value, onChange, disabled }: {
  values: number[]; value: number; onChange: (value: number) => void; disabled: boolean;
}) {
  return <label><span>H3 时长（已审核）</span><select aria-label="H3 时长（已审核）" value={value} onChange={(event) => onChange(Number(event.target.value))} disabled={disabled}>
    {values.map((seconds) => <option key={seconds} value={seconds}>{seconds} 秒</option>)}
  </select><small>仅 5 秒（默认）与本次 F6 资格的 8 秒可选；网关的其他时长不会暴露为产品能力。</small></label>;
}

export function MiniMaxH3ReviewNotice() {
  return <small>原生音频并不自动构成可接受对白；需在候选回放中人工检查可懂度、口型、表演与跨镜连续性。</small>;
}
