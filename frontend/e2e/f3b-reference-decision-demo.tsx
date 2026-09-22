import { createRoot } from "react-dom/client";
import { useState } from "react";

import "../src/styles.css";
import { ArtReferenceGallery } from "../src/pages/ArtReferenceGallery";
import type { ArtReferenceDecision, ArtReferenceDecisionState, ArtReferenceProposal, ManagedAsset } from "../src/types";

const projectId = "f3b-local-decision-simulator";
const createdAt = "2026-09-22T00:00:00Z";
const provenance = { origin: "Portable local simulator (explicit mock)", rights: "unknown" as const, rightsNote: "Static SVG test card; no ImageGen, provider, project write, or creative approval.", declaredAdditions: [] };

function staticCardUrl(id: string) {
  const letter = id.split("-").at(-1)?.toUpperCase() || "?";
  const prop = id.includes("prop");
  const [base, accent] = ({ A: ["#164e63", "#67e8f9"], B: ["#4c1d95", "#c4b5fd"], C: ["#713f12", "#fde68a"], D: ["#7f1d1d", "#fca5a5"], E: ["#14532d", "#86efac"] } as Record<string, string[]>)[letter] || ["#334155", "#cbd5e1"];
  const subject = prop ? "PROP" : "SCENE";
  const shape = prop ? `<path d="M480 100 690 270 570 440 390 440 270 270Z" fill="${accent}"/><circle cx="480" cy="270" r="70" fill="${base}"/>` : `<path d="M120 390 320 170 450 300 590 120 840 390Z" fill="${accent}"/><circle cx="720" cy="150" r="52" fill="${base}"/>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540"><rect width="960" height="540" fill="${base}"/><path d="M0 0h960v540H0z" fill="url(#g)"/><defs><pattern id="p" width="42" height="42" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><path d="M0 0h42v8H0z" fill="#fff" opacity=".13"/></pattern><linearGradient id="g"><stop stop-color="#020617" stop-opacity=".32"/><stop offset="1" stop-color="#000" stop-opacity=".05"/></linearGradient></defs><rect width="960" height="540" fill="url(#p)"/>${shape}<text x="48" y="70" fill="white" font-family="system-ui" font-size="30" font-weight="700">${subject} · LOCAL ${letter}</text><text x="48" y="505" fill="white" font-family="system-ui" font-size="18">static data URL · no project API or generated media</text></svg>`)}`;
}

function asset(subject: "scene" | "prop", letter: string): ManagedAsset {
  const id = `demo-${subject}-${letter.toLowerCase()}`;
  return { id, projectId, originalHash: `${id}-original`, displayHash: `${id}-display`, mimeType: "image/svg+xml", byteSize: 512, width: 960, height: 540, createdAt, provenance };
}

function study(subjectType: "scene" | "prop", subjectId: string, label: string): ArtReferenceProposal {
  const candidates = ["A", "B", "C", "D", "E"].map((letter) => {
    const item = asset(subjectType, letter);
    return { id: `${item.id}-candidate`, assetId: item.id, proposalId: `sim-${subjectType}-study`, outputFilename: `${label}-${letter}.svg`, outputHash: `${item.id}-output`, role: "art_reference" as const, asset: item, createdAt };
  });
  return { id: `sim-${subjectType}-study`, projectId, subjectType, subjectId, request: { demonstration: "本地模拟：按钮只更新此页面内存，绝不发送 API、写入项目或声明 ImageGen 交付。" }, requestHash: `sim-${subjectType}-request`, state: "delivered", current: true, exportedAt: createdAt, cancelledAt: null, cancellationReason: null, createdAt, deliveries: [{ id: `sim-${subjectType}-delivery`, deliveryId: `sim-${subjectType}-local`, state: "accepted", diagnosticCode: null, manifestHash: `sim-${subjectType}-static`, createdAt, candidates }] };
}

const art = {
  source: "Portable local decision simulator; no production data.", style: "demo",
  scenes: [{ id: "S-DEMO", name: "Scene · signal room", summary: "Local simulated scene subject.", anchors: [], lighting: [], image: { prompt: "", negativePrompt: "", sheet: "", tags: [] } }],
  props: [{ id: "P-DEMO", name: "Prop · brass compass", summary: "Local simulated prop subject.", anchors: [], image: { prompt: "", negativePrompt: "", sheet: "", tags: [] } }],
};

function Demo() {
  const [studies, setStudies] = useState([study("scene", "S-DEMO", "scene"), study("prop", "P-DEMO", "prop")]);
  const [decisions, setDecisions] = useState<ArtReferenceDecision[]>([]);
  const [states, setStates] = useState<ArtReferenceDecisionState[]>([]);

  const choose = async (body: { subjectType: "scene" | "prop"; subjectId: string; assetId: string; expectedReferenceRevision: number }) => {
    const candidate = studies.flatMap((item) => item.deliveries.flatMap((delivery) => delivery.candidates)).find((item) => item.assetId === body.assetId);
    if (!candidate?.asset) throw new Error("Local simulator candidate is unavailable.");
    const state = states.find((item) => item.subjectType === body.subjectType && item.subjectId === body.subjectId);
    if ((state?.revision || 0) !== body.expectedReferenceRevision) throw new Error("Local simulator CAS conflict.");
    const decision: ArtReferenceDecision = {
      id: `sim-decision-${body.subjectType}-${body.subjectId}-${body.expectedReferenceRevision + 1}`,
      projectId, subjectType: body.subjectType, subjectId: body.subjectId, referenceRevision: body.expectedReferenceRevision + 1,
      acceptedArtRevision: 1, acceptedArtHash: "portable-local-simulator", subject: { id: body.subjectId, type: body.subjectType }, subjectHash: `sim-${body.subjectType}-${body.subjectId}`,
      assetId: candidate.assetId, assetHash: candidate.asset.originalHash, proposalId: candidate.proposalId, candidateId: candidate.id, current: true, createdAt,
    };
    return decision;
  };
  const recordDecision = (decision: ArtReferenceDecision) => {
    setDecisions((prior) => [decision, ...prior.map((item) => item.subjectType === decision.subjectType && item.subjectId === decision.subjectId ? { ...item, current: false } : item)]);
    setStates((prior) => {
      const next = { subjectType: decision.subjectType, subjectId: decision.subjectId, revision: decision.referenceRevision, activeDecisionId: decision.id, current: true } as ArtReferenceDecisionState;
      return [...prior.filter((item) => item.subjectType !== decision.subjectType || item.subjectId !== decision.subjectId), next];
    });
  };
  const markStale = (subjectType: "scene" | "prop") => {
    setStudies((prior) => prior.map((item) => item.subjectType === subjectType ? { ...item, current: false } : item));
    setDecisions((prior) => prior.map((item) => item.subjectType === subjectType ? { ...item, current: false } : item));
    setStates((prior) => prior.map((item) => item.subjectType === subjectType ? { ...item, current: false } : item));
  };
  const restore = () => setStudies([study("scene", "S-DEMO", "scene"), study("prop", "P-DEMO", "prop")]);

  return <main className="page source-outline-page" data-testid="f3b-local-decision-simulator">
    <header className="page-header"><div><span>TEST-ONLY · LOCAL STATE</span><h1>F3B reference-decision simulator</h1><p>Real review UI with static cards and page-memory-only choice/replacement. It is not a project, persistence, provider, or creative-approval walkthrough.</p></div></header>
    <section className="notice warning"><strong>模拟边界：</strong>“用作此环境/道具的参考图”只更新此页面的 React state。后端持久化、重启和真实 F3B 交付由自动化回归另行证明；此页面不访问它们。</section>
    <div className="button-row"><button type="button" onClick={() => markStale("scene")}>模拟环境美术变更 → 标记陈旧</button><button type="button" onClick={() => markStale("prop")}>模拟道具美术变更 → 标记陈旧</button><button type="button" onClick={restore}>恢复当前模拟研究</button></div>
    <article className="panel cast-panel art-panel">
      <ArtReferenceGallery projectId={projectId} art={art} acceptedRevision={1} acceptedContentHash="portable-local-simulator" studies={studies} decisions={decisions} decisionStates={states} readOnly={false} busy={false} setAssignment={() => undefined} refresh={async () => undefined} createReferenceDecision={choose} onReferenceDecisionCreated={recordDecision} showStudyActions={false} assetUrl={staticCardUrl} />
    </article>
  </main>;
}

createRoot(document.getElementById("root")!).render(<Demo />);
