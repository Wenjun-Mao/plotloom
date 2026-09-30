const $ = id => document.getElementById(id);
const labels = ['快乐', '愤怒', '悲伤', '害怕', '厌恶', '低落', '惊讶', '平静'];

export function setupReuse({ api, state, selectedCandidate, mutate, status, loadProject, acceptAuxiliary }) {
  const vector = $('emotion-vector');
  labels.forEach((label, index) => {
    const field = document.createElement('div'); field.className = 'field';
    const title = document.createElement('span'); title.id = `emotion-label-${index}`; title.textContent = label;
    const input = document.createElement('input'); input.id = `emotion-${index}`;
    input.type = 'number'; input.min = '0'; input.max = '1'; input.step = '.05'; input.value = '0';
    input.setAttribute('aria-labelledby', title.id); field.append(title, input); vector.append(field);
  });
  function controls() {
    const index = $('reuse-engine').value === 'index_base';
    $('delivery-controls').hidden = !index;
    $('delivery-description-field').hidden = !index || $('delivery-mode').value !== 'text';
    vector.hidden = !index || $('delivery-mode').value !== 'manual';
  }
  $('reuse-engine').onchange = $('delivery-mode').onchange = controls;
  controls();
  $('clone-button').onclick = () => mutate(async () => {
    const c = selectedCandidate(); const engineId = $('reuse-engine').value;
    const mode = engineId === 'index_base' ? $('delivery-mode').value : 'none';
    const delivery = { mode };
    if (mode === 'text') delivery.description = $('delivery-description').value.trim();
    if (mode === 'manual') delivery.vector = labels.map((_, i) => {
      const input = $(`emotion-${i}`);
      if (!input.value || !input.checkValidity()) throw new Error('情绪强度需为 0–1');
      return Number(input.value);
    });
    const seed = $('reuse-seed').value;
    if (seed && !$('reuse-seed').checkValidity()) throw new Error('种子需为 0–4294967295 的整数');
    const result = await api('/api/clone-trials', 'POST', {
      projectId: state.project.projectId, generationId: c.currentGeneration.generationId,
      text: $('clone-text').value.trim(), engineId, delivery, ...(seed ? { seed: Number(seed) } : {}),
    });
    status('clone-status', `复用试听已排队：${result.trialId}`);
    acceptAuxiliary('reuse');
    await loadProject(state.project.projectId, false, state.epoch);
  }, 'clone-status');
}

export async function renderTrials({ api, state, epoch, node, active, statusName, progressText }) {
  const project = state.project;
  const { trials } = await api(`/api/clone-trials?projectId=${encodeURIComponent(project.projectId)}`);
  if (epoch !== state.epoch) return false;
  const signature = JSON.stringify(trials);
  if (signature !== state.cloneSignature) {
    state.cloneSignature = signature; const area = $('clone-list'); area.replaceChildren();
    for (const trial of trials) {
      const item = node('div', 'clone-item');
      item.append(node('strong', '', `${trial.engineId === 'index_base' ? 'IndexTTS2' : 'Qwen Base'} · ${statusName(trial.status)}`));
      item.append(node('p', '', trial.text), node('p', 'small-text', `${trial.trialId} · seed ${trial.seed} · ${trial.delivery.mode}`));
      if (trial.delivery.description) item.append(node('p', 'small-text', `表演方向：${trial.delivery.description}`));
      if (trial.errorCode) item.append(node('p', 'error', trial.errorCode));
      for (const warning of trial.audioDetails?.warnings || []) item.append(node('p', 'error', warning));
      const effective = trial.executionDetails.effectiveVector;
      if (effective) {
        item.append(node('p', 'small-text', `实际情绪强度：${labels.map((label, i) => `${label} ${effective[i]}`).join(' · ')}`));
        if (trial.executionDetails.classifierSeconds !== undefined) item.append(node('p', 'small-text', `情绪分类 ${trial.executionDetails.classifierSeconds.toFixed(2)} 秒`));
        const copy = node('button', '', '复制实际强度到手动控制'); copy.onclick = () => {
          $('reuse-engine').value = 'index_base'; $('delivery-mode').value = 'manual';
          effective.forEach((value, i) => { $(`emotion-${i}`).value = value; });
          $('delivery-mode').onchange(); $('emotion-vector').scrollIntoView({ block: 'center' });
        }; item.append(copy);
      }
      if (active(trial.status)) { const progress = node('p', 'job-progress', '正在查询队列…'); progress.id = `clone-progress-${trial.trialId}`; progress.setAttribute('role', 'status'); item.append(progress); }
      if (trial.status === 'completed') { const audio = node('audio'); audio.controls = true; audio.src = `/api/clone-trials/${trial.trialId}/audio`; audio.onplay = () => document.querySelectorAll('audio').forEach(other => { if (other !== audio) other.pause(); }); item.append(audio); }
      area.append(item);
    }
  }
  for (const trial of trials.filter(t => active(t.status))) {
    try {
      const progress = await api(`/api/clone-trials/${trial.trialId}/progress`);
      if (epoch !== state.epoch) return false;
      const target = $(`clone-progress-${trial.trialId}`); if (target) target.textContent = progressText(progress);
    } catch (_) { /* The next bounded polling pass retries progress. */ }
  }
  return trials.some(t => active(t.status));
}
