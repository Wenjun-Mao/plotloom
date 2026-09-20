import WorkspaceApp from "./app/WorkspaceApp";
import { PlayView } from "./play/PlayView";
import { StoryPrototypePage } from "./pages/StoryPrototypePage";
import { CharacterReferenceGalleryPage } from "./pages/CharacterReferenceGalleryPage";

/**
 * The Play view deliberately branches before the workspace mounts.  Its URL is
 * a lightweight viewing surface over the canonical project and selected media,
 * not another editor route or persisted player session.
 */
export default function App() {
  const view = new URLSearchParams(window.location.search).get("view");
  if (view === "play") return <PlayView />;
  if (view === "story-prototype") return <StoryPrototypePage />;
  if (view === "character-reference-review") return <CharacterReferenceGalleryPage />;
  return <WorkspaceApp />;
}
