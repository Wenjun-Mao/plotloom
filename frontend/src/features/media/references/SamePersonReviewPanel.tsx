import type { Dispatch, SetStateAction } from "react";
import type {
  ImageJob,
  ManagedAsset,
  ReviewedKeyframe,
  SamePersonComparison,
  VisualWorkbench,
} from "../../../types";
import { plotloomApi } from "../../../api";
import { Button, Field } from "../../../components";

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
  comparisons: SamePersonComparison[];
  setReviewer: Dispatch<SetStateAction<string>>;
  setNotes: Dispatch<SetStateAction<string>>;
  setComparisons: Dispatch<SetStateAction<SamePersonComparison[]>>;
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
            跨镜头同一人物视觉复核 · required before still preview
          </strong>
          <p className="muted">
            逐一查看此候选冻结的 primary/complementary
            身份参考与当前候选。这里记录的是具名审阅者的视觉判断；Codex
            engineering/visual assessment 必须明确写作 Codex，不能冒充
            human/product
            decision。此复核不使用人脸识别，也不替代服装、道具或镜头状态的作者权威。
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
                    alt="selected candidate under review"
                  />
                  <strong>候选 · {selectedBinding.assetId.slice(0, 8)}</strong>
                </>
              ) : (
                <small>Selected candidate bytes are unavailable.</small>
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
                        alt={`${mapping.characterId} frozen ${index === 0 ? "primary" : "complementary"} reference`}
                      />
                    ) : (
                      <small>
                        Frozen asset {asset.assetId.slice(0, 8)} is unavailable.
                      </small>
                    )}
                    <strong>
                      {mapping.characterId} ·{" "}
                      {index === 0 ? "primary" : `complementary ${index}`} · r
                      {mapping.referenceRevision}
                    </strong>
                    <small>
                      frozen decision {mapping.referenceDecisionId.slice(0, 8)}{" "}
                      · {asset.originalHash.slice(0, 12)}
                    </small>
                  </article>
                );
              }),
            )}
          </div>
          <div className="field-grid two compact">
            <Field label="审阅者（Codex 或 creator/product reviewer）">
              <input
                value={samePersonReviewer}
                disabled={readOnly || busy}
                onChange={(event) => setSamePersonReviewer(event.target.value)}
              />
            </Field>
            <Field label="当前引用">
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
                              judgment: event.target.value as "pass" | "fail",
                            }
                          : item,
                      ),
                    )
                  }
                >
                  <option value="pass">pass</option>
                  <option value="fail">fail</option>
                </select>
              </Field>
              <Field label="身份对比说明">
                <input
                  value={comparison.identityNotes}
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
              <Field label="镜头状态说明">
                <input
                  value={comparison.stateNotes}
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
          <Field label="复核备注">
            <textarea
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
              已覆盖此 keyframe；身份引用或审核 keyframe 变化时会自动过期。
            </small>
          ) : (
            <div className="notice warning">
              此身份感知 keyframe 尚无当前复核，因此不能进入 still animatic。
            </div>
          )}
          {workbench.samePersonReviews.reviews
            .filter(
              (item) => item.bindingId === selectedBinding.id && !item.current,
            )
            .map((item) => (
              <small className="notice" key={item.id}>
                历史/已过期复核 {item.id.slice(0, 8)} · reviewer {item.reviewer}{" "}
                · frozen references remain inspectable above.
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
                samePersonComparisons.some(
                  (item) =>
                    !item.identityNotes.trim() || !item.stateNotes.trim(),
                )
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
