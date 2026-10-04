import path from "node:path";
import { expect, test } from "./fixture";

// Default mode keeps these two cases on one worker. Their runtime fixtures
// must still be independent, including after a successful root override.
test.describe("mutable workbench fixture isolation", () => {
  test.describe.configure({ mode: "default" });

  test("can leave a test-owned alternate installation active", async ({ request, workbench }) => {
    await workbench.restartBackend({
      PLOTLOOM_OUTPUTS_DIR: path.join(workbench.outputsRoot, "prior-test-root"),
      PLOTLOOM_APPLICATION_DATA_DIR: path.join(workbench.applicationDataRoot, "prior-test-root"),
    });
    const response = await request.post(`${workbench.apiOrigin}/api/v2/projects`, {
      data: { brief: { title: "Prior fixture's alternate installation", synopsis: "Fixture isolation regression." } },
    });
    expect(response.ok(), await response.text()).toBeTruthy();
  });

  test("owns original roots before and after its own backend restart", async ({ request, workbench }) => {
    const response = await request.post(`${workbench.apiOrigin}/api/v2/projects`, {
      data: { brief: { title: "New fixture's restart identity", synopsis: "Fixture restart identity regression." } },
    });
    expect(response.ok(), await response.text()).toBeTruthy();
    const { id } = await response.json() as { id: string };
    const endpoint = `${workbench.apiOrigin}/api/v2/projects/${id}`;
    const before = await request.get(endpoint);
    expect(before.ok(), await before.text()).toBeTruthy();
    await workbench.restartBackend();
    const after = await request.get(endpoint);
    expect(after.ok(), await after.text()).toBeTruthy();
    expect((await after.json() as { id: string }).id).toBe(id);
  });
});
