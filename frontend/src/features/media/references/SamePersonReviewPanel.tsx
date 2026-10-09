import type { Dispatch, SetStateAction } from "react";
import type {
  ImageJob,
  ManagedAsset,
  ReviewedKeyframe,
  VisualWorkbench,
} from "../../../types";
import { plotloomApi } from "../../../api";
import { Button, Field } from "../../../components";
import type { SamePersonComparisonDraft } from "../../../same-person-review-types";
import { completeSamePersonComparisons, samePersonReviewSummary } from "./same-person-draft";

type IdentityMapping = NonNullable<
  NonNullable<ImageJob["request"]["frozenSnapshot"]>["characterIdentity"]
>[number];

export function SamePersonReviewPanel({
  projectId,
  selectedBinding,
  selectedIdentityMapping,
  assetById,
  currentReviewByBinding,
  workbench,
  reviewer: samePersonReviewer,
  notes: samePersonNotes,
  comparisons: samePersonComparisons,
  setReviewer: setSamePersonReviewer,
  setNotes: setSamePersonNotes,
  setComparisons: setSamePersonComparisons,
  readOnly,
  busy,
  onRecord,
}: {
  projectId?: string;
  selectedBinding: ReviewedKeyframe | undefined;
  selectedIdentityMapping: IdentityMapping[];
  assetById: Map<string, ManagedAsset>;
  currentReviewByBinding: Map<
    string,
    VisualWorkbench["samePersonReviews"]["reviews"][number]
  >;
  workbench: VisualWorkbench;
  reviewer: string;
  notes: string;
  comparisons: SamePersonComparisonDraft[];
  setReviewer: Dispatch<SetStateAction<string>>;
  setNotes: Dispatch<SetStateAction<string>>;
  setComparisons: Dispatch<SetStateAction<SamePersonComparisonDraft[]>>;
  readOnly: boolean;
  busy: boolean;
  onRecord: () => void;
}) {
  return (
    <>
      {selectedBinding && selectedIdentityMapping.length > 0 && (
        <section
          className="intent-editor"
          data-testid="same-person-review-panel"
          aria-label="跨镜头同一人物视觉复核"
        >
          <strong>
            跨镜头同一人物视觉复核
          </strong>
          <p className="muted">
            生成视频或创建连续静帧预览前，逐一比较此候选与任务冻结的主参考图和补充参考图。
            记录实际审阅者的视觉判断；由 Codex 完成的技术或视觉检查，审阅者须写为
            Codex，不能记作真人的创作确认。此复核不使用人脸识别，也不替代作者对服装、道具和镜头状态的设定。
          </p>
          <div
            className="frozen-review-comparison"
            data-testid="frozen-reference-comparison"
          >
            <article className="media-candidate">
              {projectId && assetById.get(selectedBinding.assetId) ? (
                <>
                  <img
                    src={plotloomApi.managedAssetUrl(
                      projectId,
                      selectedBinding.assetId,
                    )}
                    alt="正在复核的候选图片"
                  />
                  <strong>候选 · {selectedBinding.assetId.slice(0, 8)}</strong>
                </>
              ) : (
                <small>无法读取当前候选图片，请先检查素材。</small>
              )}
            </article>
            {selectedIdentityMapping.flatMap((mapping) =>
              mapping.assets.map((asset, index) => {
                const frozenAsset = assetById.get(asset.assetId);
                return (
                  <article
                    className="media-candidate"
                    key={`${mapping.referenceDecisionId}:${asset.assetId}`}
                    data-testid={`frozen-reference-${asset.assetId}`}
                  >
                    {projectId && frozenAsset ? (
                      <img
                        src={plotloomApi.managedAssetUrl(
                          projectId,
                          frozenAsset.id,
                        )}
                        alt={`${mapping.characterId} 任务冻结的${index === 0 ? "主参考图" : "补充参考图"}`}
                      />
                    ) : (
                      <small>
                        无法读取任务冻结的素材 {asset.assetId.slice(0, 8)}。
                      </small>
                    )}
                    <strong>
                      {mapping.characterId} ·{" "}
                      {index === 0 ? "主参考图" : `补充参考图 ${index}`} · r
                      {mapping.referenceRevision}
                    </strong>
                    <small>
                      冻结的参考选择 {mapping.referenceDecisionId.slice(0, 8)}{" "}
                      · {asset.originalHash.slice(0, 12)}
                    </small>
                    {mapping.acceptedCast && (
                      <small>
                        已确认角色 {mapping.acceptedCast.castCharacterId} · r
                        {mapping.acceptedCast.revision} · {mapping.acceptedCast.contentHash.slice(0, 12)}
                      </small>
                    )}
                  </article>
                );
              }),
            )}
          </div>
          <div className="field-grid two compact">
            <Field label="审阅者（姓名或 Codex）" required>
              <input
                aria-required="true"
                value={samePersonReviewer}
                disabled={readOnly || busy}
                onChange={(event) => setSamePersonReviewer(event.target.value)}
              />
            </Field>
              <Field label="本任务的身份参考">
              <input
                readOnly
                value={selectedIdentityMapping
                  .map(
                    (item) =>
                      `${item.characterId} · r${item.referenceRevision}`,
                  )
                  .join(" / ")}
              />
            </Field>
          </div>
          {samePersonComparisons.map((comparison, index) => (
            <div
              className="field-grid two compact"
              key={comparison.characterId}
            >
              <Field label={`${comparison.characterId} 身份判断`}>
                <select
                  data-testid={`same-person-judgment-${comparison.characterId}`}
                  value={comparison.judgment}
                  disabled={readOnly || busy}
                  onChange={(event) =>
                    setSamePersonComparisons((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index
                          ? {
                              ...item,
                              judgment: event.target.value as SamePersonComparisonDraft["judgment"],
                              productionDecision: undefined,
                              uncertaintyReason: undefined,
                            }
                          : item,
                      ),
                    )
                  }
                >
                  <option value="">请选择身份判断</option>
                  <option value="pass">通过</option>
                  <option value="fail">不通过</option>
                  <option value="unassessable">无法判断</option>
                </select>
              </Field>
              {comparison.judgment === "unassessable" && <>
                <Field label={`${comparison.characterId} 无法判断时的投产决定`} required>
                  <select data-testid={`same-person-production-${comparison.characterId}`}
                    aria-required="true" value={comparison.productionDecision ?? ""} disabled={readOnly || busy}
                    onChange={event => setSamePersonComparisons(current => current.map((item, itemIndex) => itemIndex === index
                      ? { ...item, productionDecision: event.target.value as "" | "hold" | "authorize" } : item))}>
                    <option value="">请选择投产决定</option>
                    <option value="hold">暂缓投产</option>
                    <option value="authorize">接受身份不确定性，明确授权投产</option>
                  </select>
                </Field>
                <Field label="构图与身份不确定性说明" required>
                  <textarea aria-required="true" rows={2} value={comparison.uncertaintyReason ?? ""}
                    placeholder="说明为何有意采用此构图、无法辨认的身份信息，以及接受的不确定性。"
                    disabled={readOnly || busy}
                    onChange={event => setSamePersonComparisons(current => current.map((item, itemIndex) => itemIndex === index
                      ? { ...item, uncertaintyReason: event.target.value } : item))} />
                </Field>
              </>}
              <Field label="身份对比说明" required>
                <input
                  aria-required="true"
                  value={comparison.identityNotes}
                  placeholder="比较面貌、体态和稳定外观，说明一致或不同之处。"
                  disabled={readOnly || busy}
                  onChange={(event) =>
                    setSamePersonComparisons((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index
                          ? { ...item, identityNotes: event.target.value }
                          : item,
                      ),
                    )
                  }
                />
              </Field>
              <Field label="镜头状态说明" required>
                <input
                  aria-required="true"
                  value={comparison.stateNotes}
                  placeholder="说明本镜头的服装、动作和道具状态；不要把它们当作身份特征。"
                  disabled={readOnly || busy}
                  onChange={(event) =>
                    setSamePersonComparisons((current) =>
                      current.map((item, itemIndex) =>
                        itemIndex === index
                          ? { ...item, stateNotes: event.target.value }
                          : item,
                      ),
                    )
                  }
                />
              </Field>
            </div>
          ))}
          <Field label="复核备注" required>
            <textarea
              aria-required="true"
              rows={2}
              value={samePersonNotes}
              disabled={readOnly || busy}
              placeholder="记录人眼判断和任何可见限制。"
              onChange={(event) => setSamePersonNotes(event.target.value)}
            />
          </Field>
          {currentReviewByBinding.get(selectedBinding.id) ? (
            <small className="notice">
              当前复核{" "}
              {currentReviewByBinding.get(selectedBinding.id)?.id.slice(0, 8)}{" "}
              ：{samePersonReviewSummary(currentReviewByBinding.get(selectedBinding.id)!)}。
              {currentReviewByBinding.get(selectedBinding.id)?.productionEligible ? "此决定允许生成视频或创建连续静帧预览。" : "此决定阻止生成视频或创建连续静帧预览。"}
              身份参考或已审核关键帧变化时会自动过期。
            </small>
          ) : (
            <div className="notice warning">
              此关键帧没有适用于当前内容的人物身份复核。每位角色通过，或无法判断且明确授权投产后，才能生成视频或创建连续静帧预览。无法确认身份时不要标记通过；不通过或暂缓投产都会阻止这两项操作。
            </div>
          )}
          {workbench.samePersonReviews.reviews
            .filter(
              (item) => item.bindingId === selectedBinding.id && !item.latest,
            )
            .map((item) => (
              <small className="notice" key={item.id}>
                {item.current ? "已被较新决定取代的复核" : "已过期的复核"} {item.id.slice(0, 8)} · 审阅者 {item.reviewer}{" "}
                · {samePersonReviewSummary(item)} · 仍可在上方查看任务冻结的参考图。
              </small>
            ))}
          <div className="button-row">
            <Button
              data-testid="record-same-person-review"
              variant="primary"
              disabled={
                readOnly ||
                busy ||
                !samePersonReviewer.trim() ||
                !samePersonNotes.trim() ||
                !completeSamePersonComparisons(samePersonComparisons)
              }
              onClick={() => void onRecord()}
            >
              记录视觉复核
            </Button>
          </div>
        </section>
      )}
    </>
  );
}
