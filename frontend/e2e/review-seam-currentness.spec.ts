import { acknowledgeGraphMapping, graphDraftRevision } from "./fixtures/graph-authoring";
import { expect, test } from "./fixture";
import { availableSpecialistWithoutSend, createScriptProject, fixture, json, writeDelivery } from "./f5a-fixture";
import type { APIRequestContext } from "@playwright/test";

async function invalidate(request: APIRequestContext, origin: string, id: string, stage: "cast" | "script") {
  const project = `${origin}/api/v2/projects/${id}`;
  if (stage === "script") {
    const { acceptedArt: base } = await json(request.get(`${project}/art`));
    await json(request.post(`${project}/art/reopen`, { data: { expectedArtRevision: base.revision } }));
    const art = structuredClone(base.art);
    art.scenes[0].summary += " Current upstream revision.";
    await json(request.post(`${project}/art/save`, { data: { expectedArtRevision: base.revision, binding: base.binding, art } }));
    return;
  }
  const root = `${project}/source-outline`;
  const base = await json(request.get(root));
  const graph = (await json(request.get(`${project}/stages`))).stages.find((item: any) => item.head.stage === "story_graph").head;
  const mapping = structuredClone(base.acceptedSectionMap.mapping);
  mapping.sections[0].summary += " Current map context.";
  const draftRevision = await acknowledgeGraphMapping(request, project, mapping);
  const next = await json(request.put(`${root}/section-map`, { data: {
    expectedSectionMapRevision: base.acceptedSectionMap.revision,
    expectedSourceRevision: base.source.revision, expectedOutlineRevision: base.acceptedOutline.revision,
    expectedOutlineContentHash: base.acceptedOutline.contentHash, mapping, expectedGraphDraftRevision: draftRevision,
  } }));
  await json(request.post(`${root}/section-map/install-graph`, { data: {
    expectedSourceRevision: next.source.revision, expectedSourceContentHash: next.source.contentHash,
    expectedOutlineRevision: next.acceptedOutline.revision, expectedOutlineContentHash: next.acceptedOutline.contentHash,
    expectedSectionMapRevision: next.acceptedSectionMap.revision, expectedSectionMapContentHash: next.acceptedSectionMap.contentHash,
    expectedGraphRevision: graph.revision, expectedGraphDraftRevision: await graphDraftRevision(request, project),
  } }));
}

for (const stage of ["cast", "script"] as const) {
  for (const ready of [false, true]) test(`first stale ${stage} ${ready ? "ready" : "prepared"} candidate has no acceptance authority`, async ({ page, request, workbench }) => {
    const id = await createScriptProject(request, workbench.apiOrigin, `first-${stage}-${ready}`, {}, stage === "cast" ? [] : ["cast", "art"]);
    const url = `${workbench.apiOrigin}/api/v2/projects/${id}/${stage}`;
    const prepared = await json(request.post(`${url}/candidates`));
    const sends = await availableSpecialistWithoutSend(page, id, stage === "cast" ? "characters" : stage, prepared.jobId);
    if (ready) {
      await writeDelivery(prepared, stage === "cast" ? "characters" : stage, await fixture(`${stage}.json`));
      await json(request.post(`${url}/candidates/${prepared.jobId}/refresh`));
    }
    const browserUrl = `${workbench.frontendOrigin}/v2/?project=${id}&stage=${stage === "cast" ? "characters" : "source#script"}`;
    await page.goto(browserUrl);
    const panel = page.getByTestId(`${stage}-review`);
    await expect(panel.getByRole("button", { name: ready ? (stage === "cast" ? "确认使用此角色设定" : "确认使用此剧本") : "发送给文字创作助手" })).toBeEnabled();
    await invalidate(request, workbench.apiOrigin, id, stage);
    const state = await json(request.get(url));
    expect(state[stage === "cast" ? "acceptedCast" : "acceptedScript"]).toBeNull();
    expect(state.status).toBe("stale");
    await page.reload();
    await expect(panel).toContainText("上下文已过期");
    if (ready) {
      await expect(panel.getByRole("button", { name: stage === "cast" ? "确认使用此角色设定" : "确认使用此剧本" })).toBeDisabled();
    } else {
      await expect(panel.getByRole("button", { name: "发送给文字创作助手" })).toBeDisabled();
      await expect(panel.getByRole("button", { name: "立即检查" })).toBeEnabled();
      await expect(panel.getByRole("button", { name: "取消此任务", exact: true })).toBeEnabled();
    }
    expect(sends()).toBe(0);
  });

  test(`current ${stage} replacement remains dispatchable and acceptable over stale retained evidence`, async ({ page, request, workbench }) => {
    const id = await createScriptProject(request, workbench.apiOrigin, `replacement-${stage}`);
    const url = `${workbench.apiOrigin}/api/v2/projects/${id}/${stage}`;
    const acceptedKey = stage === "cast" ? "acceptedCast" : "acceptedScript";
    const retained = (await json(request.get(url)))[acceptedKey];
    await invalidate(request, workbench.apiOrigin, id, stage);
    expect((await json(request.get(url))).status).toBe("stale");
    const prepared = await json(request.post(`${url}/candidates`));
    const sends = await availableSpecialistWithoutSend(page, id, stage === "cast" ? "characters" : stage, prepared.jobId);
    const current = await json(request.get(url));
    expect(current.status).toBe("prepared");
    expect(current.staleReasons).toEqual([]);
    expect(current[acceptedKey]).toEqual(retained);
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=${stage === "cast" ? "characters" : "source#script"}`);
    const panel = page.getByTestId(`${stage}-review`);
    await expect(panel.getByRole("button", { name: "发送给文字创作助手" })).toBeEnabled();
    await writeDelivery(prepared, stage === "cast" ? "characters" : stage, await fixture(`${stage}.json`));
    await json(request.post(`${url}/candidates/${prepared.jobId}/refresh`));
    await page.reload();
    const accept = panel.getByRole("button", { name: stage === "cast" ? "确认使用此角色设定" : "确认使用此剧本" });
    await expect(accept).toBeEnabled();
    expect((await json(request.get(url)))[acceptedKey]).toEqual(retained);
    await accept.click();
    await expect(panel).toContainText(stage === "cast" ? "已确认角色设定 r2" : "已确认 r2");
    expect(sends()).toBe(0);
  });
}
