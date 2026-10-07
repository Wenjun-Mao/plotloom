import { expect, test } from "./fixture";
import { createScriptProject, json } from "./f5a-fixture";

test.describe("current shared graph authoring", () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test("cancels, commits and undoes one exact draft transaction, then recovers unfinished prose", async ({ page, request, workbench }) => {
    const id = await createScriptProject(request, workbench.apiOrigin, "graph-commands", {}, []);
    const url = `${workbench.apiOrigin}/api/v2/projects/${id}`;
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=graph`);
    await expect(page.getByRole("heading", { name: "剧情图与精确合同" })).toBeVisible();
    await page.getByRole("button", { name: "新增未连接剧情节点", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "确认结构修改" });
    await expect(dialog).toContainText("新增节点");
    await dialog.getByRole("button", { name: "取消", exact: true }).click();
    let state = await json(request.get(`${url}/graph-workbench`));
    expect(state.draft.payload.mapping.topology.nodes).toHaveLength(4);
    await page.getByRole("button", { name: "新增未连接剧情节点", exact: true }).click();
    await dialog.getByRole("button", { name: "确认修改", exact: true }).click();
    await expect(dialog).toHaveCount(0);
    state = await json(request.get(`${url}/graph-workbench`));
    expect(state.draft.payload.mapping.topology.nodes).toHaveLength(5);
    const added = state.draft.payload.mapping.topology.nodes[4].id;
    await expect(page.locator(`[data-node-id="${added}"]`)).toBeVisible();
    await page.getByRole("button", { name: "撤销结构修改", exact: true }).click();
    await expect(page.getByRole("button", { name: "撤销结构修改", exact: true })).toBeDisabled();
    state = await json(request.get(`${url}/graph-workbench`));
    expect(state.draft.payload.mapping.topology.nodes).toHaveLength(4);
    await page.getByText("全部稳定身份与待连接关系", { exact: true }).click();
    await page.getByRole("button", { name: "Beacon lit", exact: true }).click();
    await page.getByRole("textbox", { name: "剧情摘要", exact: true }).fill("Unfinished current author prose");
    const save = page.getByRole("button", { name: "保存图草稿", exact: true });
    await save.click();
    // A click starts the asynchronous flush; reload must not abort its receipt
    // and leave the session buffer on an older CAS revision than the server.
    await expect(save).toBeEnabled();
    await expect.poll(async () => {
      const saved = await json(request.get(`${url}/graph-workbench`));
      return saved.draft.payload.mapping.sections.find((section: any) => section.sectionId === "beacon").summary;
    }).toBe("Unfinished current author prose");
    await page.reload();
    await expect(page.getByRole("dialog", { name: "草稿版本已过期", exact: true })).toHaveCount(0);
    await page.getByText("全部稳定身份与待连接关系", { exact: true }).click();
    await page.getByRole("button", { name: "Beacon lit", exact: true }).click();
    await expect(page.getByRole("textbox", { name: "剧情摘要", exact: true })).toHaveValue("Unfinished current author prose");
    const source = await json(request.get(`${url}/source-outline`));
    expect(source.acceptedSectionMap.mapping.sections.find((section: any) => section.sectionId === "beacon").summary).toBe("The beacon guides sailors through the storm.");
    expect(source.graphAdmission.graphRevision).toBe(1);
    expect((await json(request.get(`${url}/runs`))).runs).toEqual([]);
  });
});
