import { useEffect, useMemo, useState } from "react";
import { plotloomApi } from "../api";
import { Button, ErrorNotice, Field } from "../components";
import type { AcceptedCastRevision, CharacterReferenceProposal, VisualWorkbench } from "../types";

/** The F2B entry point: exploratory studies are owned by an accepted cast, not Bible or shots. */
export function CastReferenceStudiesPanel({ projectId, accepted, readOnly }: {
  projectId: string;
  accepted: AcceptedCastRevision;
  readOnly: boolean;
}) {
  const characters = useMemo(() => {
    const cast = Array.isArray(accepted.cast.characters) ? accepted.cast.characters : [];
    return cast.flatMap((item) => {
      if (!item || typeof item !== "object") return [];
      const character = item as Record<string, unknown>;
      const castId = typeof character.id === "string" ? character.id : "";
      const mapping = accepted.consumerMappings.find((entry) => entry.castCharacterId === castId);
      return mapping ? [{ id: mapping.consumerCharacterId, label: String(character.name || castId) }] : [];
    });
  }, [accepted]);
  const [proposals, setProposals] = useState<CharacterReferenceProposal[]>([]);
  const [workbench, setWorkbench] = useState<VisualWorkbench>();
  const [characterId, setCharacterId] = useState("");
  const [direction, setDirection] = useState("");
  const [parent, setParent] = useState("");
  const [reviewer, setReviewer] = useState("creator");
  const [notes, setNotes] = useState("");
  const [assignment, setAssignment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = async () => {
    const [nextProposals, nextWorkbench] = await Promise.all([
      plotloomApi.getCharacterReferenceProposals(projectId), plotloomApi.getVisualWorkbench(projectId),
    ]);
    setProposals(nextProposals.proposals); setWorkbench(nextWorkbench);
  };
  useEffect(() => { void refresh().catch((reason) => setError(reason.message)); }, [projectId]);
  useEffect(() => { if (!characterId && characters[0]) setCharacterId(characters[0].id); }, [characterId, characters]);
  const candidates = proposals.filter((proposal) => proposal.current && proposal.characterId === characterId)
    .flatMap((proposal) => proposal.deliveries.flatMap((delivery) => delivery.candidates.map((candidate) => ({ proposal, candidate }))));
  const state = workbench?.characterReferences.states.find((item) => item.characterId === characterId);
  const decisions = workbench?.characterReferences.decisions.filter((item) => item.characterId === characterId) ?? [];
  const currentDecision = decisions.find((item) => item.current);
  const act = async (operation: () => Promise<void>) => {
    setBusy(true); setError("");
    try { await operation(); await refresh(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Reference study operation failed"); }
    finally { setBusy(false); }
  };
  return <section className="panel cast-reference-studies" data-testid="cast-reference-studies">
    <header><span>06 · F2B identity reference studies</span><strong>accepted cast r{accepted.revision}</strong></header>
    <p>These exploratory studies freeze the accepted cast identity and appearance direction. They create no Story Bible, Shot, Approval, or production cross-shot claim.</p>
    <div className="field-grid two compact">
      <Field label="Cast subject"><select value={characterId} disabled={readOnly || busy} onChange={(event) => setCharacterId(event.target.value)}>{characters.map((character) => <option value={character.id} key={character.id}>{character.label} · {character.id}</option>)}</select></Field>
      <Field label="Frozen cast revision"><input readOnly value={`${accepted.revision} · ${accepted.contentHash.slice(0, 12)}`} /></Field>
      <Field label="Refinement parent"><select value={parent} disabled={readOnly || busy} onChange={(event) => setParent(event.target.value)}><option value="">Original study</option>{candidates.map(({ candidate }) => <option key={candidate.assetId} value={candidate.assetId}>{candidate.assetId.slice(0, 8)} · {candidate.role}</option>)}</select></Field>
      <Field label="Reference decision reviewer"><input value={reviewer} disabled={readOnly || busy} onChange={(event) => setReviewer(event.target.value)} /></Field>
    </div>
    <Field label="Pose / composition direction"><textarea rows={2} value={direction} disabled={readOnly || busy} placeholder="Specify a distinct study; the accepted appearance remains frozen." onChange={(event) => setDirection(event.target.value)} /></Field>
    <Field label="Selection notes"><textarea rows={2} value={notes} disabled={readOnly || busy} placeholder="Why this candidate is a stable identity reference." onChange={(event) => setNotes(event.target.value)} /></Field>
    <div className="button-row"><Button variant="primary" disabled={readOnly || busy || !characterId || !direction.trim()} onClick={() => void act(async () => { await plotloomApi.prepareCharacterReferenceProposal(projectId, { characterId, castRevision: accepted.revision, visualDirection: direction.trim(), parentCandidateAssetId: parent || undefined }); setDirection(""); setParent(""); })}>Prepare study assignment</Button><small>Only a current accepted cast can prepare or receive a study.</small></div>
    {assignment && <Field label="Frozen specialist assignment"><textarea readOnly rows={3} value={assignment} /></Field>}
    <section className="frozen-review-comparison" aria-label="cast reference decision history">
      <strong>Explicit reference decision</strong>
      {currentDecision ? <p data-testid="cast-current-reference">current r{currentDecision.referenceRevision} · {currentDecision.characterContextHash.slice(0, 12)} · {currentDecision.reviewer}<br />{currentDecision.notes}<br />asset hashes: {currentDecision.assetHashes.map((asset) => asset.originalHash.slice(0, 12)).join(", ")}</p> : <p>No current identity reference selected.</p>}
      {decisions.filter((decision) => !decision.current).map((decision) => <small key={decision.id}>historical r{decision.referenceRevision} · {decision.characterContextHash.slice(0, 12)} · {decision.revokedAt ? "revoked" : "superseded"}</small>)}
    </section>
    <div className="frozen-review-comparison">{proposals.filter((proposal) => proposal.characterId === characterId).map((proposal) => <article className="media-candidate" key={proposal.id}><strong>{proposal.parentCandidateAssetId ? "refinement" : "study"} · {proposal.current ? "current" : "historical"} · {proposal.requestHash.slice(0, 12)}</strong><div className="button-row"><Button variant="quiet" disabled={readOnly || busy || !proposal.current} onClick={() => void act(async () => { const copied = await plotloomApi.copyCharacterReferenceProposal(projectId, proposal.id); setAssignment(copied.assignment); })}>Copy assignment</Button><Button variant="quiet" disabled={readOnly || busy} onClick={() => void act(() => plotloomApi.refreshCharacterReferenceProposal(projectId, proposal.id).then(() => undefined))}>Refresh delivery</Button></div>{proposal.deliveries.flatMap((delivery) => delivery.candidates).map((candidate) => candidate.asset ? <figure key={candidate.id}><img src={plotloomApi.managedAssetUrl(projectId, candidate.asset.id)} alt={`${characterId} reference study`} /><figcaption>{candidate.assetId.slice(0, 8)} · {candidate.outputHash.slice(0, 12)}</figcaption><Button variant="quiet" disabled={readOnly || busy || !reviewer.trim() || !notes.trim() || !proposal.current} onClick={() => void act(() => plotloomApi.selectCharacterReference(projectId, { characterId, authority: "cast", primaryAssetId: candidate.assetId, complementaryAssetIds: [], expectedReferenceRevision: state?.revision ?? 0, reviewer: reviewer.trim(), notes: notes.trim() }).then(() => undefined))}>Select identity reference</Button><Button variant="quiet" disabled={readOnly || busy || !proposal.current} onClick={() => setParent(candidate.assetId)}>Use for refinement</Button></figure> : null)}</article>)}</div>
    {error && <ErrorNotice message={error} />}
  </section>;
}
