// Attended performance fixture: native API/read owners, no automatic approval.
import { createRoot } from "react-dom/client";
import { useEffect, useState } from "react";
import { MaterialReview } from "../src/features/autopilot/MaterialReview";
import { VideoBatchReview } from "../src/features/video-batch/VideoBatchReview";
import { batchApi } from "../src/features/video-batch/api";
import type { Batch } from "../src/features/video-batch/contracts";
import "../src/styles.css";
import "../src/features/autopilot/autopilot.css";
import "../src/creator-ui.css";
const projectId = new URLSearchParams(location.search).get("project")!;
function Host() {
  const video = new URLSearchParams(location.search).get("review") === "video";
  const [batch, setBatch] = useState<Batch | null>(null);
  useEffect(() => { if(video) void batchApi.current(projectId).then(setBatch); }, []);
  return video ? batch && <VideoBatchReview projectId={projectId} batch={batch} disabled={false} onClose={()=>{}} onSaved={async()=>{}} />
    : <MaterialReview projectId={projectId} onClose={()=>{}} onAccepted={async()=>{}} onUncertain={()=>{}} />;
}
createRoot(document.getElementById("root")!).render(<Host />);
