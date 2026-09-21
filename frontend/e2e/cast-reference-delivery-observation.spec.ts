import { expect, test, type Workbench } from "./fixture";
import {
  createAcceptedCastOnlyProject,
  makeProposalManifestInvalid,
  makeProposalPackageConflict,
  prepareProposalFromBrowser,
  proposal,
  sendProposalFromBrowser,
  writeProposalDelivery,
  writeProposalPartialDelivery,
} from "./fixtures/cast-reference";

test.describe("Characters delivery observation", () => {
  test("observes partial delivery and later admits its final result", async ({ page, request, workbench }) => {
    test.setTimeout(30_000);
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "partial-final");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const gallery = page.getByTestId("character-reference-gallery");
    await gallery.getByLabel("你想改什么").fill("Observe a partial package before its final original study.");
    const prepared = await prepareProposalFromBrowser(page, gallery, projectId, request, workbench.apiOrigin);
    let terminallyReleased = false;
    try {
      const packagePaths = await sendProposalFromBrowser(page, projectId, prepared.id);
      await writeProposalPartialDelivery(packagePaths.deliveryPath);
      const partial = await waitForAutomaticRefresh(page, projectId, prepared.id);
      expect(partial.status()).toBe(422);
      expect(await partial.json()).toMatchObject({ code: "delivery_partial" });
      await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, prepared.id)).deliveries[0]?.diagnosticCode).toBe("delivery_partial");
      await expect(gallery.locator(`[data-proposal-id="${prepared.id}"]`)).toContainText("delivery_partial");

      await writeProposalDelivery(packagePaths.deliveryPath, prepared, "f2b-partial-final", "original");
      const admitted = await waitForAutomaticRefresh(page, projectId, prepared.id);
      expect(admitted.status()).toBe(200);
      expect(await admitted.json()).toMatchObject({ state: "accepted" });
      terminallyReleased = true;
      await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, prepared.id)).deliveries[0]?.state).toBe("accepted");
      await expect(gallery).toContainText("当前候选，未选择");
    } finally {
      if (!terminallyReleased) await resetDisposableRuntime(workbench, "after-partial-final-failure");
    }
  });

  test("records a final-invalid Characters delivery without publishing a candidate", async ({ page, request, workbench }) => {
    test.setTimeout(20_000);
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "final-invalid");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const gallery = page.getByTestId("character-reference-gallery");
    await gallery.getByLabel("你想改什么").fill("Persist the final-invalid delivery diagnostic.");
    const prepared = await prepareProposalFromBrowser(page, gallery, projectId, request, workbench.apiOrigin);
    let terminallyReleased = false;
    try {
      const packagePaths = await sendProposalFromBrowser(page, projectId, prepared.id);
      await writeProposalDelivery(packagePaths.deliveryPath, prepared, "f2b-final-invalid", "original");
      await makeProposalManifestInvalid(packagePaths.deliveryPath);

      const invalid = await waitForAutomaticRefresh(page, projectId, prepared.id);
      expect(invalid.status()).toBe(422);
      expect(await invalid.json()).toMatchObject({ code: "delivery_manifest_invalid" });
      await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, prepared.id)).deliveries[0]).toMatchObject({
        state: "rejected",
        diagnosticCode: "delivery_manifest_invalid",
        candidates: [],
      });
      await expect(gallery.locator(`[data-proposal-id="${prepared.id}"]`)).toContainText("delivery_manifest_invalid");

      // This test's terminal cleanup is an inapplicable delivery, the only
      // supported way to release a lease after observing an invalid outcome.
      const cancelled = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-reference-proposals/${prepared.id}/cancel`, {
        data: { reason: "Release the test-only native-dispatch lease after final-invalid evidence." },
      });
      expect(cancelled.ok(), await cancelled.text()).toBeTruthy();
      await writeProposalDelivery(packagePaths.deliveryPath, prepared, "f2b-final-invalid-cleanup", "original");
      const cleanup = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-reference-proposals/${prepared.id}/refresh`);
      expect(cleanup.ok(), await cleanup.text()).toBeTruthy();
      expect(await cleanup.json()).toMatchObject({ state: "inapplicable", candidates: [] });
      terminallyReleased = true;
    } finally {
      if (!terminallyReleased) await resetDisposableRuntime(workbench, "after-final-invalid-failure");
    }
  });

  test("stops automatic Characters polling after refreshed package-conflict state", async ({ page, request, workbench }) => {
    test.setTimeout(20_000);
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "conflict-stop");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const gallery = page.getByTestId("character-reference-gallery");
    await gallery.getByLabel("你想改什么").fill("Expose the immutable package conflict in the gallery.");
    const prepared = await prepareProposalFromBrowser(page, gallery, projectId, request, workbench.apiOrigin);
    let refreshRequests = 0;
    const observeRefresh = (browserRequest: import("@playwright/test").Request) => {
      if (browserRequest.method() === "POST" && refreshPath(projectId, prepared.id) === new URL(browserRequest.url()).pathname) refreshRequests += 1;
    };
    page.on("request", observeRefresh);
    try {
      const packagePaths = await sendProposalFromBrowser(page, projectId, prepared.id);
      await makeProposalPackageConflict(packagePaths.packagePath);
      const conflict = await waitForAutomaticRefresh(page, projectId, prepared.id);
      expect(conflict.status()).toBe(409);
      expect(await conflict.json()).toMatchObject({ code: "package_conflict" });
      await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, prepared.id)).deliveries[0]).toMatchObject({
        state: "rejected",
        diagnosticCode: "package_conflict",
        candidates: [],
      });
      await expect(gallery.locator(`[data-proposal-id="${prepared.id}"]`)).toContainText("package_conflict");

      const countAfterRefreshedConflict = refreshRequests;
      await page.waitForTimeout(3_500);
      expect(refreshRequests).toBe(countAfterRefreshedConflict);
    } finally {
      page.off("request", observeRefresh);
      // The test deliberately proves that an immutable package conflict cannot
      // produce a terminal delivery. Reset only this disposable test runtime
      // before later browser files receive their own native-dispatch fixture.
      await resetDisposableRuntime(workbench, "after-package-conflict");
    }
  });
});

function refreshPath(projectId: string, proposalId: string): string {
  return `/api/v2/projects/${projectId}/character-reference-proposals/${proposalId}/refresh`;
}

function waitForAutomaticRefresh(
  page: import("@playwright/test").Page,
  projectId: string,
  proposalId: string,
) {
  const path = refreshPath(projectId, proposalId);
  return page.waitForResponse((response) => response.request().method() === "POST"
    && new URL(response.url()).pathname === path, { timeout: 10_000 });
}

async function resetDisposableRuntime(workbench: Workbench, suffix: string): Promise<void> {
  await workbench.restartBackend({
    PLOTLOOM_APPLICATION_DATA_DIR: `${workbench.applicationDataRoot}/${suffix}`,
    PLOTLOOM_OUTPUTS_DIR: `${workbench.outputsRoot}/${suffix}`,
  });
}
