const $ = id => document.getElementById(id);
const state = { project: null, shortlist: [], order: [], blind: false, notes: false,
  epoch: 0, polling: null, candidateDrafts: new Map(), candidateSignature: '', cloneSignature: '', pendingGenerationId: null };

async function api(path, method = 'GET', body) {
  const response = await fetch(path, { method, headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined });
  if (!response.ok) {
    let code = `HTTP ${response.status}`;
    try { code = (await response.json()).detail?.code || code; } catch (_) { /* Keep HTTP status. */ }
    throw new Error(code);
  }
  return response.status === 204 ? null : response.json();
}
function status(id, text) { $(id).textContent = text; }
function active(value) { return ['queued', 'running'].includes(value); }
function statusName(value) { return ({ queued: '排队中', running: '生成中', completed: '已完成', completed_stale: '输入已更改', failed: '失败', interrupted: '已中断' })[value] || value; }
function progressText(progress) {
  if (progress.status === 'queued') {
    if (progress.queueAhead === null) return '已接收请求，等待入队…';
    return progress.queueAhead ? `排队中 · 前方 ${progress.queueAhead} 个任务` : '排队中 · 下一个开始';
  }
  if (progress.status === 'running') {
    const phase = ({ starting: '任务启动中', loading_model: '模型准备中', synthesizing: '语音合成中', preparing_audio: '音频整理中', finalizing: '结果保存中' })[progress.phase] || '生成中';
    return `${phase} · 已运行 ${Math.floor(progress.elapsedSeconds || 0)} 秒（模型未提供完成百分比）`;
  }
  return `${statusName(progress.status)}${progress.errorCode ? ` · ${progress.errorCode}` : ''}`;
}
function node(tag, className, text) { const item = document.createElement(tag); if (className) item.className = className; if (text !== undefined) item.textContent = text; return item; }
function projectFormChanged() {
  const p = state.project;
  return !!p && (p.name !== $('project-name').value || p.brief !== $('project-brief').value || p.auditionText !== $('audition-text').value);
}
function changed() { return projectFormChanged() || state.candidateDrafts.size > 0; }
function clearPolling() { if (state.polling) clearInterval(state.polling); state.polling = null; }
function selectedCandidate() { return state.project?.candidates.find(c => c.currentGeneration?.generationId === state.project.selectedGenerationId); }

async function refreshProjects(epoch = state.epoch) {
  const { projects } = await api('/api/projects');
  if (epoch !== state.epoch) return;
  const list = $('project-list'); list.replaceChildren();
  for (const p of projects) {
    const button = node('button', p.projectId === state.project?.projectId ? 'active' : '', p.name);
    button.type = 'button'; button.addEventListener('click', () => navigate(p.projectId)); list.append(button);
  }
}
function showChooser() {
  state.project = null; state.shortlist = []; state.candidateDrafts.clear(); state.candidateSignature = ''; state.cloneSignature = ''; clearPolling();
  $('chooser').hidden = false; $('workspace').hidden = true;
  refreshProjects().catch(e => status('service-status', e.message));
}
function updateForm(p) {
  $('project-title').textContent = p.name; $('project-meta').textContent = `${p.projectId} · r${p.revision}`;
  $('project-name').value = p.name; $('project-brief').value = p.brief; $('audition-text').value = p.auditionText;
  status('draft-status', '');
}
async function loadProject(id, replaceForm = true, epoch = state.epoch) {
  const p = await api(`/api/projects/${id}`);
  if (epoch !== state.epoch) return;
  const switched = state.project?.projectId !== id;
  state.project = p; $('chooser').hidden = true; $('workspace').hidden = false;
  if (switched) { state.shortlist = []; state.order = p.candidates.map(c => c.candidateId); state.candidateDrafts.clear(); state.candidateSignature = ''; state.cloneSignature = ''; }
  if (replaceForm) updateForm(p);
  const signature = JSON.stringify([p.selectedGenerationId, p.candidates]);
  if (signature !== state.candidateSignature) { renderCandidates(); renderCompare(); state.candidateSignature = signature; }
  await refreshGenerationProgress(p, epoch);
  if (epoch !== state.epoch) return;
  const pending = p.candidates.find(c => c.latestGeneration?.generationId === state.pendingGenerationId);
  if (pending && active(pending.latestGeneration.status)) status('candidate-status', '');
  if (pending && !active(pending.latestGeneration.status)) {
    status('candidate-status', `${candidateLabel(pending)}：${statusName(pending.latestGeneration.status)}${pending.latestGeneration.errorCode ? ` · ${pending.latestGeneration.errorCode}` : ''}`);
    state.pendingGenerationId = null;
  }
  renderSelection(); await refreshProjects(epoch);
  if (epoch !== state.epoch) return;
  const cloneActive = await loadClones(epoch);
  if (epoch !== state.epoch) return;
  clearPolling();
  if (cloneActive || p.candidates.some(c => active(c.latestGeneration?.status))) {
    state.polling = setInterval(() => loadProject(id, false, epoch).catch(e => status('candidate-status', e.message)), 2500);
  }
}
async function refreshGenerationProgress(project, epoch) {
  for (const candidate of project.candidates) {
    const generation = candidate.latestGeneration;
    if (!active(generation?.status)) continue;
    let progress;
    try { progress = await api(`/api/generations/${generation.generationId}/progress`); }
    catch (_) {
      if (epoch !== state.epoch) return;
      const target = $(`progress-${generation.generationId}`);
      if (target) target.textContent = '进度暂不可用，稍后自动重试。';
      continue;
    }
    if (epoch !== state.epoch || state.project?.projectId !== project.projectId) return;
    const target = $(`progress-${generation.generationId}`);
    if (target) target.textContent = progressText(progress);
  }
}
async function navigate(id, fromHistory = false) {
  if (changed() && !window.confirm('当前项目有未保存的修改。放弃修改并切换吗？')) {
    if (fromHistory) history.replaceState({}, '', state.project ? `?project=${encodeURIComponent(state.project.projectId)}` : '/');
    return;
  }
  state.epoch += 1; clearPolling();
  if (!fromHistory) history.pushState({}, '', id ? `?project=${encodeURIComponent(id)}` : '/');
  if (!id) { showChooser(); return; }
  try { await loadProject(id, true, state.epoch); }
  catch (e) { status('service-status', `项目打开失败：${e.message}`); showChooser(); }
}
async function mutate(action, statusId = 'candidate-status') {
  try { await action(); } catch (e) { status(statusId, `操作失败：${e.message}`); }
}
function candidateLabel(c) {
  if (state.blind) return `盲听 ${String(state.order.indexOf(c.candidateId) + 1).padStart(2, '0')}`;
  return `候选 ${String(c.ordinal).padStart(2, '0')}`;
}
function shuffle() {
  state.order = state.project.candidates.map(c => c.candidateId);
  for (let i = state.order.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [state.order[i], state.order[j]] = [state.order[j], state.order[i]];
  }
}
function playSolo(audio) {
  document.querySelectorAll('audio').forEach(other => { if (other !== audio) other.pause(); });
  audio.currentTime = 0; audio.play().catch(() => status('candidate-status', '无法播放录音。'));
}
function makeCandidate(c) {
  const current = c.currentGeneration; const latest = c.latestGeneration;
  const card = node('article', 'candidate-card' + (state.project.selectedGenerationId === current?.generationId ? ' selected' : ''));
  const head = node('div', 'card-head'); head.append(node('h3', '', candidateLabel(c)), node('span', 'small-text', latest ? statusName(latest.status) : '未生成')); card.append(head);
  card.append(node('div', 'id', c.candidateId));
  const direction = node('textarea'); direction.rows = 2; direction.maxLength = 300; direction.value = state.candidateDrafts.get(c.candidateId) ?? c.direction;
  direction.setAttribute('aria-label', `${candidateLabel(c)}的声线方向`);
  direction.hidden = state.blind || !state.notes;
  direction.addEventListener('input', () => { if (direction.value === c.direction) state.candidateDrafts.delete(c.candidateId); else state.candidateDrafts.set(c.candidateId, direction.value); });
  card.append(direction);
  if (active(latest?.status)) {
    const progress = node('p', 'job-progress', latest.status === 'queued' ? '正在查询队列位置…' : '正在查询生成进度…');
    progress.id = `progress-${latest.generationId}`; progress.setAttribute('role', 'status'); card.append(progress);
  }
  if (current) {
    const audio = node('audio'); audio.controls = true; audio.preload = 'metadata'; audio.src = `/api/generations/${current.generationId}/audio`;
    audio.setAttribute('aria-label', `播放${candidateLabel(c)}`); audio.addEventListener('play', () => document.querySelectorAll('audio').forEach(other => { if (other !== audio) other.pause(); })); card.append(audio);
    card.append(node('div', 'small-text', `${current.sourceDurationSeconds?.toFixed(2) || '?'} 秒 · ${current.h3Eligible ? 'H3 参考就绪' : (current.errorCode || '仅可试听')}`));
  }
  if (latest?.status === 'failed' || latest?.status === 'interrupted' || latest?.status === 'completed_stale') card.append(node('p', 'error', `最近一次：${latest.errorCode || statusName(latest.status)}。${current ? '原录音仍可用。' : ''}`));
  const actions = node('div', 'card-actions');
  const save = node('button', '', '保存说明'); save.hidden = state.blind || !state.notes; save.onclick = () => mutate(async () => {
    state.project = await api(`/api/candidates/${c.candidateId}`, 'PUT', { expectedProjectRevision: state.project.revision, expectedCandidateRevision: c.revision, direction: direction.value.trim() });
    state.candidateDrafts.delete(c.candidateId); renderCandidates(); status('candidate-status', '候选说明已保存；已有录音未修改。');
  }); actions.append(save);
  const generate = node('button', '', current ? '重新生成此候选' : '生成此候选'); generate.disabled = active(latest?.status); generate.onclick = () => mutate(async () => {
    if (projectFormChanged() || direction.value !== c.direction) throw new Error('请先保存项目与此候选说明');
    if (current && !window.confirm('新录音成功后将替换此候选的旧未发布录音。继续吗？')) return;
    const result = await api(`/api/candidates/${c.candidateId}/generations`, 'POST', { expectedProjectRevision: state.project.revision, expectedCandidateRevision: c.revision });
    state.pendingGenerationId = result.generationId;
    status('candidate-status', `${candidateLabel(c)} 已排队：${result.generationId}`); await loadProject(state.project.projectId, false, state.epoch);
  }); actions.append(generate);
  if (current) {
    const compare = node('button', '', state.shortlist.includes(c.candidateId) ? '移出对比' : '加入对比'); compare.onclick = () => {
      const index = state.shortlist.indexOf(c.candidateId);
      if (index >= 0) state.shortlist.splice(index, 1); else if (state.shortlist.length < 2) state.shortlist.push(c.candidateId); else { status('candidate-status', '最多比较两条候选。'); return; }
      renderCandidates(); renderCompare();
    }; actions.append(compare);
    const select = node('button', '', state.project.selectedGenerationId === current.generationId ? '当前参考' : '选为参考'); select.disabled = state.project.selectedGenerationId === current.generationId; select.onclick = () => mutate(async () => {
      await api(`/api/projects/${state.project.projectId}/selections`, 'POST', { generationId: current.generationId });
      await loadProject(state.project.projectId, false, state.epoch);
    }); actions.append(select);
  }
  const remove = node('button', 'danger', '移除'); remove.onclick = () => mutate(async () => {
    if (!window.confirm(`移除此候选及其未发布录音？${c.candidateId}`)) return;
    state.project = await api(`/api/candidates/${c.candidateId}`, 'DELETE', { expectedProjectRevision: state.project.revision, expectedCandidateRevision: c.revision });
    state.candidateDrafts.delete(c.candidateId); state.shortlist = state.shortlist.filter(id => id !== c.candidateId); state.order = state.order.filter(id => id !== c.candidateId); renderCandidates(); renderCompare(); renderSelection();
  }); actions.append(remove); card.append(actions); return card;
}
function renderCandidates() {
  const grid = $('candidate-grid'); grid.replaceChildren(); const p = state.project; if (!p) return;
  const ids = p.candidates.map(c => c.candidateId); state.order = [...state.order.filter(id => ids.includes(id)), ...ids.filter(id => !state.order.includes(id))];
  const map = new Map(p.candidates.map(c => [c.candidateId, c])); for (const id of state.order) grid.append(makeCandidate(map.get(id)));
  $('blind-toggle').textContent = state.blind ? '结束盲听' : '打乱并盲听'; $('blind-toggle').setAttribute('aria-pressed', String(state.blind));
  $('notes-toggle').textContent = state.notes ? '隐藏设计说明' : '显示设计说明'; $('notes-toggle').disabled = state.blind;
}
function renderCompare() {
  const area = $('compare-slots'); area.replaceChildren(); status('compare-count', `${state.shortlist.length} / 2 已入围`);
  for (let i = 0; i < 2; i += 1) {
    const c = state.project?.candidates.find(item => item.candidateId === state.shortlist[i]); const slot = node('div', 'compare-slot');
    slot.append(node('strong', '', c ? candidateLabel(c) : '等待选择'));
    if (c?.currentGeneration) { const button = node('button', '', '从头播放'); button.onclick = () => { const audio = [...document.querySelectorAll('#candidate-grid audio')].find(a => a.src.includes(c.currentGeneration.generationId)); if (audio) playSolo(audio); }; slot.append(button); }
    area.append(slot);
  }
}
function renderSelection() {
  const c = selectedCandidate(); status('selected-label', c ? `${candidateLabel(c)} · ${c.currentGeneration.generationId}` : '尚未选择参考声线');
  $('clone-button').disabled = !c; $('publish-button').disabled = !c?.currentGeneration?.h3Eligible;
}
async function loadClones(epoch = state.epoch) {
  const p = state.project; const area = $('clone-list'); if (!p) return false;
  const { trials } = await api(`/api/clone-trials?projectId=${encodeURIComponent(p.projectId)}`);
  if (epoch !== state.epoch) return false;
  const signature = JSON.stringify(trials); if (signature === state.cloneSignature) return trials.some(t => active(t.status));
  state.cloneSignature = signature; area.replaceChildren();
  for (const t of trials) { const item = node('div', 'clone-item'); item.append(node('div', '', `${t.text} · ${statusName(t.status)}${t.errorCode ? ` · ${t.errorCode}` : ''}`)); if (t.status === 'completed') { const audio = node('audio'); audio.controls = true; audio.src = `/api/clone-trials/${t.trialId}/audio`; item.append(audio); } area.append(item); }
  return trials.some(t => active(t.status));
}
async function loadVoices() {
  const { voices } = await api('/api/voices'); const area = $('voice-list'); area.replaceChildren();
  for (const voice of voices) { const item = node('div', 'voice-item'); const id = node('div', 'voice-id', voice.voiceId); const copy = node('button', '', '复制 Voice ID'); copy.onclick = () => navigator.clipboard.writeText(voice.voiceId).then(() => status('publish-status', 'Voice ID 已复制。')).catch(() => status('publish-status', voice.voiceId)); item.append(id, copy, node('p', '', voice.transcript)); const audio = node('audio'); audio.controls = true; audio.src = `/api/voices/${voice.voiceId}/audio`; item.append(audio); area.append(item); }
}

$('new-project').onclick = $('chooser-create').onclick = () => mutate(async () => {
  const name = window.prompt('新项目名称（可以使用角色名）：'); if (!name?.trim()) return;
  const p = await api('/api/projects', 'POST', { name: name.trim() }); await navigate(p.projectId);
}, 'service-status');
$('save-project').onclick = () => mutate(async () => {
  const p = state.project; state.project = await api(`/api/projects/${p.projectId}`, 'PUT', { expectedRevision: p.revision, name: $('project-name').value.trim(), brief: $('project-brief').value, auditionText: $('audition-text').value });
  updateForm(state.project); await refreshProjects(); status('draft-status', '项目已保存。');
}, 'draft-status');
$('delete-project').onclick = () => mutate(async () => {
  const p = state.project; const confirmation = window.prompt(`输入准确项目名「${p.name}」以删除项目及未发布录音：`); if (confirmation === null) return;
  await api(`/api/projects/${p.projectId}`, 'DELETE', { expectedRevision: p.revision, confirmName: confirmation }); await navigate(null);
}, 'draft-status');
$('add-candidate').onclick = () => mutate(async () => {
  if (projectFormChanged()) throw new Error('请先保存项目'); const direction = $('new-direction').value.trim();
  state.project = await api(`/api/projects/${state.project.projectId}/candidates`, 'POST', { expectedProjectRevision: state.project.revision, direction });
  $('new-direction').value = ''; renderCandidates(); status('candidate-status', '候选已添加，其他录音未改变。');
});
$('blind-toggle').onclick = () => { if (!state.project) return; state.blind = !state.blind; if (state.blind) { state.notes = false; shuffle(); } else state.order = state.project.candidates.map(c => c.candidateId); renderCandidates(); renderCompare(); };
$('notes-toggle').onclick = () => { state.notes = !state.notes; renderCandidates(); };
$('clone-button').onclick = () => mutate(async () => {
  const c = selectedCandidate(); const result = await api('/api/clone-trials', 'POST', { projectId: state.project.projectId, generationId: c.currentGeneration.generationId, text: $('clone-text').value.trim() });
  status('clone-status', `复用试听已排队：${result.trialId}`); await loadProject(state.project.projectId, false, state.epoch);
}, 'clone-status');
$('publish-button').onclick = () => mutate(async () => {
  const c = selectedCandidate(); const result = await api('/api/voices', 'POST', { projectId: state.project.projectId, generationId: c.currentGeneration.generationId });
  status('publish-status', `已发布：${result.voiceId}`); await loadVoices();
}, 'publish-status');
for (const id of ['project-name', 'project-brief', 'audition-text']) $(id).addEventListener('input', () => status('draft-status', '未保存的项目修改。'));
window.addEventListener('beforeunload', e => { if (changed()) { e.preventDefault(); e.returnValue = ''; } });
window.addEventListener('popstate', () => navigate(new URLSearchParams(location.search).get('project'), true));
Promise.all([api('/health'), refreshProjects(), loadVoices()]).then(async ([health]) => {
  status('service-status', health.designModelAvailable && health.baseModelAvailable ? '服务在线 · 模型文件可用' : '服务在线 · 模型文件不完整');
  const id = new URLSearchParams(location.search).get('project'); if (id) await navigate(id, true); else showChooser();
}).catch(e => status('service-status', `连接失败：${e.message}`));
