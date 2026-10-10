import net from "node:net";
import { test, checkedStaticTest, expect } from "./fixture";
import { demoProject } from "../src/demo";

for (const [mode, ownedTest] of [["Vite", test], ["checked static", checkedStaticTest]] as const) {
  ownedTest(`${mode} fixture owns distinct live endpoints and retains backend origin/data across restart`, async ({ page, request, workbench }) => {
    const origins = mode === "Vite"
      ? [workbench.apiOrigin, workbench.providerOrigin, workbench.frontendOrigin]
      : [workbench.apiOrigin, workbench.providerOrigin];
    expect(new Set(origins).size).toBe(origins.length);
    for (const origin of origins) await assertListenerCannotBeClaimed(origin);
    const providerBefore = await (await request.get(`${workbench.providerOrigin}/control/status`)).json();
    expect(providerBefore.totalRequests).toBe(0);

    const created = await request.post(`${workbench.apiOrigin}/api/v2/projects`, {
      data: { brief: { ...demoProject.brief, title: `Owned ${mode} restart` } },
    });
    expect(created.ok(), await created.text()).toBeTruthy();
    const projectId = (await created.json()).id;
    const endpoint = `/api/v2/projects/${projectId}`;
    const saved = await (await request.get(`${workbench.apiOrigin}${endpoint}`)).json();
    expect(await (await request.get(`${workbench.frontendOrigin}${endpoint}`)).json()).toEqual(saved);

    const hmr = mode === "Vite" ? page.waitForEvent("websocket").then(async socket => {
      expect(new URL(socket.url()).port).toBe(new URL(workbench.frontendOrigin).port);
      await socket.waitForEvent("framereceived", { predicate: frame => JSON.parse(String(frame.payload)).type === "connected" });
    }) : undefined;
    await page.goto(`${workbench.frontendOrigin}/v2/?project=${projectId}&stage=source`);
    if (hmr) {
      await hmr;
      const client = await request.get(`${workbench.frontendOrigin}/v2/@vite/client`);
      expect(client.ok()).toBeTruthy();
      expect(await client.text()).toContain(`const directSocketHost = "127.0.0.1:${new URL(workbench.frontendOrigin).port}/v2/"`);
    }
    await expect(page.getByRole("textbox", { name: "标题", exact: true })).toHaveValue(`Owned ${mode} restart`);
    const originalOrigin = workbench.apiOrigin;
    await workbench.restartBackend();
    expect(workbench.apiOrigin).toBe(originalOrigin);
    await assertListenerCannotBeClaimed(originalOrigin);
    expect(await (await request.get(`${workbench.apiOrigin}${endpoint}`)).json()).toEqual(saved);
    expect(await (await request.get(`${workbench.frontendOrigin}${endpoint}`)).json()).toEqual(saved);
    await page.reload();
    await expect(page.getByRole("textbox", { name: "标题", exact: true })).toHaveValue(`Owned ${mode} restart`);
    expect(await (await request.get(`${workbench.providerOrigin}/control/status`)).json()).toEqual(providerBefore);
  });
}

async function assertListenerCannotBeClaimed(origin: string) {
  const competingServer = net.createServer();
  const result = await new Promise<NodeJS.ErrnoException | undefined>(resolve => {
    competingServer.once("error", resolve);
    competingServer.listen(Number(new URL(origin).port), "127.0.0.1", () => resolve(undefined));
  });
  if (competingServer.listening) await new Promise<void>(resolve => competingServer.close(() => resolve()));
  expect(result?.code, `listener must remain owned: ${origin}`).toBe("EADDRINUSE");
}
