import { Button } from "../components";
import type { ArtReferenceProposal } from "../types";
import { artStyleLabel, record, type ArtReferenceSubject } from "./artReferencePresentation";

export function ArtReferencePreparation({ style, subject, study, actionable, direction, onDirectionChange, onPrepare, onSend, onRefresh, onCancel }: {
  style: unknown; subject: ArtReferenceSubject; study?: ArtReferenceProposal;
  actionable: boolean; direction: string; onDirectionChange: (value: string) => void;
  onPrepare: () => void; onSend: () => void; onRefresh: () => void; onCancel: () => void;
}) {
  const frozen = Boolean(study?.current && study.state !== "cancelled");
  const snapshot = record(study?.request.frozenSnapshot);
  const frozenDirection = typeof snapshot.renderDirection === "string" ? snapshot.renderDirection : "";
  // A current task shows the request it will actually send, not the editable draft.
  const image = record((frozen ? record(record(snapshot.subject).content) : subject.content).image);
  return <section className="appearance-ideas">
    <h3>生成参考图片</h3>
    <p>准备只保存任务，发送给图像生成助手后才开始生成。返回的图片仍需你审阅和选用。</p>
    <p>美术风格：{artStyleLabel(style)}</p>
    <label>{frozen ? "本次任务的图片要求（已冻结）" : "图片要求"}<textarea
      data-testid="art-reference-direction" disabled={!actionable} readOnly={frozen} rows={3}
      value={frozen ? frozenDirection : direction} onChange={(event) => onDirectionChange(event.target.value)}
    /></label>
    <small>{frozen ? "这些要求已保存到任务中，不会随草稿修改。" : "可以用中文补充构图、光线或细节要求。默认沿用已接受的美术设定。"}</small>
    <details className="reference-technical">
      <summary>生成指令（高级）</summary>
      <p>以下为{frozen ? "本次任务冻结" : "已接受美术设定"}中的模型提示词原文；图片要求会与它们一同交给图像生成助手。</p>
      <dl>{([ ["prompt", "主图提示词"], ["sheet", "参考图提示词"], ["negativePrompt", "排除内容"] ] as const).map(([key, label]) =>
        typeof image[key] === "string" && <div key={key}><dt>{label}</dt><dd>{image[key]}</dd></div>)}</dl>
    </details>
    {!frozen && <Button disabled={!actionable || !direction.trim()} onClick={onPrepare}>准备图片生成任务</Button>}
    {study && <div className="button-row">
      {study.current && study.state === "prepared" && <Button variant="primary" disabled={!actionable} onClick={onSend}>发送给图像生成助手</Button>}
      {study.state !== "prepared" && <Button disabled={!actionable} onClick={onRefresh}>检查图像交付</Button>}
      {(study.state === "prepared" || study.state === "exported") && <Button variant="danger" disabled={!actionable} onClick={onCancel}>取消图片任务</Button>}
    </div>}
  </section>;
}
