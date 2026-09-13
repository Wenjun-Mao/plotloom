import type { VideoBackend } from "../types";

export const MINIMAX_H3_ADAPTER_ID = "minimax_h3_gateway";
export type H3AspectPolicy = "" | "cover_center_crop" | "contain_pad" | "reject_mismatch";

export function isMiniMaxH3Backend(backend: VideoBackend | null): boolean {
  return backend?.enabled === true && backend.adapterId === MINIMAX_H3_ADAPTER_ID;
}

export function MiniMaxH3Summary({ backend }: { backend: VideoBackend }) {
  return <p>固定 Spark H3 profile：{backend.width}×{backend.height} / 约 {backend.durationSeconds?.toFixed(2)} 秒 / 原生音频。提交后由私有网关容量控制；不会计入 Wan 付费秒数，也不会自动重试。</p>;
}

export function MiniMaxH3AspectPolicyField({ value, onChange, disabled }: { value: H3AspectPolicy; onChange: (value: H3AspectPolicy) => void; disabled: boolean }) {
  return <label><span>关键帧比例处理（必选）</span><select value={value} onChange={(event) => onChange(event.target.value as H3AspectPolicy)} disabled={disabled}>
    <option value="">请选择，绝不静默拉伸</option>
    <option value="cover_center_crop">居中裁切以填满 16:9</option>
    <option value="contain_pad">完整保留并以黑边填充 16:9</option>
    <option value="reject_mismatch">比例不符时拒绝提交</option>
  </select></label>;
}

export function MiniMaxH3ReviewNotice() {
  return <small>原生音频并不自动构成可接受对白；需在候选回放中人工检查可懂度、口型、表演与跨镜连续性。</small>;
}
