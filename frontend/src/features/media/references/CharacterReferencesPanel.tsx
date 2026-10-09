import type { Dispatch, SetStateAction } from "react";
import type {
  CharacterReferenceProposal,
  ManagedAsset,
  StoryBible,
  VisualWorkbench,
} from "../../../types";
import { plotloomApi } from "../../../api";
import { Button, Field } from "../../../components";
import type { MediaReadPhase } from "../useMediaWorkbenchData";

type ReferenceForm = {
  characterId: string;
  primaryAssetId: string;
  complementaryAssetIds: string[];
  reviewer: string;
  notes: string;
  proposalCharacterId: string;
  proposalDirection: string;
  proposalParentCandidateAssetId: string;
  setCharacterId: Dispatch<SetStateAction<string>>;
  setPrimaryAssetId: Dispatch<SetStateAction<string>>;
  setComplementaryAssetIds: Dispatch<SetStateAction<string[]>>;
  setReviewer: Dispatch<SetStateAction<string>>;
  setNotes: Dispatch<SetStateAction<string>>;
  setProposalCharacterId: Dispatch<SetStateAction<string>>;
  setProposalDirection: Dispatch<SetStateAction<string>>;
  setProposalParentCandidateAssetId: Dispatch<SetStateAction<string>>;
};

export function CharacterReferencesPanel({
  projectId,
  bible,
  storyBibleRevision,
  workbench,
  proposals,
  assetById,
  referenceStateByCharacter,
  currentReferenceByCharacter,
  form: {
    characterId: referenceCharacterId,
    primaryAssetId: referencePrimaryAssetId,
    complementaryAssetIds: referenceComplementaryAssetIds,
    reviewer: referenceReviewer,
    notes: referenceNotes,
    proposalCharacterId,
    proposalDirection,
    proposalParentCandidateAssetId,
    setCharacterId: setReferenceCharacterId,
    setPrimaryAssetId: setReferencePrimaryAssetId,
    setComplementaryAssetIds: setReferenceComplementaryAssetIds,
    setReviewer: setReferenceReviewer,
    setNotes: setReferenceNotes,
    setProposalCharacterId,
    setProposalDirection,
    setProposalParentCandidateAssetId,
  },
  readOnly,
  busy,
  mediaReadPhase = "ready",
  onSelectReference,
  onRevokeReference,
  onPrepareProposal,
  onSendProposal,
  onRefreshProposal,
}: {
  projectId?: string;
  bible: StoryBible;
  storyBibleRevision?: number;
  workbench: VisualWorkbench;
  proposals: CharacterReferenceProposal[];
  assetById: Map<string, ManagedAsset>;
  referenceStateByCharacter: Map<
    string,
    VisualWorkbench["characterReferences"]["states"][number]
  >;
  currentReferenceByCharacter: Map<
    string,
    VisualWorkbench["characterReferences"]["decisions"][number]
  >;
  form: ReferenceForm;
  readOnly: boolean;
  busy: boolean;
  mediaReadPhase?: MediaReadPhase;
  onSelectReference: () => void;
  onRevokeReference: (characterId: string) => void;
  onPrepareProposal: () => void;
  onSendProposal: (proposalId: string) => void;
  onRefreshProposal: (proposalId: string) => void;
}) {
  const proposalCandidates = proposals
    .filter(
      (proposal) =>
        proposal.current && proposal.characterId === proposalCharacterId,
    )
    .flatMap((proposal) =>
      proposal.deliveries.flatMap((delivery) =>
        delivery.candidates.map((candidate) => ({ proposal, candidate })),
      ),
    );
  return (
      <section
        className="image-job-panel"
        data-testid="character-reference-panel"
      >
        <div className="section-title">
          <span>角色身份参考</span>
          <strong>
            选择参考图 → 为镜头生成图片 → 记录人物视觉复核
          </strong>
        </div>
        <p className="muted">
          身份参考用于保持同一人物的外观，可更新或撤销。它不改写已确认的角色设定，
          也不替代每个镜头的状态、服装、构图和剧情；图片任务只采用当前镜头中人物的参考图。
          角色页已选的外观图仍须在这里明确选为当前制作参考；可以选用同一张图，无需重新生成。
        </p>
        <div className="field-grid two compact">
          <Field label="角色" required>
            <select
              aria-required="true"
              data-testid="reference-character"
              value={referenceCharacterId}
              disabled={readOnly || busy}
              onChange={(event) => setReferenceCharacterId(event.target.value)}
            >
              {bible.characters.map((character) => (
                <option key={character.id} value={character.id}>
                  {character.name} · {character.id}
                </option>
              ))}
            </select>
          </Field>
          <Field label="主身份参考" required>
            <select
              aria-required="true"
              data-testid="reference-primary-asset"
              value={referencePrimaryAssetId}
              disabled={readOnly || busy}
              onChange={(event) =>
                setReferencePrimaryAssetId(event.target.value)
              }
            >
              <option value="">选择已导入 JPEG / PNG</option>
              {workbench.assets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.id.slice(0, 8)} · {asset.width}×{asset.height}
                </option>
              ))}
            </select>
          </Field>
          <Field label="辅助参考（最多 2 项）">
            <select
              multiple
              data-testid="reference-complementary-assets"
              value={referenceComplementaryAssetIds}
              disabled={readOnly || busy}
              onChange={(event) =>
                setReferenceComplementaryAssetIds(
                  Array.from(event.currentTarget.selectedOptions)
                    .map((option) => option.value)
                    .filter((assetId) => assetId !== referencePrimaryAssetId)
                    .slice(0, 2),
                )
              }
            >
              {workbench.assets
                .filter((asset) => asset.id !== referencePrimaryAssetId)
                .map((asset) => (
                  <option key={asset.id} value={asset.id}>
                    {asset.id.slice(0, 8)} · {asset.width}×{asset.height}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="审阅者" required>
            <input
              aria-required="true"
              data-testid="reference-reviewer"
              value={referenceReviewer}
              disabled={readOnly || busy}
              onChange={(event) => setReferenceReviewer(event.target.value)}
            />
          </Field>
        </div>
        <Field label="选择说明" required>
          <textarea
            aria-required="true"
            data-testid="reference-notes"
            rows={2}
            value={referenceNotes}
            disabled={readOnly || busy}
            placeholder="说明用于跨镜头一致性的身份特征；不要把镜头状态写成身份。"
            onChange={(event) => setReferenceNotes(event.target.value)}
          />
        </Field>
        <div className="button-row">
          <Button
            data-testid="select-character-reference"
            variant="primary"
            disabled={
              readOnly ||
              busy ||
              !referenceCharacterId ||
              !referencePrimaryAssetId ||
              !referenceReviewer.trim() ||
              !referenceNotes.trim()
            }
            onClick={() => void onSelectReference()}
          >
            选择身份参考
          </Button>
          <small>每次选择会产生新版本；旧决定及其冻结引用保持可审计。</small>
        </div>
        <div className="media-candidate-grid" aria-label="当前角色身份参考比较">
          {bible.characters.map((character) => {
            const decision = currentReferenceByCharacter.get(character.id);
            const acceptedCast = decision?.characterContext.acceptedCast as
              | { revision?: number; contentHash?: string; castCharacterId?: string }
              | undefined;
            const referenceAssetIds = decision
              ? [decision.primaryAssetId, ...decision.complementaryAssetIds]
              : [];
            return (
              <article
                key={character.id}
                className="media-candidate"
                data-testid={`character-reference-${character.id}`}
              >
                {referenceAssetIds.length && projectId ? (
                  <div className="frozen-reference-set">
                    {referenceAssetIds.map((assetId, index) => {
                      const asset = assetById.get(assetId);
                      return asset ? (
                        <figure key={assetId}>
                          <img
                            src={plotloomApi.managedAssetUrl(
                              projectId,
                              asset.id,
                            )}
                            alt={`${character.name} ${index === 0 ? "主身份参考图" : "补充身份参考图"}`}
                          />
                          <figcaption>
                            {index === 0 ? "主参考图" : `补充参考图 ${index}`}{" "}
                            · {asset.id.slice(0, 8)}
                          </figcaption>
                        </figure>
                      ) : (
                        <small key={assetId}>
                          无法读取参考素材 {assetId.slice(0, 8)}。
                        </small>
                      );
                    })}
                  </div>
                ) : (
                  mediaReadPhase === "ready" ? <div className="notice warning">尚未选择身份参考</div>
                    : <small>当前身份参考状态尚未核验，请待媒体刷新完成。</small>
                )}
                <strong>
                  {character.name} ·{" "}
                  {decision?.current
                    ? `r${decision.referenceRevision}`
                    : mediaReadPhase === "ready" ? "尚未选择" : "状态未知"}
                </strong>
                <small>
                  {decision?.notes ??
                    (mediaReadPhase === "ready" ? "为有人物的镜头准备图片任务前，须先选择该人物的参考图。" : "读取完成前不会开放参考选择或图片请求。")}
                </small>
                {acceptedCast && (
                  <small data-testid={`cast-linked-reference-${character.id}`}>
                    已确认角色 · {acceptedCast.castCharacterId} · r
                    {acceptedCast.revision} · {acceptedCast.contentHash?.slice(0, 12)}
                  </small>
                )}
                {decision && (
                  <div className="button-row">
                    <small>
                      {decision.assetHashes.length} 项冻结源 ·{" "}
                      {decision.reviewer}
                    </small>
                    <Button
                      variant="danger"
                      disabled={readOnly || busy}
                      onClick={() =>
                        void onRevokeReference(character.id)
                      }
                    >
                      撤销
                    </Button>
                  </div>
                )}
              </article>
            );
          })}
        </div>
        {false && <details className="image-job-history">
          <summary>
            Story-first reference proposal（不创建 Shot、Approval 或自动选择）
          </summary>
          <div className="field-grid two compact">
            <Field label="角色">
              <select
                data-testid="proposal-character"
                value={proposalCharacterId}
                disabled={readOnly || busy}
                onChange={(event) => setProposalCharacterId(event.target.value)}
              >
                {bible.characters.map((character) => (
                  <option key={character.id} value={character.id}>
                    {character.name} · {character.id}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Story Bible revision">
              <input readOnly value={storyBibleRevision ?? "尚未保存"} />
            </Field>
          </div>
          <Field label="细化父候选（可选，仅同角色当前 proposal candidate）">
            <select
              data-testid="proposal-parent-candidate"
              value={proposalParentCandidateAssetId}
              disabled={readOnly || busy}
              onChange={(event) =>
                setProposalParentCandidateAssetId(event.target.value)
              }
            >
              <option value="">原始 proposal</option>
              {proposalCandidates.map(({ candidate }) => (
                <option key={candidate.assetId} value={candidate.assetId}>
                  细化 {candidate.assetId.slice(0, 8)} · {candidate.role}
                </option>
              ))}
            </select>
          </Field>
          <Field label="探索性视觉方向">
            <textarea
              data-testid="proposal-direction"
              rows={2}
              value={proposalDirection}
              disabled={readOnly || busy}
              placeholder="探索角色的稳定外观锚点；这不是 storyboard request。"
              onChange={(event) => setProposalDirection(event.target.value)}
            />
          </Field>
          <div className="button-row">
            <Button
              data-testid="prepare-character-proposal"
              variant="quiet"
              disabled={
                readOnly ||
                busy ||
                !storyBibleRevision ||
                !proposalCharacterId ||
                !proposalDirection.trim()
              }
              onClick={() => void onPrepareProposal()}
            >
              准备 proposal assignment
            </Button>
            <small>
              生成结果只进入候选池；创作者仍须显式把已导入资产选择为身份参考。
            </small>
          </div>
          {proposals.map((proposal) => (
            <article
              key={proposal.id}
              className="image-job-card"
              data-testid={`character-proposal-${proposal.id}`}
            >
              <strong>
                {proposal.characterId} ·{" "}
                {proposal.parentCandidateAssetId ? "REFINEMENT" : "ORIGINAL"} ·{" "}
                {proposal.state.toUpperCase()}
              </strong>
              <small>
                {" "}
                · {proposal.current ? "current" : "inapplicable/history"} ·{" "}
                {proposal.requestHash.slice(0, 12)}
              </small>
              {proposal.parentCandidateAssetId && (
                <small>
                  冻结 parent candidate ·{" "}
                  {proposal.parentCandidateAssetId.slice(0, 8)}
                </small>
              )}
              <div className="button-row">
                <Button
                  variant="quiet"
                  disabled={readOnly || busy || !proposal.current}
                  onClick={() =>
                    void onSendProposal(proposal.id)
                  }
                >
                  Send to specialist
                </Button>
                <Button
                  variant="quiet"
                  disabled={readOnly || busy}
                  onClick={() =>
                    void onRefreshProposal(proposal.id)
                  }
                >
                  检查 delivery
                </Button>
              </div>
              {proposal.deliveries
                .flatMap((delivery) => delivery.candidates)
                .map((candidate) => (
                  <div className="frozen-reference-set" key={candidate.id}>
                    {candidate.asset && projectId && (
                      <figure>
                        <img
                          src={plotloomApi.managedAssetUrl(
                            projectId,
                            candidate.asset.id,
                          )}
                          alt={`${proposal.characterId} proposal candidate`}
                        />
                        <figcaption>
                          candidate · {candidate.assetId.slice(0, 8)} ·{" "}
                          {candidate.role}
                        </figcaption>
                      </figure>
                    )}
                    <Button
                      data-testid={`refine-character-proposal-${candidate.assetId}`}
                      variant="quiet"
                      disabled={
                        readOnly ||
                        busy ||
                        !proposal.current ||
                        proposal.characterId !== proposalCharacterId
                      }
                      onClick={() =>
                        setProposalParentCandidateAssetId(candidate.assetId)
                      }
                    >
                      以此候选细化
                    </Button>
                  </div>
                ))}
            </article>
          ))}
        </details>}
      </section>

  );
}
