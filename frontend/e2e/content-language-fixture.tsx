import { createRoot } from "react-dom/client";
import { useState } from "react";
import { useContentLanguageCheck } from "../src/features/content-language/useContentLanguageCheck";
import { ContentLanguageReview } from "../src/features/content-language/ContentLanguageReview";
import "../src/styles.css";
const original = { lang: "en", entries: [{ id: "hero", prose: "错误的语言。", literalText: "再见", providerTechnical: "English provider instructions." }] };
function Host() {
  const [candidate, setCandidate] = useState<Record<string, unknown>>(original);
  const check = useContentLanguageCheck({ projectId: "project", stage: "characters", jobId: "candidate", candidate, original, basis: "frozen-source" });
  return <main style={{ maxWidth: 900, margin: "auto", padding: 24 }}><h1>内容语言检查</h1><p>仅合成 HTTP 状态，不是实际助手检查。</p>
    <p>创作候选已完成结构交付，尚未经创作者采用。</p>
    <label>完整候选 JSON<textarea aria-label="完整候选 JSON" rows={8} value={JSON.stringify(candidate, null, 2)} onChange={event => { try { setCandidate(JSON.parse(event.target.value)); } catch { /* This fixture only submits complete JSON. */ } }} /></label>
    <ContentLanguageReview check={check} /><button disabled={!check.ready}>采用当前完整候选</button>
  </main>;
}
createRoot(document.getElementById("root")!).render(<Host />);
