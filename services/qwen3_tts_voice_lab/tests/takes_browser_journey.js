async (page) => {
  if (new URL(page.url()).port !== '8898') throw new Error('fixture origin required');
  const origin = 'http://127.0.0.1:8898';
  const request = async (path, method = 'GET', body) => {
    const response = await page.request.fetch(origin + path, { method, ...(body ? { data: body } : {}) });
    if (!response.ok()) throw new Error(await response.text());
    return response.status() === 204 ? null : response.json();
  };
  let project = await request('/api/projects', 'POST', { name: 'Take 浏览器验收' });
  project = await request('/api/projects/' + project.projectId, 'PUT', { expectedRevision: project.revision, name: project.name, brief: 'fixture', auditionText: '参考声音。' });
  project = await request(`/api/projects/${project.projectId}/candidates`, 'POST', { expectedProjectRevision: project.revision, direction: '成熟低音', engineId: 'moss_design' });
  const candidate = project.candidates[0];
  const generation = await request(`/api/candidates/${candidate.candidateId}/generations`, 'POST', { expectedProjectRevision: project.revision, expectedCandidateRevision: candidate.revision, seed: 1 });
  for (let i = 0; i < 100; i += 1) {
    const value = await request('/api/generations/' + generation.generationId);
    if (value.status === 'completed') break;
    if (i === 99) throw new Error('fixture generation not completed');
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  await request(`/api/projects/${project.projectId}/selections`, 'POST', { generationId: generation.generationId });
  const voice = await request('/api/voices', 'POST', { projectId: project.projectId, generationId: generation.generationId });
  await page.goto(`${origin}/?voice=${voice.voiceId}`);
  await page.locator('#take-voice').waitFor();
  await page.waitForFunction(id => document.getElementById('take-voice').value === id, voice.voiceId);
  await page.locator('#take-engine').selectOption('index_base');
  await page.locator('#take-mode').selectOption('text');
  await page.locator('#take-text').fill('别打开那扇门，先把电源切断。');
  await page.locator('#take-description').fill('坚定、果断、时间紧迫');
  await page.locator('#take-seed').fill('123');
  await page.locator('#take-create').click();
  await page.locator('#take-list audio').waitFor();
  const first = (await request('/api/voice-takes?voiceId=' + voice.voiceId)).takes[0];
  await page.locator('#take-list').getByRole('button', { name: '复制实际强度为手动草稿' }).click();
  if (await page.locator('#take-mode').inputValue() !== 'manual') throw new Error('effective copy');
  await page.locator('#take-text').fill('马上关门。');
  await page.locator('#take-create').click();
  await page.waitForFunction(() => document.querySelectorAll('#take-list audio').length === 2);
  const all = (await request('/api/voice-takes?voiceId=' + voice.voiceId)).takes;
  const second = all[0];
  if (first.takeId === second.takeId || all[1].sourceSha256 !== first.sourceSha256) throw new Error('immutable take');
  for (const kind of ['source', 'h3']) {
    const bytes = await page.request.get(`${origin}/api/voice-takes/${first.takeId}/audio?kind=${kind}`);
    if (!bytes.ok() || (await bytes.body()).length < 100) throw new Error('audio download');
  }
  const audio = page.locator('#take-list audio').first();
  await audio.evaluate(element => element.play());
  await page.waitForFunction(() => [...document.querySelectorAll('#take-list audio')].some(element => element.currentTime > 0));
  await page.locator(`[data-take-id="${first.takeId}"]`).getByRole('button', { name: first.takeId, exact: true }).click();
  await page.reload();
  await page.waitForFunction(() => document.querySelectorAll('#take-list audio').length === 2);
  if (!page.url().includes(first.takeId) || await page.locator('#take-mode').inputValue() !== 'manual') throw new Error('selection/draft refresh');
  if (await page.locator(`#take-list [data-take-id="${first.takeId}"][aria-current="true"]`).count() !== 1) throw new Error('visible selected-take restoration');
  page.once('dialog', dialog => dialog.accept());
  await page.locator(`[data-take-id="${second.takeId}"]`).getByRole('button', { name: '删除此表演', exact: true }).click();
  await page.waitForFunction(() => document.querySelectorAll('#take-list audio').length === 1);
  const current = await request('/api/projects/' + project.projectId);
  await request('/api/projects/' + project.projectId, 'DELETE', { expectedRevision: current.revision, confirmName: current.name });
  await page.reload();
  await page.locator('#take-list audio').waitFor();
  if ((await request('/api/voice-takes/' + first.takeId)).sourceSha256 !== first.sourceSha256) throw new Error('project deletion changed take');
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.locator('#takes-heading').evaluate(element => element.scrollIntoView({ block: 'start' }));
  await page.screenshot({ path: 'output/playwright/voice-takes-1440x900.png' });
  console.log(JSON.stringify({ projectId: project.projectId, voiceId: voice.voiceId, takeId: first.takeId, sourceSha256: first.sourceSha256, h3Sha256: first.h3Sha256 }));
}
