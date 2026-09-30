async (page) => {
  // Run via playwright-cli against fixtures/browser_server.py, never live Spark.
  if (new URL(page.url()).port !== '8898') throw new Error('fixture origin required');
  const origin = 'http://127.0.0.1:8898';
  const create = async name => {
    const response = await page.request.post(`${origin}/api/projects`, {data: {name}});
    const project = await response.json();
    return project.projectId;
  };
  const first = await create('浏览器验收甲'); await create('浏览器验收乙');
  await page.goto(`http://127.0.0.1:8898/?project=${first}`);
  await page.getByRole('heading', {name:'浏览器验收甲', exact:true}).waitFor();
  await page.locator('#project-brief').fill('成熟低音，克制而坚韧。');
  await page.locator('#audition-text').fill('雨还没有停。主灯，或者码头，我们只能先保住一边。');
  await page.getByRole('button', {name:'保存项目', exact:true}).click();
  await page.locator('#creation-count').selectOption('1');
  await page.locator('#paired-directions textarea').fill('四十岁左右的中国女性，成熟低音，自然口语。');
  await page.getByRole('button', {name:'生成候选', exact:true}).click();
  await page.locator('#candidate-grid audio').nth(1).waitFor();
  if (await page.locator('.candidate-card').count() !== 2) throw new Error('paired count');
  await page.locator('.candidate-card').nth(1).getByRole('button', {name:'选为参考', exact:true}).click();
  await page.locator('#reuse-engine').selectOption('index_base');
  await page.locator('#delivery-mode').selectOption('text');
  await page.locator('#clone-text').fill('别打开那扇门，先把电源切断。');
  await page.locator('#delivery-description').fill('坚定、果断、时间紧迫');
  await page.getByRole('button', {name:'生成复用试听', exact:true}).click();
  await page.locator('.clone-item audio').waitFor();
  await page.locator('.clone-item').getByText('audio.peak_exceeds_full_scale', {exact:true}).waitFor();
  await page.getByRole('button', {name:'复制实际强度到手动控制', exact:true}).click();
  if (await page.locator('#delivery-mode').inputValue() !== 'manual') throw new Error('manual copy');
  await page.getByRole('button', {name:'发布所选声线', exact:true}).click();
  await page.locator('.voice-id').waitFor();
  await page.getByRole('button', {name:'打乱并盲听', exact:true}).click();
  if (await page.locator('.candidate-card select:visible').count()) throw new Error('blind engine leak');
  await page.getByRole('button', {name:'结束盲听', exact:true}).click();
  // A denied discard must preserve every auxiliary draft and create no project.
  await page.locator('#new-direction').fill('甲项目的未提交方向');
  await page.locator('#new-engine').selectOption('moss_design');
  const count = (await (await page.request.get(`${origin}/api/projects`)).json()).projects.length;
  page.once('dialog', dialog => dialog.dismiss());
  await page.getByRole('button', {name:'＋ 新建', exact:true}).click();
  const after = (await (await page.request.get(`${origin}/api/projects`)).json()).projects.length;
  if (after !== count || await page.locator('#new-direction').inputValue() !== '甲项目的未提交方向') throw new Error('cancel mutated draft/project');
  page.once('dialog', dialog => dialog.accept());
  await page.getByRole('button', {name:'浏览器验收乙', exact:true}).click();
  await page.getByRole('heading', {name:'浏览器验收乙', exact:true}).waitFor();
  if (await page.locator('#new-direction').inputValue() || await page.locator('#delivery-description').inputValue()) throw new Error('cross-project draft leak');
  if (await page.locator('#reuse-engine').inputValue() !== 'qwen_base' || await page.locator('#emotion-1').inputValue() !== '0') throw new Error('reuse defaults');
  await page.getByRole('button', {name:'浏览器验收甲', exact:true}).click();
  await page.locator('.clone-item audio').waitFor(); await page.reload();
  await page.locator('.clone-item audio').waitFor(); await page.locator('.voice-id').waitFor();
  await page.setViewportSize({width:1440,height:900});
  await page.locator('#candidate-grid').scrollIntoViewIfNeeded();
  await page.screenshot({path:'output/playwright/voice-lab-multi-engine-candidates.png'});
  await page.getByRole('button', {name:'复制实际强度到手动控制', exact:true}).click();
  await page.locator('#reuse-engine').scrollIntoViewIfNeeded();
  await page.screenshot({path:'output/playwright/voice-lab-multi-engine-reuse.png'});
  console.log('paired/reuse/actual-vector/publication/blind/navigation/refresh browser journey passed');
}
