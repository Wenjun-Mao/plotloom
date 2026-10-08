import { Button } from "../components";
import { StageGuide } from "../components/StageGuide";
import { bridgeCut } from "../production-bridge-handoff";
import type { InstalledProduction } from "../types";

/** Shot navigation is owned by the installed receipt, never the latest candidate. */
export function InstalledProductionSummary({ installation, disabled, canonicalReady, onOpenShot, onReread }: {
  installation: InstalledProduction; disabled: boolean; canonicalReady: boolean;
  onOpenShot?: (shotId: string) => void; onReread: () => void;
}) {
  const current = installation.status === "current" && installation.staleReasons.length === 0;
  const firstCut = installation.cuts.map(bridgeCut).find(cut => cut !== undefined);
  return <section data-testid="installed-production">
    <strong>已建立的制作内容 · {current ? "当前有效" : "需要重建"}</strong>
    <p>{current
      ? "此处展示已确认的制作内容。新的待审提案不会替换它；是否可播放仍取决于当前审核和选用的视频片段。"
      : "故事或制作版本已变化。旧内容与媒体仍保留，故事播放暂停；请核对当前内容，准备重建提案并重新审核。这里的镜头直达已暂停。"}</p>
    <details><summary>已建立的场次与镜头</summary><ul>{installation.cuts.map((raw, index) => {
      const cut = bridgeCut(raw);
      return <li key={String(raw.shotId ?? index)}>{String(raw.shotId)} · {String(raw.seconds)} 秒
        {current && cut && onOpenShot && <Button variant="quiet" disabled={disabled || !canonicalReady} onClick={() => onOpenShot(cut.shotId)}>在分镜工作台打开 {cut.shotId}</Button>}
      </li>;
    })}</ul></details>
    {current && <StageGuide next={firstCut && onOpenShot && <Button variant="primary" disabled={disabled || !canonicalReady} onClick={() => onOpenShot(firstCut.shotId)}>继续：打开第一个镜头</Button>}>
      打开镜头后，依次完成分镜审核、参考选择、关键帧审核与视频片段审核。也可展开“已建立的场次与镜头”选择其他镜头。
    </StageGuide>}
    {current && !canonicalReady && <Button disabled={disabled} onClick={onReread}>重新读取投产镜头</Button>}
    <details><summary>已建立内容的来源详情</summary><p>提案 r{installation.proposalRevision} · {installation.admissionId}</p><code>{installation.proposalContentHash}</code>
      {installation.staleReasons.length > 0 && <ul>{installation.staleReasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul>}
    </details>
  </section>;
}
