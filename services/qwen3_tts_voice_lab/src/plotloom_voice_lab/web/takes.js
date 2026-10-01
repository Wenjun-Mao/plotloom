const $ = id => document.getElementById(id);
const labels = ['快乐', '愤怒', '悲伤', '害怕', '厌恶', '低落', '惊讶', '平静'];

export function setupTakes({ api, node, status, active, progressText }) {
  let epoch = 0, timer = null, signature = '', submitting = false, restoreScroll = true;
  const fields = ['take-engine', 'take-seed', 'take-text', 'take-mode', 'take-description'];
  const voice = () => $('take-voice').value;
  const key = id => `voice-lab.take-draft.${id}`;
  const address = takeId => {
    const url = new URL(location.href);
    if (voice()) url.searchParams.set('voice', voice()); else url.searchParams.delete('voice');
    if (takeId) url.searchParams.set('take', takeId); else url.searchParams.delete('take');
    history.replaceState({}, '', url);
  };
  labels.forEach((text, index) => {
    const field = node('div', 'field'), title = node('span', '', text), input = node('input');
    title.id = `take-emotion-label-${index}`; input.id = `take-emotion-${index}`;
    Object.assign(input, { type: 'number', min: '0', max: '1', step: '.05', value: '0' });
    input.setAttribute('aria-labelledby', title.id); field.append(title, input); $('take-vector').append(field);
  });
  const vector = () => labels.map((_, i) => $(`take-emotion-${i}`));
  function controls() {
    const index = $('take-engine').value === 'index_base';
    $('take-controls').hidden = !index;
    $('take-description-field').hidden = !index || $('take-mode').value !== 'text';
    $('take-vector').hidden = !index || $('take-mode').value !== 'manual';
    $('take-create').disabled = !voice() || submitting;
  }
  function saveDraft() {
    if (!voice()) return;
    try { sessionStorage.setItem(key(voice()), JSON.stringify({ values: fields.map(id => $(id).value), vector: vector().map(i => i.value) })); }
    catch (_) { status('take-status', '当前浏览器无法保留表演草稿。'); }
  }
  function restoreDraft() {
    fields.forEach(id => { $(id).value = ({ 'take-engine': 'qwen_base', 'take-mode': 'none' })[id] || ''; });
    vector().forEach(input => { input.value = '0'; });
    try {
      const draft = JSON.parse(sessionStorage.getItem(key(voice())) || 'null');
      if (draft) { fields.forEach((id, i) => { $(id).value = draft.values[i]; }); vector().forEach((input, i) => { input.value = draft.vector[i]; }); }
    } catch (_) { /* Keep empty, valid controls if a session draft is malformed. */ }
    controls();
  }
  function body() {
    const engineId = $('take-engine').value, mode = engineId === 'index_base' ? $('take-mode').value : 'none';
    const delivery = { mode }, seed = $('take-seed').value;
    if (seed && !$('take-seed').checkValidity()) throw new Error('种子需为 0–4294967295 的整数');
    if (mode === 'text') delivery.description = $('take-description').value.trim();
    if (mode === 'manual') delivery.vector = vector().map(input => {
      if (!input.value || !input.checkValidity()) throw new Error('情绪强度需为 0–1');
      return Number(input.value);
    });
    return { voiceId: voice(), text: $('take-text').value.trim(), engineId, delivery, ...(seed ? { seed: Number(seed) } : {}) };
  }
  function fill(take, effective) {
    $('take-engine').value = take.engineId; $('take-text').value = take.text; $('take-seed').value = String(take.seed);
    $('take-mode').value = effective ? 'manual' : take.delivery.mode;
    $('take-description').value = take.delivery.description || '';
    (effective || take.delivery.vector || labels.map(() => 0)).forEach((value, i) => { vector()[i].value = value; });
    controls(); saveDraft(); $('take-text').focus();
    status('take-status', '已复制为新表演草稿；点击生成后会得到新的 Take ID。');
  }
  function card(take) {
    const item = node('article', 'clone-item'); item.dataset.takeId = take.takeId;
    const select = node('button', '', take.takeId); select.onclick = () => { address(take.takeId); selectCard(take.takeId, true); };
    item.append(select, node('p', '', take.text), node('p', 'small-text', `${take.engineId} · seed ${take.seed} · ${take.delivery.mode}`));
    if (take.delivery.description) item.append(node('p', 'small-text', take.delivery.description));
    const progress = node('p', 'job-progress', progressText(take)); progress.id = `take-progress-${take.takeId}`; item.append(progress);
    const effective = take.executionDetails.effectiveVector;
    if (effective) {
      item.append(node('p', 'small-text', `实际情绪强度：${labels.map((label, i) => `${label} ${effective[i]}`).join(' · ')}`));
      const copy = node('button', '', '复制实际强度为手动草稿'); copy.onclick = () => fill(take, effective); item.append(copy);
    }
    if (take.status === 'completed') {
      const audio = node('audio'); audio.controls = true; audio.preload = 'metadata'; audio.src = `/api/voice-takes/${take.takeId}/audio`;
      audio.setAttribute('aria-label', `试听 ${take.takeId}`);
      audio.onplay = () => document.querySelectorAll('audio').forEach(other => { if (other !== audio) other.pause(); }); item.append(audio);
      item.append(node('p', 'small-text', `${take.durationSeconds.toFixed(2)} 秒 · ${take.sampleRate} Hz · ${take.h3Eligible ? 'H3 参考就绪' : `仅可试听：${take.h3IssueCode}`}`));
      for (const warning of take.audioDetails.warnings || []) item.append(node('p', 'error', warning));
      for (const kind of take.h3Eligible ? ['source', 'h3'] : ['source']) {
        const link = node('a', '', kind === 'source' ? '下载原生 WAV' : '下载 H3 WAV'); link.href = `/api/voice-takes/${take.takeId}/audio?kind=${kind}`; link.download = `${take.takeId}-${kind}.wav`; item.append(link, document.createTextNode(' '));
      }
      const copy = node('button', '', '复制 Take ID'); copy.onclick = async () => {
        try { await navigator.clipboard.writeText(take.takeId); status('take-status', 'Take ID 已复制。'); }
        catch (_) { status('take-status', `请手动复制 Take ID：${take.takeId}`); }
      }; item.append(copy);
    }
    const repeat = node('button', '', '复制为新表演'); repeat.onclick = () => fill(take); item.append(repeat);
    if (!active(take.status) && take.status !== 'deleted') {
      const remove = node('button', 'danger', '删除此表演'); remove.onclick = async () => {
        if (!window.confirm(`删除此 Take 的托管音频？声线和其他表演不会改变。\n${take.takeId}`)) return;
        const token = epoch;
        try {
          await api(`/api/voice-takes/${take.takeId}`, 'DELETE', { confirmTakeId: take.takeId });
          if (token === epoch) {
            if (new URL(location.href).searchParams.get('take') === take.takeId) address();
            signature = ''; await refresh(token);
          }
        } catch (error) { if (token === epoch) status('take-status', error.message); }
      }; item.append(remove);
    }
    return item;
  }
  function selectCard(id, scroll = false) {
    for (const item of $('take-list').querySelectorAll('[data-take-id]')) {
      const selected = item.dataset.takeId === id;
      item.classList.toggle('selected', selected); item.setAttribute('aria-current', String(selected));
      if (selected && scroll) item.scrollIntoView({ block: 'center' });
    }
  }
  async function refresh(token = epoch) {
    if (timer) clearTimeout(timer); timer = null;
    if (!voice()) { $('take-list').replaceChildren(node('p', 'muted', '先发布或选择一条声线。')); return; }
    try {
      const { takes } = await api(`/api/voice-takes?voiceId=${encodeURIComponent(voice())}`);
      if (token !== epoch) return;
      const next = JSON.stringify(takes);
      if (signature !== next) {
        signature = next; $('take-list').replaceChildren(...takes.map(card));
        if (!takes.length) $('take-list').append(node('p', 'muted', '此声线还没有台词表演。'));
      }
      const selected = new URL(location.href).searchParams.get('take');
      if (selected && !takes.some(t => t.takeId === selected && t.status !== 'deleted')) {
        status('take-status', '所选 Take 不存在、已删除或不属于此声线。'); address();
      } else selectCard(selected, restoreScroll);
      restoreScroll = false;
      let held = false;
      for (const take of takes.filter(t => active(t.status) || ['failed', 'interrupted'].includes(t.status))) {
        const details = await api(`/api/voice-takes/${take.takeId}`);
        if (token !== epoch) return;
        held ||= details.phase === 'active';
        const target = $(`take-progress-${take.takeId}`); if (target) target.textContent = progressText(details);
      }
      if (held || takes.some(t => active(t.status))) timer = setTimeout(() => refresh(token), 2000);
    } catch (error) {
      if (token === epoch) { status('take-status', `进度暂不可用：${error.message}`); timer = setTimeout(() => refresh(token), 3000); }
    }
  }
  function choose() {
    epoch += 1; signature = ''; restoreScroll = false; address(); restoreDraft(); status('take-status', ''); refresh(epoch);
  }
  $('take-voice').onchange = choose;
  for (const input of [...fields.map($), ...vector()]) input.addEventListener('input', () => { controls(); saveDraft(); });
  $('take-create').onclick = async () => {
    const token = epoch; submitting = true; controls();
    try {
      const take = await api('/api/voice-takes', 'POST', body());
      if (token === epoch) { address(take.takeId); status('take-status', `已接收：${take.takeId}`); await refresh(token); }
    } catch (error) { if (token === epoch) status('take-status', `未确认入队：${error.message}。不要盲目重新提交，先刷新列表。`); }
    finally { submitting = false; controls(); }
  };
  return {
    async voices(values) {
      const previous = voice(), requested = new URL(location.href).searchParams.get('voice');
      $('take-voice').replaceChildren(node('option', '', '选择已发布声线'));
      for (const value of values) { const option = node('option', '', value.voiceId); option.value = value.voiceId; $('take-voice').append(option); }
      $('take-voice').firstChild.value = '';
      $('take-voice').value = values.some(v => v.voiceId === previous) ? previous : values.some(v => v.voiceId === requested) ? requested : '';
      if (voice() !== previous) { epoch += 1; signature = ''; restoreScroll = true; restoreDraft(); }
      controls(); await refresh(epoch);
    },
  };
}
