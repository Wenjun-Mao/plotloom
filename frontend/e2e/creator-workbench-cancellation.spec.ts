import { expect, test } from "./fixture";
import { createCreatorGraph } from "./fixtures/creator-graph";
import { json } from "./f5a-fixture";

test("delivered window blur cancels native resize from textarea focus without saving content", async ({ page, request, workbench }) => {
  await page.setViewportSize({ width: 1700, height: 900 });
  const id = await createCreatorGraph(request, workbench.apiOrigin, "focus-cancellation", 3, 2);
  await page.goto(`${workbench.frontendOrigin}/v2/?project=${id}&stage=creator`);
  const inspector = page.getByRole("complementary", { name: "当前节点详情" });
  const textarea = inspector.getByRole("textbox", { name: "剧情摘要", exact: true });
  const separator = page.getByRole("separator", { name: "调整节点详情宽度" });
  await expect(textarea).toBeVisible();
  const before = await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`));
  const writes: string[] = [];
  page.on("request", event => { if (["POST", "PUT", "PATCH", "DELETE"].includes(event.method())) writes.push(event.url()); });
  for (const original of [null, 350]) {
    if (original === null) await separator.dblclick();
    else { await separator.focus(); await page.keyboard.press("Home"); await page.keyboard.press("Shift+ArrowLeft"); }
    await textarea.focus();
    await textarea.evaluate(element => (element as HTMLTextAreaElement).setSelectionRange(1, 3));
    const content = await textarea.inputValue();
    const body = inspector.locator(".creator-inspector-body");
    const position = await body.evaluate(element => element.scrollTop);
    const handle = (await separator.boundingBox())!, width = (await inspector.boundingBox())!.width;
    await page.mouse.move(handle.x + 9, handle.y + 40); await page.mouse.down(); await page.mouse.move(handle.x - 80, handle.y + 40);
    expect((await inspector.boundingBox())!.width).toBeGreaterThan(width);
    await expect(textarea).toBeFocused();
    // Browser-tab activation did not deliver an OS window blur on this host.
    // Exercise event handling deterministically; pointer/focus remain native.
    await page.evaluate(() => window.dispatchEvent(new Event("blur")));
    expect((await inspector.boundingBox())!.width).toBeCloseTo(width, 0);
    await page.mouse.up();
    expect((await inspector.boundingBox())!.width).toBeCloseTo(width, 0);
    expect(await page.evaluate(id => JSON.parse(localStorage.getItem(`plotloom:creator-presentation:v1:${id}`)!).width, id)).toBe(original);
    await expect(textarea).toBeFocused(); await expect(textarea).toHaveValue(content);
    expect(await textarea.evaluate(element => [(element as HTMLTextAreaElement).selectionStart, (element as HTMLTextAreaElement).selectionEnd])).toEqual([1, 3]);
    expect(await body.evaluate(element => element.scrollTop)).toBe(position);
  }
  expect(writes).toEqual([]);
  expect((await json(request.get(`${workbench.apiOrigin}/api/v2/projects/${id}/graph-workbench`))).draft).toEqual(before.draft);
});
