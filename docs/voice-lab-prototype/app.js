const grid = document.getElementById('candidate-grid');
const cards = [...grid.querySelectorAll('[data-candidate]')];
const originalOrder = [...cards];
const blindButton = document.getElementById('blind-toggle');
const notesButton = document.getElementById('notes-toggle');
const candidateCount = document.getElementById('candidate-count');
const generateButton = document.getElementById('generate-button');
const compareStatus = document.getElementById('compare-status');
const shortlist = [];
let blind = false;
let notesVisible = false;

function nameFor(card) {
  if (!card) return '';
  if (!blind) return `候选 ${card.dataset.candidate.toUpperCase()}`;
  return `盲听片段 ${String([...grid.children].indexOf(card) + 1).padStart(2, '0')}`;
}

function cardFor(id) {
  return cards.find(card => card.dataset.candidate === id);
}

function updateView() {
  [...grid.children].forEach(card => {
    const id = card.dataset.candidate;
    const selected = shortlist.includes(id);
    card.querySelector('.candidate-label').textContent = nameFor(card);
    card.querySelector('.candidate-note').hidden = blind || !notesVisible;
    card.querySelector('audio').setAttribute('aria-label', `播放${nameFor(card)}`);
    card.classList.toggle('is-shortlisted', selected);
    const button = card.querySelector('.shortlist-button');
    button.setAttribute('aria-pressed', String(selected));
    button.textContent = selected ? '移出对比' : '加入对比';
    card.querySelector('.candidate-state').textContent = selected ? '已入围' : '未入围';
  });

  blindButton.setAttribute('aria-pressed', String(blind));
  blindButton.textContent = blind ? '结束盲听' : '打乱并盲听';
  notesButton.setAttribute('aria-pressed', String(notesVisible));
  notesButton.textContent = notesVisible ? '隐藏设计说明' : '显示设计说明';
  notesButton.disabled = blind;
  document.getElementById('compare-count').textContent = `${shortlist.length} / 2 已入围`;

  for (let slot = 0; slot < 2; slot += 1) {
    const id = shortlist[slot];
    const label = document.getElementById(`slot-label-${slot}`);
    label.textContent = id ? nameFor(cardFor(id)) : '等待选择';
    const playButton = document.querySelector(`.compare-play[data-slot="${slot}"]`);
    playButton.disabled = !id;
  }
}

function shuffleCards() {
  const shuffled = [...originalOrder];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const choice = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[choice]] = [shuffled[choice], shuffled[index]];
  }
  if (shuffled.every((card, index) => card === originalOrder[index])) {
    shuffled.push(shuffled.shift());
  }
  shuffled.forEach(card => grid.append(card));
}

blindButton.addEventListener('click', () => {
  blind = !blind;
  if (blind) {
    notesVisible = false;
    shuffleCards();
    compareStatus.textContent = '顺序已打乱；名称和设计说明已隐藏。当前播放和入围选择仍保持。';
  } else {
    originalOrder.forEach(card => grid.append(card));
    compareStatus.textContent = '已恢复候选身份，入围对比的两条样本保持不变。';
  }
  updateView();
});

notesButton.addEventListener('click', () => {
  notesVisible = !notesVisible;
  updateView();
});

cards.forEach(card => {
  const id = card.dataset.candidate;
  const audio = card.querySelector('audio');
  audio.addEventListener('play', () => {
    cards.forEach(other => {
      if (other !== card) other.querySelector('audio').pause();
      other.classList.toggle('is-playing', other === card);
    });
  });
  audio.addEventListener('pause', () => card.classList.remove('is-playing'));
  audio.addEventListener('ended', () => card.classList.remove('is-playing'));
  card.querySelector('.shortlist-button').addEventListener('click', () => {
    const index = shortlist.indexOf(id);
    if (index >= 0) {
      shortlist.splice(index, 1);
      compareStatus.textContent = `${nameFor(card)} 已移出对比。`;
    } else if (shortlist.length === 2) {
      compareStatus.textContent = '最多同时比较两条；请先移出其中一条。';
    } else {
      shortlist.push(id);
      compareStatus.textContent = `${nameFor(card)} 已加入对比。`;
    }
    updateView();
  });
});

document.querySelectorAll('.compare-play').forEach(button => {
  button.addEventListener('click', () => {
    const id = shortlist[Number(button.dataset.slot)];
    if (!id) return;
    const audio = cardFor(id).querySelector('audio');
    audio.currentTime = 0;
    audio.play().catch(() => {
      compareStatus.textContent = '浏览器未能播放这条样本；请检查本地音频文件。';
    });
  });
});

function markDraftChanged() {
  document.getElementById('draft-status').textContent = '生成草稿已修改。当前已加载的样本不会随之变化。';
}

for (const id of ['voice-brief', 'audition-line']) {
  document.getElementById(id).addEventListener('input', markDraftChanged);
}

candidateCount.addEventListener('change', () => {
  generateButton.textContent = `生成 ${candidateCount.value} 个候选`;
  markDraftChanged();
});

updateView();
