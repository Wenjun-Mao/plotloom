import { createRoot } from "react-dom/client";

import "../src/styles.css";
import { ArtReferenceGallery } from "../src/pages/ArtReferenceGallery";
import type { ArtReferenceProposal, ManagedAsset } from "../src/types";

const projectId = "f3b-read-only-demo";
const createdAt = "2026-09-22T00:00:00Z";
const provenance = { origin: "Portable read-only F3B demonstration (explicit mock)", rights: "unknown" as const, rightsNote: "Static SVG test card; no ImageGen, provider, or creative approval.", declaredAdditions: [] };

function mockAsset(subject: "scene" | "prop", letter: string): ManagedAsset {
  const id = `demo-${subject}-${letter.toLowerCase()}`;
  return { id, projectId, originalHash: `${id}-original`, displayHash: `${id}-display`, mimeType: "image/svg+xml", byteSize: 512, width: 960, height: 540, createdAt, provenance };
}

function mockStudy(subjectType: "scene" | "prop", subjectId: string, label: string): ArtReferenceProposal {
  const candidates = ["A", "B", "C", "D", "E"].map((letter) => {
    const asset = mockAsset(subjectType, letter);
    return { id: `${asset.id}-candidate`, assetId: asset.id, proposalId: `demo-${subjectType}-study`, outputFilename: `${label}-${letter}.svg`, outputHash: `${asset.id}-output`, role: "art_reference" as const, asset, createdAt };
  });
  return { id: `demo-${subjectType}-study`, projectId, subjectType, subjectId, request: { demonstration: "可移植只读浏览器演示（明确 mock；静态 A–E 测试卡）" }, requestHash: `demo-${subjectType}-request`, state: "delivered", current: true, exportedAt: createdAt, cancelledAt: null, cancellationReason: null, createdAt, deliveries: [{ id: `demo-${subjectType}-delivery`, deliveryId: `demo-${subjectType}-read-only`, state: "accepted", diagnosticCode: null, manifestHash: `demo-${subjectType}-static`, createdAt, candidates }] };
}

const art = {
  source: "Portable read-only mock; no production data.", style: "demo",
  scenes: [{ id: "S-DEMO", name: "Scene · signal room", summary: "Mock scene subject for image-review interaction.", anchors: [], lighting: [], image: { prompt: "", negativePrompt: "", sheet: "", tags: [] } }],
  props: [{ id: "P-DEMO", name: "Prop · brass compass", summary: "Mock prop subject for isolation review.", anchors: [], image: { prompt: "", negativePrompt: "", sheet: "", tags: [] } }],
};

function Demo() {
  return <main className="page source-outline-page" data-testid="f3b-portable-demo">
    <header className="page-header"><div><span>TEST-ONLY · LOCAL LOOPBACK</span><h1>F3B environment / prop review</h1><p>Portable, read-only presentation fixture. Its static SVG cards are explicitly mocked and cannot write project or provider state.</p></div></header>
    <article className="panel cast-panel art-panel">
      <ArtReferenceGallery projectId={projectId} art={art} acceptedRevision={1} acceptedContentHash="portable-mock" studies={[mockStudy("scene", "S-DEMO", "scene"), mockStudy("prop", "P-DEMO", "prop")]} readOnly busy={false} setAssignment={() => undefined} refresh={async () => undefined} />
    </article>
  </main>;
}

createRoot(document.getElementById("root")!).render(<Demo />);
