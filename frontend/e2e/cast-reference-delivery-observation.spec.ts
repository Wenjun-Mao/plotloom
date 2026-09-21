import { expect, test, type Workbench } from "./fixture";
import {
  createAcceptedCastOnlyProject,
  makeProposalManifestInvalid,
  makeProposalOutputSetPartial,
  makeProposalPackageConflict,
  prepareProposalFromBrowser,
  proposal,
  sendProposalFromBrowser,
  writeProposalDelivery,
  writeProposalPartialDelivery,
} from "./fixtures/cast-reference";

test.describe("Characters delivery observation", () => {
  test("keeps repeated pre-final delivery observations pending and later admits one final result", async ({ page, request, workbench }) => {
    test.setTimeout(30_000);
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "partial-final");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const gallery = page.getByTestId("character-reference-gallery");
    await gallery.getByLabel("想法").fill("Observe a partial package before its final original study.");
    const prepared = await prepareProposalFromBrowser(page, gallery, projectId, request, workbench.apiOrigin);
    let terminallyReleased = false;
    try {
      const packagePaths = await sendProposalFromBrowser(page, projectId, prepared.id);
      await writeProposalPartialDelivery(packagePaths.deliveryPath);
      let pendingPolls = 0;
      const observePending = (browserRequest: import("@playwright/test").Request) => {
        if (browserRequest.method() === "POST" && refreshPath(projectId, prepared.id) === new URL(browserRequest.url()).pathname) pendingPolls += 1;
      };
      page.on("request", observePending);
      try {
        const pending = await waitForAutomaticRefresh(page, projectId, prepared.id);
        expect(pending.status()).toBe(200);
        expect(await pending.json()).toMatchObject({ state: "awaiting_delivery", candidates: [] });
        await page.waitForTimeout(6_500);
        expect(pendingPolls).toBeGreaterThanOrEqual(3);
        await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, prepared.id)).deliveries).toEqual([]);
        await expect(gallery.locator(`[data-proposal-id="${prepared.id}"]`)).not.toContainText("delivery_partial");
      } finally {
        page.off("request", observePending);
      }

      await writeProposalDelivery(packagePaths.deliveryPath, prepared, "f2b-partial-final", "original");
      const admitted = await waitForAutomaticRefresh(page, projectId, prepared.id);
      expect(admitted.status()).toBe(200);
      expect(await admitted.json()).toMatchObject({ state: "accepted" });
      terminallyReleased = true;
      await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, prepared.id)).deliveries[0]?.state).toBe("accepted");
      await expect(gallery.getByTestId("appearance-viewer")).toContainText("候选图片");
    } finally {
      if (!terminallyReleased) await resetDisposableRuntime(workbench, "after-partial-final-failure");
    }
  });

  test("records a final-invalid Characters delivery without publishing a candidate", async ({ page, request, workbench }) => {
    test.setTimeout(20_000);
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "final-invalid");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const gallery = page.getByTestId("character-reference-gallery");
    await gallery.getByLabel("想法").fill("Persist the final-invalid delivery diagnostic.");
    const prepared = await prepareProposalFromBrowser(page, gallery, projectId, request, workbench.apiOrigin);
    let terminallyReleased = false;
    try {
      const packagePaths = await sendProposalFromBrowser(page, projectId, prepared.id);
      await writeProposalDelivery(packagePaths.deliveryPath, prepared, "f2b-final-invalid", "original");
      await makeProposalManifestInvalid(packagePaths.deliveryPath);

      const invalid = await waitForAutomaticRefresh(page, projectId, prepared.id);
      expect(invalid.status(), await invalid.text()).toBe(422);
      expect(await invalid.json()).toMatchObject({ code: "delivery_manifest_invalid" });
      await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, prepared.id)).deliveries[0]).toMatchObject({
        state: "rejected",
        diagnosticCode: "delivery_manifest_invalid",
        publicationPhase: "final",
        candidates: [],
      });
      const failedCard = gallery.locator(`[data-proposal-id="${prepared.id}"]`).first();
      await expect(failedCard).toContainText("delivery_manifest_invalid");
      await expect(failedCard).toContainText("本次交付未通过，未加入图片列表");
      await expect(failedCard).not.toContainText("返回图片会出现在上方");

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

  test("keeps a post-marker partial delivery visible as a final integrity failure", async ({ page, request, workbench }) => {
    test.setTimeout(20_000);
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "final-partial");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const gallery = page.getByTestId("character-reference-gallery");
    await gallery.getByLabel("想法").fill("Expose final output-set integrity failure.");
    const prepared = await prepareProposalFromBrowser(page, gallery, projectId, request, workbench.apiOrigin);
    let terminallyReleased = false;
    try {
      const packagePaths = await sendProposalFromBrowser(page, projectId, prepared.id);
      await writeProposalDelivery(packagePaths.deliveryPath, prepared, "f2b-final-partial", "original");
      await makeProposalOutputSetPartial(packagePaths.deliveryPath);

      const invalid = await waitForAutomaticRefresh(page, projectId, prepared.id);
      expect(invalid.status(), await invalid.text()).toBe(422);
      expect(await invalid.json()).toMatchObject({ code: "delivery_partial" });
      await expect.poll(async () => (await proposal(request, workbench.apiOrigin, projectId, prepared.id)).deliveries[0]).toMatchObject({
        state: "rejected",
        diagnosticCode: "delivery_partial",
        publicationPhase: "final",
        candidates: [],
      });
      await expect(gallery.locator(`[data-proposal-id="${prepared.id}"]`)).toContainText("delivery_partial");
      await expect(gallery.getByTestId("historical-partial-deliveries")).toHaveCount(0);

      const cancelled = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-reference-proposals/${prepared.id}/cancel`, {
        data: { reason: "Release the test-only native-dispatch lease after final output-set evidence." },
      });
      expect(cancelled.ok(), await cancelled.text()).toBeTruthy();
      await writeProposalDelivery(packagePaths.deliveryPath, prepared, "f2b-final-partial-cleanup", "original");
      const cleanup = await request.post(`${workbench.apiOrigin}/api/v2/projects/${projectId}/character-reference-proposals/${prepared.id}/refresh`);
      expect(cleanup.ok(), await cleanup.text()).toBeTruthy();
      terminallyReleased = true;
    } finally {
      if (!terminallyReleased) await resetDisposableRuntime(workbench, "after-final-partial-failure");
    }
  });

  test("stops automatic Characters polling after refreshed package-conflict state", async ({ page, request, workbench }) => {
    test.setTimeout(20_000);
    const projectId = await createAcceptedCastOnlyProject(request, workbench.apiOrigin, "conflict-stop");
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=characters`);
    const gallery = page.getByTestId("character-reference-gallery");
    await gallery.getByLabel("想法").fill("Expose the immutable package conflict in the gallery.");
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
