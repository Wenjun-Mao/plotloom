const byId = id => document.getElementById(id);
const state = { round: null, selection: null, shortlist: [], blind: false, notes: false, order: [] };
let roundTimer = null;
let cloneTimer = null;
let roundEpoch = 0;

async function request(path, options = {}) {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    let code = `HTTP ${response.status}`;
    try { code = (await response.json()).detail?.code || code; } catch (_) { /* HTTP status is enough. */ }
    throw new Error(code);
  }
  return response.json();
}

function setStatus(id, message) { byId(id).textContent = message; }
function isActive(status) { return status === 'queued' || status === 'running'; }
function statusText(status) {
  return ({ queued: '排队中', running: '生成中', completed: '已完成', partial: '部分完成', failed: '失败', interrupted: '已中断' })[status] || status;
}

function updateDirectionFields() {
  const count = Number(byId('candidate-count').value);
  const area = byId('direction-fields');
  const saved = [...area.querySelectorAll('textarea')].map(field => field.value);
  area.replaceChildren();
  for (let index = 0; index < count; index += 1) {
    const label = document.createElement('label');
    label.textContent = `候选 ${String(index + 1).padStart(2, '0')} · 设计说明`;
    const field = document.createElement('textarea');
    field.rows = 2;
    field.maxLength = 300;
    field.value = saved[index] ?? byId('voice-brief').value;
    field.addEventListener('input', () => setStatus('draft-status', '设计草稿已修改；已保存录音不会改变。'));
    label.append(field);
    area.append(label);
  }
  byId('generate-button').textContent = `生成 ${count} 个候选`;
}

function candidateLabel(candidate) {
  if (state.blind) return `盲听片段 ${String(state.order.indexOf(candidate.candidateId) + 1).padStart(2, '0')}`;
  return `候选 ${String(candidate.ordinal).padStart(2, '0')}`;
}

function shuffleOrder() {
  const values = [...state.round.candidates.map(item => item.candidateId)];
  for (let i = values.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [values[i], values[j]] = [values[j], values[i]];
  }
  if (values.length > 1 && values.every((id, i) => id === state.order[i])) values.push(values.shift());
  state.order = values;
}

function renderCompare() {
  byId('compare-count').textContent = `${state.shortlist.length} / 2 已入围`;
  for (let slot = 0; slot < 2; slot += 1) {
    const candidate = state.round?.candidates.find(item => item.candidateId === state.shortlist[slot]);
    byId(`slot-label-${slot}`).textContent = candidate ? candidateLabel(candidate) : '等待选择';
    document.querySelector(`.compare-play[data-slot="${slot}"]`).disabled = !candidate;
  }
}

function renderSelection() {
  const current = state.selection?.candidateId;
  const candidate = state.round?.candidates.find(item => item.candidateId === current);
  byId('selected-label').textContent = current
    ? `${candidate ? candidateLabel(candidate) : '已选参考'} · ${current.slice(0, 13)}…`
    : '尚未选择参考声线';
  byId('clone-button').disabled = !current;
}

function makeCandidateCard(candidate) {
  const card = document.createElement('article');
  card.className = 'candidate-card';
  if (state.shortlist.includes(candidate.candidateId)) card.classList.add('is-shortlisted');
  const header = document.createElement('div');
  header.className = 'candidate-header';
  const title = document.createElement('h3');
  title.textContent = candidateLabel(candidate);
  const duration = document.createElement('span');
  duration.textContent = candidate.sourceDurationSeconds ? `${candidate.sourceDurationSeconds.toFixed(2)} 秒` : statusText(candidate.status);
  header.append(title, duration);
  card.append(header);

  if (state.notes && !state.blind) {
    const note = document.createElement('p');
    note.className = 'candidate-note';
    note.textContent = candidate.direction;
    card.append(note);
  }
  if (candidate.status === 'completed') {
    const audio = document.createElement('audio');
    audio.controls = true;
    audio.preload = 'metadata';
    audio.src = `/api/candidates/${candidate.candidateId}/audio`;
    audio.setAttribute('aria-label', `播放${candidateLabel(candidate)}`);
    audio.addEventListener('play', () => {
      document.querySelectorAll('#candidate-grid audio, #clone-list audio').forEach(other => {
        if (other !== audio) other.pause();
      });
      card.classList.add('is-playing');
    });
    audio.addEventListener('pause', () => card.classList.remove('is-playing'));
    card.append(audio);
    const actions = document.createElement('div');
    actions.className = 'candidate-actions';
    const compare = document.createElement('button');
    compare.className = 'shortlist-button';
    compare.type = 'button';
    compare.textContent = state.shortlist.includes(candidate.candidateId) ? '移出对比' : '加入对比';
    compare.addEventListener('click', () => {
      const current = state.shortlist.indexOf(candidate.candidateId);
      if (current >= 0) state.shortlist.splice(current, 1);
      else if (state.shortlist.length < 2) state.shortlist.push(candidate.candidateId);
      else { setStatus('compare-status', '最多同时比较两条；请先移出其中一条。'); return; }
      renderCandidates();
      renderCompare();
    });
    const select = document.createElement('button');
    select.className = 'shortlist-button';
    select.type = 'button';
    select.textContent = state.selection?.candidateId === candidate.candidateId ? '当前复用参考' : '选为复用参考';
    select.disabled = state.selection?.candidateId === candidate.candidateId;
    select.addEventListener('click', async () => {
      try {
        state.selection = await request('/api/selections', {
          method: 'POST', body: JSON.stringify({ candidateId: candidate.candidateId }),
        });
        renderCandidates();
        renderSelection();
        await loadClones();
      } catch (error) { setStatus('compare-status', `选择失败：${error.message}`); }
    });
    const eligibility = document.createElement('span');
    eligibility.className = 'candidate-state';
    eligibility.textContent = candidate.h3Eligible ? 'H3 参考已就绪'
      : candidate.errorCode === 'h3.duration_out_of_range' ? 'H3 参考需 1–10 秒' : 'H3 参考准备失败';
    actions.append(compare, select, eligibility);
    card.append(actions);
  } else if (candidate.errorCode) {
    const error = document.createElement('p');
    error.className = 'candidate-note';
    error.textContent = `生成未完成：${candidate.errorCode}`;
    card.append(error);
  }
  return card;
}

function renderCandidates() {
  const grid = byId('candidate-grid');
  grid.replaceChildren();
  if (!state.round) return;
  const byCandidate = new Map(state.round.candidates.map(item => [item.candidateId, item]));
  state.order.forEach(id => grid.append(makeCandidateCard(byCandidate.get(id))));
  byId('blind-toggle').textContent = state.blind ? '结束盲听' : '打乱并盲听';
  byId('blind-toggle').setAttribute('aria-pressed', String(state.blind));
  byId('notes-toggle').textContent = state.notes ? '隐藏设计说明' : '显示设计说明';
  byId('notes-toggle').disabled = state.blind;
  renderCompare();
  renderSelection();
}

async function loadRound(roundId, epoch = roundEpoch) {
  if (!roundId) return;
  const result = await request(`/api/rounds/${roundId}`);
  if (epoch !== roundEpoch) return;
  const changed = state.round?.roundId !== roundId;
  state.round = result;
  if (changed) {
    state.shortlist = [];
    state.order = result.candidates.map(item => item.candidateId);
    history.replaceState(null, '', `?round=${encodeURIComponent(roundId)}`);
  }
  setStatus('round-status', `${statusText(result.status)} · ${result.candidates.filter(item => item.status === 'completed').length}/${result.candidates.length} 条完成${result.errorCode ? ` · ${result.errorCode}` : ''}`);
  const selectedOption = [...byId('round-selector').options].find(option => option.value === roundId);
  if (selectedOption) selectedOption.textContent = `${result.createdAt.slice(0, 16).replace('T', ' ')} · ${result.candidates.length} 条 · ${statusText(result.status)}`;
  if (!isActive(result.status) && byId('draft-status').textContent === '新轮次已排队；旧录音保持不变。') {
    setStatus('draft-status', result.status === 'completed' ? '新轮次已完成；已保存录音不会因修改草稿而改变。' : `新轮次已结束：${statusText(result.status)}`);
  }
  if (changed || ![...document.querySelectorAll('#candidate-grid audio')].some(audio => !audio.paused)) renderCandidates();
  if (!isActive(result.status) && roundTimer) { clearInterval(roundTimer); roundTimer = null; }
  if (isActive(result.status) && !roundTimer) {
    roundTimer = setInterval(() => loadRound(roundId, epoch).catch(error => setStatus('round-status', error.message)), 2000);
  }
}

async function loadRoundList(preferredId) {
  const { rounds } = await request('/api/rounds');
  const select = byId('round-selector');
  select.replaceChildren();
  for (const round of rounds) {
    const option = document.createElement('option');
    option.value = round.roundId;
    option.textContent = `${round.createdAt.slice(0, 16).replace('T', ' ')} · ${round.candidateCount} 条 · ${statusText(round.status)}`;
    select.append(option);
  }
  const target = rounds.find(item => item.roundId === preferredId)?.roundId || rounds[0]?.roundId;
  if (target) {
    roundEpoch += 1;
    if (roundTimer) { clearInterval(roundTimer); roundTimer = null; }
    select.value = target;
    await loadRound(target);
  }
}

async function loadClones() {
  const candidateId = state.selection?.candidateId;
  const list = byId('clone-list');
  list.replaceChildren();
  if (!candidateId) return;
  const { trials } = await request(`/api/clone-trials?candidateId=${encodeURIComponent(candidateId)}`);
  for (const trial of trials) {
    const item = document.createElement('article');
    item.className = 'clone-item';
    const line = document.createElement('p');
    line.textContent = `${trial.text} · ${statusText(trial.status)}${trial.errorCode ? ` · ${trial.errorCode}` : ''}`;
    item.append(line);
    if (trial.status === 'completed') {
      const audio = document.createElement('audio');
      audio.controls = true;
      audio.src = `/api/clone-trials/${trial.trialId}/audio`;
      item.append(audio);
    }
    list.append(item);
  }
}

byId('candidate-count').addEventListener('change', updateDirectionFields);
byId('voice-brief').addEventListener('input', () => setStatus('draft-status', '共同方向已修改；请检查每条候选的独立说明。'));
byId('generate-button').addEventListener('click', async () => {
  const button = byId('generate-button');
  button.disabled = true;
  try {
    const directions = [...byId('direction-fields').querySelectorAll('textarea')].map(field => field.value.trim());
    const result = await request('/api/rounds', {
      method: 'POST', body: JSON.stringify({ auditionText: byId('audition-line').value.trim(), directions }),
    });
    setStatus('draft-status', '新轮次已排队；旧录音保持不变。');
    await loadRoundList(result.roundId);
  } catch (error) { setStatus('draft-status', `创建失败：${error.message}`); }
  finally { button.disabled = false; }
});
byId('round-selector').addEventListener('change', event => {
  roundEpoch += 1;
  if (roundTimer) { clearInterval(roundTimer); roundTimer = null; }
  loadRound(event.target.value).catch(error => setStatus('round-status', error.message));
});
byId('blind-toggle').addEventListener('click', () => {
  if (!state.round) return;
  state.blind = !state.blind;
  if (state.blind) { state.notes = false; shuffleOrder(); }
  else state.order = state.round.candidates.map(item => item.candidateId);
  renderCandidates();
});
byId('notes-toggle').addEventListener('click', () => { state.notes = !state.notes; renderCandidates(); });
document.querySelectorAll('.compare-play').forEach(button => button.addEventListener('click', () => {
  const id = state.shortlist[Number(button.dataset.slot)];
  const audio = [...byId('candidate-grid').querySelectorAll('audio')]
    .find(item => item.src.includes(id));
  if (audio) { audio.currentTime = 0; audio.play().catch(() => setStatus('compare-status', '无法播放此录音。')); }
}));
byId('clone-button').addEventListener('click', async () => {
  const button = byId('clone-button');
  button.disabled = true;
  try {
    const result = await request('/api/clone-trials', {
      method: 'POST', body: JSON.stringify({ candidateId: state.selection.candidateId, text: byId('clone-text').value.trim() }),
    });
    setStatus('clone-status', `复用试听已排队：${result.trialId}`);
    await loadClones();
    if (cloneTimer) clearInterval(cloneTimer);
    cloneTimer = setInterval(async () => {
      try {
        const trial = await request(`/api/clone-trials/${result.trialId}`);
        setStatus('clone-status', `${statusText(trial.status)}${trial.errorCode ? ` · ${trial.errorCode}` : ''}`);
        await loadClones();
        if (!isActive(trial.status)) { clearInterval(cloneTimer); cloneTimer = null; }
      } catch (error) { setStatus('clone-status', error.message); }
    }, 2000);
  } catch (error) { setStatus('clone-status', `创建失败：${error.message}`); }
  finally { button.disabled = !state.selection; }
});

updateDirectionFields();
Promise.all([request('/health'), request('/api/selections')]).then(async ([health, selections]) => {
  byId('service-status').textContent = health.designModelAvailable && health.baseModelAvailable ? '服务在线 · 模型文件可用' : '服务在线 · 模型文件不完整';
  state.selection = selections.current;
  await loadRoundList(new URLSearchParams(location.search).get('round'));
  await loadClones();
  renderSelection();
}).catch(error => { byId('service-status').textContent = `连接失败：${error.message}`; });
