import WorkspaceApp from "./app/WorkspaceApp";
import { PlayView } from "./play/PlayView";

/**
 * The Play view deliberately branches before the workspace mounts.  Its URL is
 * a lightweight viewing surface over the canonical project and selected media,
 * not another editor route or persisted player session.
 */
export default function App() {
  return new URLSearchParams(window.location.search).get("view") === "play"
    ? <PlayView />
    : <WorkspaceApp />;
}
