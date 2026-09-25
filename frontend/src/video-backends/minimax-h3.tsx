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
  return values?.filter((value) => Number.isInteger(value) && value >= 5 && value <= 15) ?? [5];
}

export function MiniMaxH3Summary({ backend, profile }: { backend: VideoBackend; profile?: VideoBackendProfile }) {
  const current = profile ?? selectedH3Profile(backend, backend.defaultProfileId ?? "");
  return <p>MiniMax H3 本地候选：{current ? `质量 ${current.quality} / ${current.width} × ${current.height} / 原生音频` : "正在读取已审核规格"}。质量 1 用于开发迭代；质量 8 用于制作审核候选，仍需人工检查。由私有网关容量控制；不会计入 Wan 付费秒数，也不会自动重试或降级。</p>;
}

export function MiniMaxH3QualityField({ profiles, value, onChange, disabled }: {
  profiles: VideoBackendProfile[]; value: string; onChange: (value: string) => void; disabled: boolean;
}) {
  const current = profiles.find((profile) => profile.id === value);
  return <label><span>H3 质量用途（必选）</span><select aria-label="H3 质量用途（必选）" value={current?.quality ?? ""} onChange={(event) => {
    const next = profiles.find((profile) => profile.quality === Number(event.target.value) && profile.width === current?.width && profile.height === current?.height);
    if (next) onChange(next.id);
  }} disabled={disabled}>
    <option value={8}>质量 8 · 制作审核候选（推荐）</option>
    <option value={1}>质量 1 · 开发迭代</option>
  </select><small>导演反馈质量 8 的随机抖动较少；每条原片仍需实际审看，切换质量不会回退或改写已有任务。</small></label>;
}

export function MiniMaxH3ProfileField({ profiles, value, onChange, disabled }: {
  profiles: VideoBackendProfile[]; value: string; onChange: (value: string) => void; disabled: boolean;
}) {
  const current = profiles.find((profile) => profile.id === value);
  const currentQualityProfiles = profiles.filter((profile) => profile.quality === current?.quality);
  return <label><span>H3 输出尺寸（必选）</span><select aria-label="H3 输出尺寸（必选）" value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
    {currentQualityProfiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.width} × {profile.height} · {profile.orientation === "portrait" ? "竖版" : "横版"} / {profile.tier === "fast" ? "快速尺寸" : profile.tier === "standard" ? "标准尺寸" : "高分辨率"}</option>)}
  </select><small>高分辨率描述像素数量，不代表创作质量已验收。</small></label>;
}

export function MiniMaxH3DurationField({ values, value, onChange, disabled }: {
  values: number[]; value: number; onChange: (value: number) => void; disabled: boolean;
}) {
  return <label><span>H3 时长（已审核）</span><select aria-label="H3 时长（已审核）" value={value} onChange={(event) => onChange(Number(event.target.value))} disabled={disabled}>
    {values.map((seconds) => <option key={seconds} value={seconds}>{seconds} 秒</option>)}
  </select><small>请求为 5–15 整数秒，网关向上吸附至 24 fps 的 17k+5 帧格。请求秒数不等于实测原片或已审核播放片段时长；当前镜头的源时长/播放准入仍单独限制。</small></label>;
}

export function MiniMaxH3ReviewNotice() {
  return <small>原生音频并不自动构成可接受对白；需在候选回放中人工检查可懂度、口型、表演与跨镜连续性。</small>;
}
